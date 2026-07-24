#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无忧睡眠官网站内搜索索引生成器
扫描官网 HTML 页面，提取 title / description / keywords / h1，生成 search.json
"""
import json
import os
import re
from pathlib import Path
from html import unescape

SITE_ROOT = Path("C:/Users/高仰珍/WorkBuddy/2026-07-07-07-26-29/shuimian-xyz")
OUT_FILE = SITE_ROOT / "search.json"
BASE_URL = "https://shuimian.xyz"


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"[\s\n\r\t]+", " ", text)
    return text.strip()


def extract_meta(content: str, name: str) -> str:
    # meta name="description" / name="keywords"
    m = re.search(r'<meta\s+name=["\']' + re.escape(name) + r'["\']\s+content=["\']([^"\']*)["\']', content, re.I)
    if m:
        return clean_text(m.group(1))
    # property="og:description"
    m = re.search(r'<meta\s+property=["\']og:' + re.escape(name) + r'["\']\s+content=["\']([^"\']*)["\']', content, re.I)
    if m:
        return clean_text(m.group(1))
    return ""


def extract_title(content: str) -> str:
    m = re.search(r'<title>(.*?)</title>', content, re.I | re.S)
    if m:
        return clean_text(m.group(1).replace("—", "-").replace("｜", "|"))
    return ""


def extract_h1(content: str) -> str:
    m = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.I | re.S)
    if m:
        txt = re.sub(r'<[^>]+>', '', m.group(1))
        return clean_text(txt)
    return ""


def extract_keywords(content: str) -> list:
    raw = extract_meta(content, "keywords")
    if not raw:
        return []
    parts = re.split(r'[|,，;；]', raw)
    return [p.strip() for p in parts if p.strip()]


def file_to_url(rel_path: Path) -> str:
    p = rel_path.as_posix().lstrip("/")
    return f"{BASE_URL}/{p}"


def build_index():
    docs = []

    # 1. 主要单页
    main_pages = [
        ("index.html", "首页"),
        ("about.html", "关于"),
        ("faq.html", "常见问题"),
        ("cases.html", "案例"),
        ("camp.html", "训练营"),
        ("consultation.html", "预约咨询"),
        ("psqi.html", "PSQI量表"),
        ("manual.html", "失眠自救手册"),
        ("contract.html", "服务协议"),
    ]
    for filename, fallback_title in main_pages:
        p = SITE_ROOT / filename
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8", errors="ignore")
        title = extract_title(content) or fallback_title
        desc = extract_meta(content, "description")
        h1 = extract_h1(content)
        keywords = extract_keywords(content)
        docs.append({
            "title": title,
            "url": file_to_url(Path(filename)),
            "description": desc or h1,
            "keywords": keywords,
            "category": "页面"
        })

    # 2. 测评页
    assess_index = SITE_ROOT / "assess" / "index.html"
    if assess_index.exists():
        content = assess_index.read_text(encoding="utf-8", errors="ignore")
        title = extract_title(content) or "免费失眠分型测评"
        desc = extract_meta(content, "description")
        docs.append({
            "title": title,
            "url": f"{BASE_URL}/assess/",
            "description": desc,
            "keywords": ["测评", "失眠分型", "焦虑型", "生物钟紊乱型", "神经疲劳型", "习惯熬夜型"],
            "category": "工具"
        })

    # 3. blog 文章
    blog_dir = SITE_ROOT / "blog"
    if blog_dir.exists():
        for html_file in sorted(blog_dir.glob("*.html")):
            if html_file.name == "index.html":
                continue
            content = html_file.read_text(encoding="utf-8", errors="ignore")
            title = extract_title(content)
            desc = extract_meta(content, "description")
            h1 = extract_h1(content)
            keywords = extract_keywords(content)
            docs.append({
                "title": title or h1,
                "url": file_to_url(html_file.relative_to(SITE_ROOT)),
                "description": desc or h1,
                "keywords": keywords,
                "category": "文章"
            })

    # 去重 + 排序
    seen = set()
    unique_docs = []
    for d in docs:
        if d["url"] in seen or not d["title"]:
            continue
        seen.add(d["url"])
        unique_docs.append(d)

    unique_docs.sort(key=lambda x: (x["category"] != "工具", x["category"] != "页面", x["title"]))

    OUT_FILE.write_text(json.dumps(unique_docs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {OUT_FILE} with {len(unique_docs)} entries")
    for d in unique_docs[:5]:
        print(" -", d["title"][:30], d["url"])


if __name__ == "__main__":
    build_index()
