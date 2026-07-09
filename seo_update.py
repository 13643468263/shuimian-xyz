#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无忧睡眠站 SEO/GEO 基建补丁：
1. 给首页以外的所有页面(blog/*.html)补 Open Graph + JSON-LD + canonical
2. 生成 robots.txt / sitemap.xml
幂等：已含 og:type 的页面跳过。
"""
import os, re
from urllib.parse import quote

SITE = r"C:\Users\高仰珍\WorkBuddy\2026-05-19-task-12\shuimian-xyz"
BLOG = os.path.join(SITE, "blog")
DOMAIN = "https://shuimian.xyz"

def extract(html, name, pat):
    m = re.search(pat, html, re.S)
    return m.group(1).strip() if m else ""

def add_seo(html, filename):
    if 'og:type' in html:
        return html, False  # 已处理过，跳过

    title = extract(html, 't', r'<title>(.*?)</title>')
    desc  = extract(html, 'd', r'<meta name="description" content="(.*?)"')
    if not desc:
        desc = title

    if filename == 'index.html':
        page_url = f"{DOMAIN}/blog/"
        jsonld_type = "CollectionPage"
    else:
        page_url = f"{DOMAIN}/blog/{quote(filename)}"
        jsonld_type = "Article"

    block = f'''  <link rel="canonical" href="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="zh_CN">
  <meta property="og:site_name" content="无忧睡眠">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{page_url}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc}">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "{jsonld_type}",
    "name": "{title}",
    "headline": "{title}",
    "description": "{desc}",
    "url": "{page_url}",
    "publisher": {{ "@type": "Organization", "name": "无忧睡眠", "url": "{DOMAIN}/" }}
  }}
  </script>
'''

    html = html.replace('</head>', block + '</head>', 1)
    return html, True

# 1. 处理 blog 下所有 html（含 index.html）
files = [f for f in os.listdir(BLOG) if f.endswith('.html')]
changed = 0
for f in files:
    path = os.path.join(BLOG, f)
    with open(path, 'r', encoding='utf-8') as fh:
        html = fh.read()
    new_html, did = add_seo(html, f)
    if did:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(new_html)
        changed += 1
        print(f"✅ SEO 补丁: blog/{f}")
    else:
        print(f"⏭  跳过(已处理): blog/{f}")

# 2. robots.txt
robots = """User-agent: *
Allow: /

Sitemap: {}/sitemap.xml
""".format(DOMAIN)
with open(os.path.join(SITE, "robots.txt"), 'w', encoding='utf-8') as fh:
    fh.write(robots)

# 3. sitemap.xml（首页 + 所有 blog 文章）
urls = [f"  <url>\n    <loc>{DOMAIN}/</loc>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>"]
for f in files:
    if f == 'index.html':
        loc = f"{DOMAIN}/blog/"
    else:
        loc = f"{DOMAIN}/blog/{quote(f)}"
    urls.append(f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>")

sitemap = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
''' + '\n'.join(urls) + '\n</urlset>\n'

with open(os.path.join(SITE, "sitemap.xml"), 'w', encoding='utf-8') as fh:
    fh.write(sitemap)

print(f"\n🎉 完成！{changed} 个页面新增 SEO 基建")
print(f"📄 已生成 robots.txt + sitemap.xml（含 {len(files)} 个页面）")
