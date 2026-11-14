# drpy-node 源站分流规则

自动从 [drpy-node](https://github.com/hjdhnx/drpy-node) 爬虫源提取域名并诊断连通性，生成分流规则。

## 📊 统计信息

- **更新时间**: 2026-11-15 00:07:43
- **直连域名**: 665 个
- **需要代理**: 76 个
- **不可达（不生成分流）**: 41 个
- **手工补充**: 1 条（`extra_proxy.txt`）

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

### Clash / ClashMi / Stash（直连侧，手机端必备）

仓库同时发布**直连规则集**，手机端（ClashMi/Stash/Clash）必须引用它，
否则源站 CDN 会落到 `MATCH` 兜底走代理 → 视频分片只剩 150~280 KB/s，必然卡顿：

```yaml
rule-providers:
  drpy_direct: { <<: *Anchor_DN, url: "https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-direct.mrs" }

rules:
  - RULE-SET,drpy_direct,DIRECT     # 必须放在 MATCH / 兜底代理之前
  - RULE-SET,drpy_proxy,PROXY
```

也可用普通 rule-provider 格式：`rules/drpy-clash-direct.yaml`（payload）。

### Surge / Shadowrocket

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/zourjke/drpy-rules/main/rules/drpy-surge.conf,PROXY
```

## 🧩 手工补充规则

`extra_proxy.txt`（与 config.json 同目录）中的条目不会被自动扫描覆盖，会追加到各格式的代理段：

- `IP-CIDR,58.99.33.0/24`

- Surge / Shadowrocket、QuantumultX：原样输出并补 `,PROXY`
- Clash：写入 `drpy-clash-payload.yaml`
- ClashMi（`drpy-clash.mrs`）：仅支持域名类条目，`IP-CIDR` 等需在主配置里自行添加

### 手工直连域名

`extra_direct.txt`（与 config.json 同目录）每行一个域名，会被**强制并入直连段**（优先级最高，不受自动诊断结果覆盖）。
用于「运行时才能拿到、源文件里不出现」的媒体/CDN 域名，例如播放地址里的分片域名。

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
