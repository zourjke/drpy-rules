#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

class ConnectivityDiagnoser:
    def __init__(self, config_path):
        with open(config_path, encoding='utf-8') as f:
            self.config = json.load(f)
        d = self.config['diagnosis']
        self.cache_dir = Path(self.config['paths']['cache_dir'])
        self.output_dir = Path(self.config['paths']['output_dir'])
        self.history_file = self.cache_dir / 'domains_history.json'
        self.timeout = int(d.get('timeout', 8))
        self.concurrency = int(d.get('concurrency', 5))
        self.retries = max(1, int(d.get('retry_count', 2)))
        self.proxy = d.get('http_proxy', 'http://127.0.0.1:7890')
        self.history = self._load_history()

    def _load_history(self):
        try:
            with open(self.history_file, encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _probe(self, domain, proxy=None):
        env = os.environ.copy()
        for key in ('http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'):
            env.pop(key, None)
        url = 'https://' + domain
        cmd = ['curl', '-L', '-k', '--connect-timeout', str(self.timeout), '--max-time', str(self.timeout + 2),
               '--silent', '--show-error', '--range', '0-0', '-o', '/dev/null',
               '-w', '%{http_code}|%{time_connect}|%{remote_ip}', '--url', url]
        if proxy:
            cmd[1:1] = ['--proxy', proxy]
        else:
            cmd[1:1] = ['--noproxy', '*']
        try:
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=self.timeout + 4)
            raw = r.stdout.strip().split('|')
            code = raw[0] if raw else '000'
            reachable = code != '000' and bool(code)
            return {'reachable': reachable, 'code': code, 'connect_time': raw[1] if len(raw) > 1 else '',
                    'remote_ip': raw[2] if len(raw) > 2 else '',
                    'error': r.stderr.strip()[-180:] if not reachable else ''}
        except subprocess.TimeoutExpired:
            return {'reachable': False, 'code': '000', 'connect_time': '', 'remote_ip': '', 'error': 'timeout'}
        except OSError as e:
            return {'reachable': False, 'code': '000', 'connect_time': '', 'remote_ip': '', 'error': str(e)}

    def diagnose_domain(self, domain):
        direct = None
        proxy = None
        for _ in range(self.retries):
            direct = self._probe(domain)
            if direct['reachable']:
                break
        if not direct['reachable']:
            for _ in range(self.retries):
                proxy = self._probe(domain, self.proxy)
                if proxy['reachable']:
                    break
        if direct['reachable']:
            status = 'DIRECT'
        elif proxy and proxy['reachable']:
            status = 'PROXY'
        else:
            status = 'UNREACHABLE'
        return {'status': status, 'direct': direct, 'proxy': proxy,
                'last_check': datetime.now().isoformat(timespec='seconds')}

    def diagnose_all(self, domains):
        results = {}
        print(f'[INFO] full diagnosis: {len(domains)} domains, proxy={self.proxy}')
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {pool.submit(self.diagnose_domain, d): d for d in domains}
            for n, future in enumerate(as_completed(futures), 1):
                domain = futures[future]
                try:
                    results[domain] = future.result()
                except Exception as e:
                    results[domain] = {'status': 'UNREACHABLE', 'direct': {}, 'proxy': {},
                                       'last_check': datetime.now().isoformat(timespec='seconds'), 'error': str(e)}
                if n % 25 == 0 or n == len(domains):
                    print(f'[INFO] progress {n}/{len(domains)}')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        counts = {}
        for item in results.values():
            counts[item['status']] = counts.get(item['status'], 0) + 1
        print('[INFO] ' + ', '.join(f'{k}={v}' for k, v in sorted(counts.items())))
        return results

def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: diagnose.py config.json [--full]')
    d = ConnectivityDiagnoser(sys.argv[1])
    domains_file = d.cache_dir / 'domains.txt'
    with open(domains_file, encoding='utf-8') as f:
        domains = sorted({x.strip().lower() for x in f if x.strip()})
    d.diagnose_all(domains)

if __name__ == '__main__':
    main()
