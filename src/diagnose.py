#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连通性诊断模块 - 测试域名直连/代理可用性
"""
import json
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

class ConnectivityDiagnoser:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.cache_dir = Path(self.config['paths']['cache_dir'])
        self.timeout = self.config['diagnosis']['timeout']
        self.concurrency = self.config['diagnosis']['concurrency']
        self.retry_count = self.config['diagnosis']['retry_count']
        self.expire_days = self.config['diagnosis']['history_expire_days']
        self.req_proxy_url = self.config['nas']['req_proxy_url']
        
        self.history_file = self.cache_dir / 'domains_history.json'
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """加载诊断历史"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] 加载历史失败: {e}")
        return {}
    
    def _save_history(self):
        """保存诊断历史"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def _needs_check(self, domain: str) -> bool:
        """判断域名是否需要重新检测"""
        if domain not in self.history:
            return True
        
        last_check = datetime.fromisoformat(self.history[domain]['last_check'])
        expire_time = datetime.now() - timedelta(days=self.expire_days)
        
        return last_check < expire_time
    
    def _test_direct(self, domain: str) -> Tuple[bool, str]:
        """测试直连"""
        url = f"https://{domain}"
        cmd = [
            'curl', '-I', '-L', '-k', '-m', str(self.timeout),
            '-s', '-o', '/dev/null', '-w', '%{http_code}',
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 2)
            status_code = result.stdout.strip()
            
            if status_code and status_code.startswith(('2', '3')):
                return True, f"直连成功 ({status_code})"
            else:
                return False, f"直连失败 ({status_code})"
        except subprocess.TimeoutExpired:
            return False, "直连超时"
        except Exception as e:
            return False, f"直连异常: {str(e)}"
    
    def _test_proxy(self, domain: str) -> Tuple[bool, str]:
        """测试代理（通过 req-proxy API）"""
        url = f"https://{domain}"
        timeout_ms = self.timeout * 1000
        
        # 使用 curl 调用 req-proxy API
        cmd = [
            'curl', '-X', 'POST', self.req_proxy_url,
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                'method': 'HEAD',
                'url': url,
                'timeout': timeout_ms
            }),
            '-m', str(self.timeout + 2),
            '-s'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 3)
            
            if result.returncode != 0:
                return False, f"代理请求失败 (exit {result.returncode})"
            
            try:
                resp = json.loads(result.stdout)
                status = resp.get('status', 0)
                
                if str(status).startswith(('2', '3')):
                    return True, f"代理成功 ({status})"
                else:
                    return False, f"代理失败 ({status})"
            except json.JSONDecodeError:
                return False, f"代理响应解析失败"
        
        except subprocess.TimeoutExpired:
            return False, "代理超时"
        except Exception as e:
            return False, f"代理异常: {str(e)}"
    
    def diagnose_domain(self, domain: str) -> Dict:
        """诊断单个域名"""
        print(f"[DIAG] 检测: {domain}")
        
        # 测试直连
        direct_ok, direct_msg = self._test_direct(domain)
        
        if direct_ok:
            result = {
                'status': 'DIRECT',
                'message': direct_msg,
                'last_check': datetime.now().isoformat(),
                'retry_count': 0
            }
        else:
            # 直连失败，测试代理
            time.sleep(0.5)  # 短暂延迟避免过于频繁
            proxy_ok, proxy_msg = self._test_proxy(domain)
            
            if proxy_ok:
                result = {
                    'status': 'PROXY',
                    'message': f"{direct_msg} / {proxy_msg}",
                    'last_check': datetime.now().isoformat(),
                    'retry_count': 0
                }
            else:
                # 双失败，增加重试计数
                retry_count = self.history.get(domain, {}).get('retry_count', 0) + 1
                
                if retry_count >= self.retry_count:
                    result = {
                        'status': 'REJECT',
                        'message': f"{direct_msg} / {proxy_msg} (重试 {retry_count} 次)",
                        'last_check': datetime.now().isoformat(),
                        'retry_count': retry_count
                    }
                else:
                    result = {
                        'status': 'PENDING',
                        'message': f"{direct_msg} / {proxy_msg} (重试 {retry_count}/{self.retry_count})",
                        'last_check': datetime.now().isoformat(),
                        'retry_count': retry_count
                    }
        
        return result
    
    def diagnose_all(self, domains: List[str], incremental: bool = True) -> Dict[str, Dict]:
        """并发诊断所有域名"""
        if incremental:
            # 增量模式：只检测新域名或过期域名
            to_check = [d for d in domains if self._needs_check(d)]
            print(f"[INFO] 增量模式：{len(to_check)}/{len(domains)} 个域名需要检测")
        else:
            # 全量模式：检测所有域名
            to_check = domains
            print(f"[INFO] 全量模式：检测所有 {len(domains)} 个域名")
        
        if not to_check:
            print("[INFO] 无需检测的域名")
            return self.history
        
        results = {}
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            future_to_domain = {executor.submit(self.diagnose_domain, domain): domain for domain in to_check}
            
            completed = 0
            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                try:
                    result = future.result()
                    results[domain] = result
                    self.history[domain] = result
                    completed += 1
                    
                    if completed % 10 == 0:
                        print(f"[INFO] 进度: {completed}/{len(to_check)}")
                except Exception as e:
                    print(f"[ERROR] 检测失败 {domain}: {e}")
                    results[domain] = {
                        'status': 'ERROR',
                        'message': str(e),
                        'last_check': datetime.now().isoformat(),
                        'retry_count': 0
                    }
        
        # 保存历史
        self._save_history()
        
        # 统计
        stats = {'DIRECT': 0, 'PROXY': 0, 'REJECT': 0, 'PENDING': 0, 'ERROR': 0}
        for result in self.history.values():
            status = result.get('status', 'ERROR')
            stats[status] = stats.get(status, 0) + 1
        
        print(f"\n[INFO] 诊断统计:")
        print(f"  - DIRECT:  {stats['DIRECT']} 个")
        print(f"  - PROXY:   {stats['PROXY']} 个")
        print(f"  - REJECT:  {stats['REJECT']} 个")
        print(f"  - PENDING: {stats['PENDING']} 个")
        print(f"  - ERROR:   {stats['ERROR']} 个")
        
        return self.history

def main():
    if len(sys.argv) < 2:
        print("用法: python3 diagnose.py <config.json> [--full]")
        sys.exit(1)
    
    config_path = sys.argv[1]
    incremental = '--full' not in sys.argv
    
    diagnoser = ConnectivityDiagnoser(config_path)
    
    # 读取域名列表
    cache_dir = Path(diagnoser.config['paths']['cache_dir'])
    domains_file = cache_dir / 'domains.txt'
    
    if not domains_file.exists():
        print(f"[ERROR] 域名列表不存在: {domains_file}")
        sys.exit(1)
    
    with open(domains_file, 'r', encoding='utf-8') as f:
        domains = [line.strip() for line in f if line.strip()]
    
    print(f"[INFO] 加载 {len(domains)} 个域名")
    diagnoser.diagnose_all(domains, incremental=incremental)

if __name__ == '__main__':
    main()
