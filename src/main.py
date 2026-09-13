#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主控脚本 - 串联所有模块
"""
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

class MainController:
    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.work_dir = Path(self.config['paths']['work_dir'])
        self.log_dir = Path(self.config['paths']['log_dir'])
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    
    def run_step(self, name: str, script: str, args: list = None) -> bool:
        """运行单个步骤"""
        self.log(f"===== {name} =====")
        start_time = time.time()
        
        cmd = ['python3', script, self.config_path]
        if args:
            cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=3600  # 1 小时超时
            )
            
            # 输出到控制台和日志
            if result.stdout:
                for line in result.stdout.splitlines():
                    self.log(line)
            
            if result.stderr:
                for line in result.stderr.splitlines():
                    self.log(f"[STDERR] {line}")
            
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                self.log(f"✅ {name} 完成 (耗时 {elapsed:.1f}s)")
                return True
            else:
                self.log(f"❌ {name} 失败 (exit code: {result.returncode})")
                return False
        
        except subprocess.TimeoutExpired:
            self.log(f"❌ {name} 超时")
            return False
        except Exception as e:
            self.log(f"❌ {name} 异常: {e}")
            return False
    
    def run(self, full_scan: bool = False, skip_github: bool = False):
        """运行完整流程"""
        self.log("========================================")
        self.log("drpy-node 分流规则生成器")
        self.log(f"工作目录: {self.work_dir}")
        self.log(f"模式: {'全量扫描' if full_scan else '增量更新'}")
        self.log("========================================")
        
        total_start = time.time()
        
        # 步骤 1: 提取域名
        if not self.run_step(
            "步骤 1: 提取域名",
            str(self.work_dir / 'extract_domains.py')
        ):
            self.log("流程终止")
            return False
        
        # 步骤 2: 连通性诊断
        diagnose_args = ['--full'] if full_scan else []
        if not self.run_step(
            "步骤 2: 连通性诊断",
            str(self.work_dir / 'diagnose.py'),
            diagnose_args
        ):
            self.log("流程终止")
            return False
        
        # 步骤 3: 生成规则
        if not self.run_step(
            "步骤 3: 生成规则",
            str(self.work_dir / 'generate_rules.py')
        ):
            self.log("流程终止")
            return False
        
        # 步骤 4: 推送到 GitHub
        if not skip_github:
            self.log("===== 步骤 4: 推送到 GitHub =====")
            upload_script = self.work_dir / 'upload_to_github.sh'
            
            if not upload_script.exists():
                self.log("❌ upload_to_github.sh 不存在")
            else:
                try:
                    result = subprocess.run(
                        ['bash', str(upload_script)],
                        cwd=self.work_dir,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.stdout:
                        for line in result.stdout.splitlines():
                            self.log(line)
                    
                    if result.returncode == 0:
                        self.log("✅ GitHub 推送完成")
                    else:
                        self.log(f"❌ GitHub 推送失败: {result.stderr}")
                
                except Exception as e:
                    self.log(f"❌ GitHub 推送异常: {e}")
        else:
            self.log("跳过 GitHub 推送")
        
        # 总结
        total_elapsed = time.time() - total_start
        self.log("========================================")
        self.log(f"✅ 全部流程完成！总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
        self.log(f"日志文件: {self.log_file}")
        self.log("========================================")
        
        return True

def main():
    if len(sys.argv) < 2:
        print("""
用法: python3 main.py <config.json> [选项]

选项:
  --full          全量扫描（重新诊断所有域名）
  --skip-github   跳过 GitHub 推送
  
示例:
  python3 main.py config.json                # 增量更新 + 推送
  python3 main.py config.json --full         # 全量扫描 + 推送
  python3 main.py config.json --skip-github  # 增量更新，不推送
""")
        sys.exit(1)
    
    config_path = sys.argv[1]
    full_scan = '--full' in sys.argv
    skip_github = '--skip-github' in sys.argv
    
    controller = MainController(config_path)
    success = controller.run(full_scan=full_scan, skip_github=skip_github)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
