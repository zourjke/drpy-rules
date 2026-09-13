# drpy-rules

本仓库同时提供 drpy-node 源站分流规则和规则生成器源码。

## 规则订阅

- Quantumult X: `rules/drpy-proxy.list`
- Clash/ClashMeta payload: `rules/drpy-clash-payload.yaml`
- ClashMi Anchor 引用: `rules/drpy-clashmi.yaml`
- Surge/Shadowrocket: `rules/drpy-surge.conf`

ClashMi：

```yaml
drpy_proxy: { <<: *Anchor_DN, url: "https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-clash-payload.yaml" }
```

在 `rules:` 中加入：

```yaml
- RULE-SET,drpy_proxy,PROXY
```

## 生成器

源码在 `src/`，示例配置为 `config.example.json`。复制为 NAS 本地的 `config.json` 后运行：

```sh
python3 src/main.py config.json
python3 src/main.py config.json --full
```

Token、NAS 凭据、缓存和日志不会提交到仓库。
