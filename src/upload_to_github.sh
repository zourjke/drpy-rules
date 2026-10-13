#!/bin/bash
# GitHub 自动推送脚本（薄封装；实际发布走 upload_rules.py → Contents API）
set -e

CONFIG_FILE="${1:-./config.json}"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[ERROR] 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

# gh 使用自身凭据（~/.config/gh/hosts.yml）；清掉外部传入的失效 token，避免覆盖
unset GH_TOKEN GITHUB_TOKEN

exec python3 "$(dirname "$CONFIG_FILE")/upload_rules.py" "$CONFIG_FILE"
