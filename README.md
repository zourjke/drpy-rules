# drpy-node 源站分流规则

自动从 [drpy-node](https://github.com/hjdhnx/drpy-node) 爬虫源提取域名并诊断连通性，生成分流规则。

## 📊 统计信息

- **更新时间**: 2026-09-13 17:23:32
- **直连域名**: 209 个
- **需要代理**: 7 个
- **已失效**: 4 个

## 🚀 使用方法

### QuantumultX

```
[filter_remote]
https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-proxy.list, tag=drpy源站, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
```

### Clash

```yaml
rule-providers:
  drpy-proxy:
    type: http
    behavior: domain
    url: "https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-clash.yaml"
    path: ./ruleset/drpy-proxy.yaml
    interval: 86400

rules:
  - RULE-SET,drpy-proxy,PROXY
```

### Surge / Shadowrocket

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-surge.conf,PROXY
```

## 📝 说明

- 规则每天凌晨 4 点自动更新
- DIRECT 域名表示可直连访问
- PROXY 域名表示需要代理访问
- REJECT 域名表示已失效（连续诊断失败）

## 🔗 相关链接

- [drpy-node 项目](https://github.com/hjdhnx/drpy-node)
- [规则仓库](zourjke/drpy-rules)

---

*由自动化脚本生成*
