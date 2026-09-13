#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则生成模块 - 生成多格式分流规则
"""
import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

class RuleGenerator:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
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
            'REJECT': []
        }
        
        for domain, info in history.items():
            status = info.get('status', 'REJECT')
            if status in result:
                result[status].append(domain)
        
        # 排序
        for key in result:
            result[key].sort()
        
        print(f"[INFO] 域名分类:")
        print(f"  - DIRECT: {len(result['DIRECT'])} 个")
        print(f"  - PROXY:  {len(result['PROXY'])} 个")
        print(f"  - REJECT: {len(result['REJECT'])} 个")
        
        return result
    
    def generate_quantumult_x(self, domains: Dict[str, List[str]]) -> str:
        """生成 QuantumultX 规则"""
        lines = [
            "# drpy-node 源站分流规则 (QuantumultX)",
            f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 统计: DIRECT={len(domains['DIRECT'])}, PROXY={len(domains['PROXY'])}, REJECT={len(domains['REJECT'])}",
            "",
            "# 需要代理的域名"
        ]
        
        for domain in domains['PROXY']:
            lines.append(f"HOST-SUFFIX,{domain},PROXY")
        
        lines.append("")
        lines.append("# 直连域名")
        for domain in domains['DIRECT']:
            lines.append(f"HOST-SUFFIX,{domain},DIRECT")
        
        lines.append("")
        lines.append("# 拒绝访问（已失效）")
        for domain in domains['REJECT']:
            lines.append(f"HOST-SUFFIX,{domain},REJECT")
        
        return '\n'.join(lines)
    
    def generate_clash_payload(self, domains: Dict[str, List[str]]) -> str:
        """生成 Clash rule-provider payload"""
        lines = [
            "# drpy-node source routing rules (Clash/ClashMeta)",
            f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Counts: DIRECT={len(domains['DIRECT'])}, PROXY={len(domains['PROXY'])}, REJECT={len(domains['REJECT'])}",
            "",
            "payload:"
        ]
        for domain in domains['PROXY']:
            lines.append(f"  - DOMAIN-SUFFIX,{domain}")
        return '\n'.join(lines) + '\n'

    def generate_clashmi_snippet(self) -> str:
        """生成 ClashMi Anchor_DN provider 引用片段"""
        repo = self.config['github']['repo']
        return (
            'drpy_proxy: { <<: *Anchor_DN, url: '
            f'"https://raw.githubusercontent.com/{repo}/main/rules/drpy-clash-payload.yaml" }}\n'
        )
    
    def generate_surge(self, domains: Dict[str, List[str]]) -> str:
        """生成 Surge/Shadowrocket 规则"""
        lines = [
            "# drpy-node 源站分流规则 (Surge/Shadowrocket)",
            f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 统计: DIRECT={len(domains['DIRECT'])}, PROXY={len(domains['PROXY'])}, REJECT={len(domains['REJECT'])}",
            "",
            "# 需要代理的域名"
        ]
        
        for domain in domains['PROXY']:
            lines.append(f"DOMAIN-SUFFIX,{domain},PROXY")
        
        lines.append("")
        lines.append("# 直连域名")
        for domain in domains['DIRECT']:
            lines.append(f"DOMAIN-SUFFIX,{domain},DIRECT")
        
        lines.append("")
        lines.append("# 拒绝访问（已失效）")
        for domain in domains['REJECT']:
            lines.append(f"DOMAIN-SUFFIX,{domain},REJECT")
        
        return '\n'.join(lines)
    
    def generate_all(self):
        """生成所有格式规则"""
        history = self.load_history()
        domains = self.filter_domains(history)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # QuantumultX
        qx_rule = self.generate_quantumult_x(domains)
        qx_file = self.output_dir / 'drpy-proxy.list'
        with open(qx_file, 'w', encoding='utf-8') as f:
            f.write(qx_rule)
        print(f"[INFO] 已生成: {qx_file}")
        
        # Clash
        clash_rule = self.generate_clash_payload(domains)
        clash_file = self.output_dir / 'drpy-clash-payload.yaml'
        with open(clash_file, 'w', encoding='utf-8') as f:
            f.write(clash_rule)
        print(f"[INFO] 已生成: {clash_file}")
        
        clashmi_file = self.output_dir / 'drpy-clashmi.yaml'
        with open(clashmi_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_clashmi_snippet())
        print(f"[INFO] 已生成: {clashmi_file}")
        
        # Surge/Shadowrocket
        surge_rule = self.generate_surge(domains)
        surge_file = self.output_dir / 'drpy-surge.conf'
        with open(surge_file, 'w', encoding='utf-8') as f:
            f.write(surge_rule)
        print(f"[INFO] 已生成: {surge_file}")
        
        # 生成 README
        readme = self._generate_readme(domains)
        readme_file = self.output_dir / 'README.md'
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme)
        print(f"[INFO] 已生成: {readme_file}")
    
    def _generate_readme(self, domains: Dict[str, List[str]]) -> str:
        """生成 README 说明文档"""
        return f"""# drpy-node 源站分流规则

自动从 [drpy-node](https://github.com/hjdhnx/drpy-node) 爬虫源提取域名并诊断连通性，生成分流规则。

## 📊 统计信息

- **更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **直连域名**: {len(domains['DIRECT'])} 个
- **需要代理**: {len(domains['PROXY'])} 个
- **已失效**: {len(domains['REJECT'])} 个

## 🚀 使用方法

### QuantumultX

```
[filter_remote]
https://raw.githubusercontent.com/{self.config['github']['repo']}/main/rules/drpy-proxy.list, tag=drpy源站, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
```

### ClashMi

规则数据文件：

```text
https://raw.githubusercontent.com/{self.config['github']['repo']}/main/rules/drpy-clash-payload.yaml
```

在 ClashMi 主配置中按 Anchor_DN 格式引用：

```yaml
drpy_proxy: {{ <<: *Anchor_DN, url: "https://raw.githubusercontent.com/{self.config['github']['repo']}/main/rules/drpy-clash-payload.yaml" }}
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

## 📝 说明

- 规则每天凌晨 4 点自动更新
- DIRECT 域名表示可直连访问
- PROXY 域名表示需要代理访问
- REJECT 域名表示已失效（连续诊断失败）

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
