#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 GitHub Contents API 发布分流规则（走 api.github.com，不依赖 git 直连 github.com）"""
import base64
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

API = "https://api.github.com"

PUBLISH = [
    ("rules/drpy-proxy.list", "drpy-proxy.list"),
    ("rules/drpy-clash.mrs", "drpy-clash.mrs"),
    ("rules/drpy-clashmi.yaml", "drpy-clashmi.yaml"),
    ("rules/drpy-surge.conf", "drpy-surge.conf"),
    ("rules/README.md", "README.md"),
    ("README.md", "README.md"),
]

SRC_FILES = [
    "extract_domains.py",
    "diagnose.py",
    "generate_rules.py",
    "main.py",
    "upload_to_github.sh",
    "upload_rules.py",
]

DROP = ["rules/drpy-clash-payload.yaml", "rules/drpy-clash.yaml"]


def gh_token() -> str:
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit("[ERROR] 无法从 gh 取 token: " + r.stderr.strip())
    return r.stdout.strip()


def call(method: str, path: str, token: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "drpy-rules-publisher")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def get_remote(repo: str, path: str, branch: str, token: str):
    status, js = call("GET", f"/repos/{repo}/contents/{path}?ref={branch}", token)
    if status == 200 and js and js.get("type") == "file":
        return js.get("sha"), js.get("content", "").replace("\n", "")
    return None, None


def put(repo: str, path: str, branch: str, token: str, local: Path, message: str) -> bool:
    sha, old = get_remote(repo, path, branch, token)
    b64 = base64.b64encode(local.read_bytes()).decode()
    if old == b64:
        print(f"[SKIP] {path}")
        return True
    body = {"message": message, "branch": branch, "content": b64}
    if sha:
        body["sha"] = sha
    status, js = call("PUT", f"/repos/{repo}/contents/{path}", token, body)
    if status in (200, 201) and js:
        print(f"[OK] {path}  {js['commit']['sha'][:8]}")
        return True
    print(f"[ERROR] {path} HTTP {status}")
    return False


def drop(repo: str, path: str, branch: str, token: str, message: str) -> bool:
    sha, _ = get_remote(repo, path, branch, token)
    if not sha:
        return True
    status, _ = call("DELETE", f"/repos/{repo}/contents/{path}", token,
                     {"message": message, "branch": branch, "sha": sha})
    if status in (200, 204):
        print(f"[DEL] {path}")
        return True
    print(f"[ERROR] 删除 {path} HTTP {status}")
    return False


def main() -> int:
    config_file = Path(sys.argv[1] if len(sys.argv) > 1 else "./config.json")
    if not config_file.exists():
        sys.exit(f"[ERROR] 配置文件不存在: {config_file}")
    cfg = json.loads(config_file.read_text(encoding="utf-8"))
    repo = cfg["github"]["repo"]
    branch = cfg["github"]["branch"]
    work = Path(cfg["paths"]["work_dir"])
    out = Path(cfg["paths"]["output_dir"])
    token = gh_token()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"自动更新分流规则 {stamp}"

    print("========================================")
    print(f"GitHub 发布 (Contents API)\n仓库: {repo}  分支: {branch}")
    print("========================================")

    (out / "update_time.txt").write_text(stamp + "\n", encoding="utf-8")

    ok = True
    for remote_path, local_name in PUBLISH + [("update_time.txt", "update_time.txt")]:
        local = out / local_name
        if not local.exists():
            print(f"[WARN] 本地缺失，跳过: {local}")
            continue
        ok &= put(repo, remote_path, branch, token, local, message)

    for name in SRC_FILES:
        src = work / name
        if src.exists():
            ok &= put(repo, f"src/{name}", branch, token, src, message)

    for path in DROP:
        drop(repo, path, branch, token, message)

    print("[INFO] ✅ 发布完成" if ok else "[ERROR] ❌ 有文件发布失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
