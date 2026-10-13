#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则生成模块 - 生成多格式分流规则
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

class RuleGenerator:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.config_path = Path(config_path)
        self.cache_dir = Path(self.config['paths']['cache_dir'])
        self.output_dir = Path(self.config['paths']['output_dir'])
        self.history_file = self.cache_dir / 'domains_history.json'
    
    def load_history(self) -> Dict:
        """加载诊断历史"""
        if not self.history_file.exists():
            print(f"[ERROR] 诊断历史不存在: {self.history_file}")
            sys.exit(1)
        
        with open(self.history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def filter_domains(self, history: Dict) -> Dict[str, List[str]]:
        """按状态分类域名"""
        result = {
            'DIRECT': [],
            'PROXY': [],
            'UNREACHABLE': []
        }
        
        for domain, info in history.items():
            status = info.get('status', 'UNREACHABLE')
            if status in result:
                result[status].append(domain)
        
        # 排序
        for key in result:
            result[key].sort()
        
        print(f"[INFO] 域名分类:")
        print(f"  - DIRECT: {len(result['DIRECT'])} 个")
        print(f"  - PROXY: {len(result['PROXY'])} 个")
        print(f"  - UNREACHABLE: {len(history) - len(result['DIRECT']) - len(result['PROXY'])} 个")
        
        return result
    
    def load_extra(self) -> List[str]:
        """读取手工补充规则（与 config.json 同目录的 extra_proxy.txt，每行「类型,值」）"""
        path = self.config_path.parent / 'extra_proxy.txt'
        if not path.exists():
            return []
        rules = []
        for raw in path.read_text(encoding='utf-8').splitlines():
            line = raw.strip()
            if line and not line.startswith('#'):
                rules.append(line)
        return rules

    @staticmethod
    def split_extra(rules: List[str]):
        """拆出域名类与其它类（IP-CIDR 等）补充规则"""
        domains, others = [], []
        for rule in rules:
            kind = rule.split(',', 1)[0].strip().upper()
            if kind in ('DOMAIN-SUFFIX', 'DOMAIN', 'DOMAIN-KEYWORD'):
                domains.append(rule)
            else:
                others.append(rule)
        return domains, others

    def generate_quantumult_x(self, domains: Dict[str, List[str]],
                              extra: List[str] = None) -> str:
        """生成 QuantumultX 规则"""
        lines = [
            "# drpy-node 源站分流规则 (QuantumultX)",
            f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 统计: DIRECT={len(domains['DIRECT'])}, PROXY={len(domains['PROXY'])}",
            "",
            "# 需要代理的域名"
        ]
        
        for domain in domains['PROXY']:
            lines.append(f"HOST-SUFFIX,{domain},PROXY")
        
        if extra:
            lines.append("")
            lines.append("# 手工补充")
            for rule in extra:
                lines.append(f"{rule},PROXY")
        
        lines.append("")
        lines.append("# 直连域名")
        for domain in domains['DIRECT']:
            lines.append(f"HOST-SUFFIX,{domain},DIRECT")
        
        return '\n'.join(lines)
    
    def generate_clash_payload(self, domains: Dict[str, List[str]],
                               extra: List[str] = None) -> str:
        """生成 Clash rule-provider payload"""
        lines = [
            "# drpy-node source routing rules (Clash/ClashMeta)",
            f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Counts: DIRECT={len(domains['DIRECT'])}, PROXY={len(domains['PROXY'])}, UNREACHABLE={len(domains['UNREACHABLE'])}",
            "",
            "payload:"
        ]
        for domain in domains['PROXY']:
            lines.append(f"  - DOMAIN-SUFFIX,{domain}")
        for rule in (extra or []):
            lines.append(f"  - {rule}")
        return '\n'.join(lines) + '\n'

    def generate_clashmi_snippet(self) -> str:
        """生成 ClashMi Anchor_DN provider 引用片段"""
        repo = self.config['github']['repo']
        return (
            'drpy_proxy: { <<: *Anchor_DN, url: '
            f'"https://raw.githubusercontent.com/{repo}/main/rules/drpy-clash.mrs" }}\n'
        )

    def generate_clash_mrs(self, domains: Dict[str, List[str]],
                           extra_domains: List[str] = None) -> str:
        """使用 CrashCore 将 domain 规则转换为 MRS"""
        source = self.output_dir / 'drpy-clash-source.yaml'
        target = self.output_dir / 'drpy-clash.mrs'
        with open(source, 'w', encoding='utf-8') as f:
            f.write('payload:\n')
            for domain in domains['PROXY']:
                f.write(f'  - DOMAIN-SUFFIX,{domain}\n')
            for rule in (extra_domains or []):
                f.write(f'  - {rule}\n')
        core = self.config.get('clash', {}).get('core', '/tmp/ShellCrash/CrashCore')
        if not Path(core).exists():
            raise RuntimeError(f'CrashCore 不存在: {core}')
        result = subprocess.run(
            [core, 'convert-ruleset', 'domain', 'yaml', str(source), str(target)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0 or not target.exists() or target.stat().st_size < 16:
            raise RuntimeError(result.stderr.strip() or 'MRS 转换失败')
        with open(target, 'rb') as f:
            if f.read(4) != b'\x28\xb5\x2f\xfd':
                raise RuntimeError('MRS 文件魔数校验失败')
        source.unlink()
        return str(target)
    
    def generate_surge(self, domains: Dict[str, List[str]],
                       extra: List[str] = None) -> str:
        """生成 Surge/Shadowrocket 规则"""
        lines = [
            "# drpy-node 源站分流规则 (Surge/Shadowrocket)",
            f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 统计: DIRECT={len(domains['DIRECT'])}, PROXY={len(domains['PROXY'])}",
            "",
            "# 需要代理的域名"
        ]
        
        for domain in domains['PROXY']:
            lines.append(f"DOMAIN-SUFFIX,{domain},PROXY")
        
        if extra:
            lines.append("")
            lines.append("# 手工补充")
            for rule in extra:
                lines.append(f"{rule},PROXY")
        
        lines.append("")
        lines.append("# 直连域名")
        for domain in domains['DIRECT']:
            lines.append(f"DOMAIN-SUFFIX,{domain},DIRECT")
        
        return '\n'.join(lines)
    
    def generate_all(self):
        """生成所有格式规则"""
        history = self.load_history()
        domains = self.filter_domains(history)
        
        extra = self.load_extra()
        extra_domains, extra_others = self.split_extra(extra)
        if extra:
            print(f"[INFO] 手工补充规则: 域名类 {len(extra_domains)} 条, 其它类 {len(extra_others)} 条")
        if extra_others:
            print(f"[INFO] MRS 为 domain 行为，已跳过非域名补充规则: {', '.join(extra_others)}")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # QuantumultX
        qx_rule = self.generate_quantumult_x(domains, extra)
        qx_file = self.output_dir / 'drpy-proxy.list'
        with open(qx_file, 'w', encoding='utf-8') as f:
            f.write(qx_rule)
        print(f"[INFO] 已生成: {qx_file}")
        
        # Clash
        clash_rule = self.generate_clash_payload(domains, extra)
        clash_file = self.output_dir / 'drpy-clash-payload.yaml'
        with open(clash_file, 'w', encoding='utf-8') as f:
            f.write(clash_rule)
        print(f"[INFO] 已生成: {clash_file}")
        
        self.generate_clash_mrs(domains, extra_domains)
        clashmi_file = self.output_dir / 'drpy-clashmi.yaml'
        with open(clashmi_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_clashmi_snippet())
        print(f"[INFO] 已生成: {clashmi_file}")
        
        # Surge/Shadowrocket
        surge_rule = self.generate_surge(domains, extra)
        surge_file = self.output_dir / 'drpy-surge.conf'
        with open(surge_file, 'w', encoding='utf-8') as f:
            f.write(surge_rule)
        print(f"[INFO] 已生成: {surge_file}")
        
        # 生成 README
        readme = self._generate_readme(domains, extra)
        readme_file = self.output_dir / 'README.md'
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme)
        print(f"[INFO] 已生成: {readme_file}")
    
    def _generate_readme(self, domains: Dict[str, List[str]],
                         extra: List[str] = None) -> str:
        """生成 README 说明文档"""
        extra = extra or []
        extra_lines = '\n'.join(f'- `{r}`' for r in extra) or '- （无）'
        return f"""# drpy-node 源站分流规则

自动从 [drpy-node](https://github.com/hjdhnx/drpy-node) 爬虫源提取域名并诊断连通性，生成分流规则。

## 📊 统计信息

- **更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **直连域名**: {len(domains['DIRECT'])} 个
- **需要代理**: {len(domains['PROXY'])} 个
- **不可达（不生成分流）**: {len(domains['UNREACHABLE'])} 个
- **手工补充**: {len(extra)} 条（`extra_proxy.txt`）

## 🚀 使用方法

### QuantumultX

```
[filter_remote]
https://raw.githubusercontent.com/{self.config['github']['repo']}/main/rules/drpy-proxy.list, tag=drpy源站, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
```

### ClashMi

规则数据文件：

```text
https://raw.githubusercontent.com/{self.config['github']['repo']}/main/rules/drpy-clash.mrs
```

在 ClashMi 主配置中按 Anchor_DN 格式引用：

```yaml
drpy_proxy: {{ <<: *Anchor_DN, url: "https://raw.githubusercontent.com/{self.config['github']['repo']}/main/rules/drpy-clash.mrs" }}
```

然后在 `rules:` 中添加：

```yaml
- RULE-SET,drpy_proxy,PROXY
```

也可以直接引用仓库中的 `rules/drpy-clashmi.yaml` 片段。

### Surge / Shadowrocket

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/{self.config['github']['repo']}/main/rules/drpy-surge.conf,PROXY
```

## 🧩 手工补充规则

`extra_proxy.txt`（与 config.json 同目录）中的条目不会被自动扫描覆盖，会追加到各格式的代理段：

{extra_lines}

- Surge / Shadowrocket、QuantumultX：原样输出并补 `,PROXY`
- Clash：写入 `drpy-clash-payload.yaml`
- ClashMi（`drpy-clash.mrs`）：仅支持域名类条目，`IP-CIDR` 等需在主配置里自行添加

## 📝 说明

- 规则每天凌晨 4 点自动更新
- DIRECT 域名表示可直连访问
- PROXY 域名表示需要代理访问
- UNREACHABLE 域名仅记录，不生成任何分流规则

## 🔗 相关链接

- [drpy-node 项目](https://github.com/hjdhnx/drpy-node)
- [规则仓库]({self.config['github']['repo']})

---

*由自动化脚本生成*
"""

def main():
    if len(sys.argv) < 2:
        print("用法: python3 generate_rules.py <config.json>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    generator = RuleGenerator(config_path)
    generator.generate_all()

if __name__ == '__main__':
    main()
