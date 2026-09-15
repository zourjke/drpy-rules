# drpy-node 源站分流规则

自动从 [drpy-node](https://github.com/hjdhnx/drpy-node) 爬虫源提取域名并诊断连通性，生成分流规则。

## 📊 统计信息

- **更新时间**: 2026-09-16 04:07:04
- **直连域名**: 253 个
- **需要代理**: 74 个
- **不可达（不生成分流）**: 39 个

## 🚀 使用方法

### QuantumultX

```
[filter_remote]
https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-proxy.list, tag=drpy源站, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
```

### ClashMi

规则数据文件：

```text
https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-clash.mrs
```

在 ClashMi 主配置中按 Anchor_DN 格式引用：

```yaml
drpy_proxy: { <<: *Anchor_DN, url: "https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-clash.mrs" }
```

然后在 `rules:` 中添加：

```yaml
- RULE-SET,drpy_proxy,PROXY
```

也可以直接引用仓库中的 `rules/drpy-clashmi.yaml` 片段。

### Surge / Shadowrocket

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-surge.conf,PROXY
```

## 📝 说明

- 规则每天凌晨 4 点自动更新
- DIRECT 域名表示可直连访问
- PROXY 域名表示需要代理访问
- UNREACHABLE 域名仅记录，不生成任何分流规则

## 🔗 相关链接

- [drpy-node 项目](https://github.com/hjdhnx/drpy-node)
- [规则仓库](zourjke/drpy-rules)

---

*由自动化脚本生成*
