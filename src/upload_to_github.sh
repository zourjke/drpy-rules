#!/bin/bash
# GitHub 自动推送脚本

set -e

# 读取配置
CONFIG_FILE="$1"
if [ -z "$CONFIG_FILE" ]; then
    CONFIG_FILE="./config.json"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[ERROR] 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

# 解析配置
REPO=$(jq -r '.github.repo' "$CONFIG_FILE")
BRANCH=$(jq -r '.github.branch' "$CONFIG_FILE")
EMAIL=$(jq -r '.github.email' "$CONFIG_FILE")
USERNAME=$(jq -r '.github.username' "$CONFIG_FILE")
OUTPUT_DIR=$(jq -r '.paths.output_dir' "$CONFIG_FILE")

echo "========================================"
echo "GitHub 推送脚本"
echo "仓库: $REPO"
echo "分支: $BRANCH"
echo "========================================"

# 检查 GITHUB_TOKEN 环境变量
if [ -z "$GITHUB_TOKEN" ]; then
    echo "[ERROR] 环境变量 GITHUB_TOKEN 未设置"
    echo "请先设置 GitHub Personal Access Token:"
    echo "  export GITHUB_TOKEN='your_token_here'"
    exit 1
fi

# 临时目录
TEMP_DIR="/tmp/drpy-rules-$$"
mkdir -p "$TEMP_DIR"

cd "$TEMP_DIR"

# 克隆仓库（如果已存在则拉取）
REPO_URL="https://${GITHUB_TOKEN}@github.com/${REPO}.git"

echo "[INFO] 克隆仓库..."
if git clone --depth 1 --branch "$BRANCH" "$REPO_URL" repo 2>/dev/null; then
    echo "[INFO] 仓库克隆成功"
    cd repo
    git pull origin "$BRANCH"
else
    echo "[INFO] 仓库不存在，创建新仓库..."
    mkdir -p repo
    cd repo
    git init
    git checkout -b "$BRANCH"
fi

# 配置 Git
git config user.name "$USERNAME"
git config user.email "$EMAIL"

# 创建 rules 目录
mkdir -p rules

# 复制规则文件
echo "[INFO] 复制规则文件..."
cp "$OUTPUT_DIR"/drpy-proxy.list rules/ 2>/dev/null || echo "[WARN] drpy-proxy.list 不存在"
cp "$OUTPUT_DIR"/drpy-clash-payload.yaml rules/ 2>/dev/null || echo "[WARN] drpy-clash-payload.yaml 不存在"
cp "$OUTPUT_DIR"/drpy-clashmi.yaml rules/ 2>/dev/null || echo "[WARN] drpy-clashmi.yaml 不存在"
rm -f rules/drpy-clash.yaml
cp "$OUTPUT_DIR"/drpy-surge.conf rules/ 2>/dev/null || echo "[WARN] drpy-surge.conf 不存在"
cp "$OUTPUT_DIR"/README.md . 2>/dev/null || echo "[WARN] README.md 不存在"

# 同步可公开的项目源码，不同步配置、凭据、缓存或日志
for source_file in extract_domains.py diagnose.py generate_rules.py main.py upload_to_github.sh; do
    if [ -f "$(dirname "$CONFIG_FILE")/$source_file" ]; then
        cp "$(dirname "$CONFIG_FILE")/$source_file" .
    fi
done
[ -f "$(dirname "$CONFIG_FILE")/README.md" ] && cp "$(dirname "$CONFIG_FILE")/README.md" . || true

# 更新时间戳
date '+%Y-%m-%d %H:%M:%S' > update_time.txt

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet; then
    echo "[INFO] 无变更，跳过推送"
    cd /
    rm -rf "$TEMP_DIR"
    exit 0
fi

# 提交变更
echo "[INFO] 提交变更..."
git add .
git commit -m "自动更新分流规则 $(date '+%Y-%m-%d %H:%M:%S')"

# 推送到 GitHub
echo "[INFO] 推送到 GitHub..."
if git push -u origin "$BRANCH" 2>&1; then
    echo "[INFO] ✅ 推送成功"
else
    echo "[ERROR] ❌ 推送失败"
    cd /
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 清理
cd /
rm -rf "$TEMP_DIR"

echo "[INFO] ✅ GitHub 推送完成"
echo "========================================"
