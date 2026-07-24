#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量为官网所有 HTML 页面导航添加"搜索"入口，并修复已知 HTML 语法错误
"""
from pathlib import Path
import re

SITE_ROOT = Path("C:/Users/高仰珍/WorkBuddy/2026-07-07-07-26-29/shuimian-xyz")


def process_file(path: Path):
    content = path.read_text(encoding="utf-8", errors="ignore")
    orig = content

    # 修复已知的语法错误： <a <a href="...">
    content = re.sub(r'<a\s+<a\s+href="/faq\.html">常见问题</a>', '<a href="/faq.html">常见问题</a>', content)

    # 如果已经有搜索入口，跳过
    if '/search.html' in content:
        if content == orig:
            return False
        path.write_text(content, encoding="utf-8")
        return True

    # 在"文章"链接后插入搜索入口
    # 兼容多种写法：/blog/、/blog/index.html
    pattern = r'(<a\s+href="/blog/"[^>]*>文章</a>)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'\1\n      <a href="/search.html">搜索</a>', content, count=1)
        path.write_text(content, encoding="utf-8")
        return True

    return False


def main():
    changed = 0
    for html in SITE_ROOT.rglob("*.html"):
        if process_file(html):
            changed += 1
            print(f"UPDATED: {html.relative_to(SITE_ROOT)}")
    print(f"\nTotal changed: {changed}")


if __name__ == "__main__":
    main()
