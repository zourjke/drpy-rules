#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名提取模块 - 从 drpy-node 爬虫源中提取所有域名
"""
import re
import json
import sys
from pathlib import Path
from typing import Set, List

class DomainExtractor:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.spider_dirs = self.config['nas']['spider_dirs']
        self.cache_dir = Path(self.config['paths']['cache_dir'])
        
        # URL 正则（提取完整 URL）
        self.url_pattern = re.compile(
            r'https?://[^\s"\'\)\]<>]+',
            re.IGNORECASE
        )
        
        # 域名提取正则
        self.domain_pattern = re.compile(
            r'^https?://([^/:]+)',
            re.IGNORECASE
        )
        
        # 过滤黑名单
        self.blacklist = {
            'localhost', '127.0.0.1', 'example.com', 'example.org',
            'test.com', 'demo.com', '0.0.0.0', '192.168.',
            '10.0.', '172.16.', 'your-domain.com'
        }
    
    def extract_from_file(self, file_path: Path) -> Set[str]:
        """从单个文件提取域名"""
        domains = set()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # 先找到所有 URL
                urls = self.url_pattern.findall(content)
                for url in urls:
                    # 从 URL 中提取域名
                    match = self.domain_pattern.match(url)
                    if match:
                        domain = match.group(1).lower().rstrip('.')
                        if self._is_valid_domain(domain):
                            domains.add(domain)
        except Exception as e:
            print(f"[ERROR] 读取文件失败 {file_path}: {e}", file=sys.stderr)
        return domains
    
    def _is_valid_domain(self, domain: str) -> bool:
        """验证域名是否有效"""
        # 排除纯 IP 地址
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
            return False
        
        # 过滤黑名单
        for black in self.blacklist:
            if black in domain:
                return False
        
        # 排除明显的变量占位符
        if '{' in domain or '}' in domain or '$' in domain:
            return False
        
        # 必须至少有一个点（排除单个单词）
        if '.' not in domain:
            return False
        
        # 域名长度限制
        if len(domain) < 4 or len(domain) > 253:
            return False
        
        # 必须有合法 TLD（至少 2 个字母）
        parts = domain.split('.')
        if len(parts[-1]) < 2 or not parts[-1].isalpha():
            return False
        
        return True
    
    def extract_all(self) -> List[str]:
        """扫描所有源目录并提取域名"""
        all_domains = set()
        file_count = 0
        
        for spider_dir in self.spider_dirs:
            spider_path = Path(spider_dir)
            if not spider_path.exists():
                print(f"[WARN] 目录不存在: {spider_dir}", file=sys.stderr)
                continue
            
            # 根据目录类型选择文件扩展名
            if 'py' in spider_dir:
                pattern = '*.py'
            elif 'js' in spider_dir:
                pattern = '*.js'
            elif 'php' in spider_dir:
                pattern = '*.php'
            else:
                pattern = '*'
            
            for file_path in spider_path.glob(pattern):
                if file_path.is_file():
                    domains = self.extract_from_file(file_path)
                    all_domains.update(domains)
                    file_count += 1
                    if file_count % 50 == 0:
                        print(f"[INFO] 已扫描 {file_count} 个文件，提取 {len(all_domains)} 个域名")
        
        sorted_domains = sorted(all_domains)
        print(f"[INFO] 扫描完成：{file_count} 个文件，{len(sorted_domains)} 个唯一域名")
        return sorted_domains
    
    def save_domains(self, domains: List[str]):
        """保存域名列表到缓存"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        output_file = self.cache_dir / 'domains.txt'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(domains))
        
        print(f"[INFO] 域名列表已保存: {output_file}")
        print(f"[INFO] 总计 {len(domains)} 个域名")

def main():
    if len(sys.argv) < 2:
        print("用法: python3 extract_domains.py <config.json>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    extractor = DomainExtractor(config_path)
    domains = extractor.extract_all()
    extractor.save_domains(domains)

if __name__ == '__main__':
    main()
