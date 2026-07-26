# -*- coding: utf-8 -*-
"""把 GEO 图文 178/179 发布为官网 blog 文章页"""
import os
import re
import json
import shutil
import base64
from datetime import datetime
from urllib.parse import quote

WEB = "C:/Users/高仰珍/WorkBuddy/2026-07-07-07-26-29/shuimian-xyz"
WORK = "C:/Users/高仰珍/WorkBuddy/2026-07-07-07-26-29"
E_DIR = "E:/无忧睡眠/06-内容运营/GEO图文"

# 文章配置
ARTICLES = [
    {
        "md": f"{WORK}/2026-07-22_GEO图文178_睡眠浅易醒怎么改善.md",
        "slug": "睡眠浅易醒怎么改善",
        "date": "2026-07-22",
        "keywords": "睡眠浅, 易醒, 失眠类型, 睡眠感缺失, 半夜醒, CBT-I, 职场女性",
        "og_image": "/images/blog/178_封面_夜空小径.png",
        "section": "症状拆解",
    },
    {
        "md": f"{WORK}/2026-07-22_GEO图文179_职场女性失眠3个隐藏诱因.md",
        "slug": "职场女性失眠3个隐藏诱因",
        "date": "2026-07-22",
        "keywords": "职场女性失眠, 情绪劳动, 屏幕绑定, 周末补觉, 生物钟紊乱, 焦虑型失眠",
        "og_image": "/images/blog/179_封面_职场女性深夜.png",
        "section": "症状拆解",
    },
]


def slugify(name):
    return name


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def copy_images():
    """把 178/179 配图复制到官网 images/blog/"""
    img_dir = os.path.join(WEB, "images", "blog")
    ensure_dir(img_dir)
    copied = []
    # 178
    src178 = os.path.join(WORK, "178配图")
    for f in os.listdir(src178):
        if f.endswith(".png"):
            shutil.copy2(os.path.join(src178, f), os.path.join(img_dir, f))
            copied.append(f)
    # 179
    src179 = os.path.join(WORK, "179配图")
    for f in os.listdir(src179):
        if f.endswith(".png"):
            shutil.copy2(os.path.join(src179, f), os.path.join(img_dir, f))
            copied.append(f)
    print("copied images:", copied)
    return copied


def parse_md(md_path):
    """简单解析 md 为 HTML 片段"""
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    html_parts = []
    i = 0
    in_list = None  # None, 'ul', 'ol'
    list_buffer = []

    def flush_list():
        nonlocal in_list, list_buffer
        if not list_buffer:
            return
        tag = "ul" if in_list == "ul" else "ol"
        items = "\n".join(f"<li>{item}</li>" for item in list_buffer)
        html_parts.append(f"<{tag}>\n{items}\n</{tag}>")
        list_buffer = []
        in_list = None

    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line:
            flush_list()
            continue

        # h1
        if line.startswith("# "):
            flush_list()
            html_parts.append(f"<h1>{inline_fmt(line[2:])}</h1>")
            continue

        # h2
        if line.startswith("## "):
            flush_list()
            html_parts.append(f"<h2>{inline_fmt(line[3:])}</h2>")
            continue

        # image
        m = re.match(r"!\[(.*?)\]\((.*?)\)", line)
        if m:
            flush_list()
            alt, src = m.group(1), m.group(2)
            # 提取文件名
            fname = os.path.basename(src)
            html_parts.append(
                f'<figure class="article-figure">\n'
                f'  <img src="/images/blog/{fname}" alt="{alt}" loading="lazy">\n'
                f'  <figcaption>{alt}</figcaption>\n'
                f'</figure>'
            )
            continue

        # ul item
        if line.startswith("- "):
            if in_list and in_list != "ul":
                flush_list()
            in_list = "ul"
            list_buffer.append(inline_fmt(line[2:]))
            continue

        # ol item
        m_ol = re.match(r"^(\d+)\.\s+(.*)", line)
        if m_ol:
            if in_list and in_list != "ol":
                flush_list()
            in_list = "ol"
            list_buffer.append(inline_fmt(m_ol.group(2)))
            continue

        # Q: / A: FAQ lines
        if line.startswith("Q：") or line.startswith("A："):
            flush_list()
            tag = "strong" if line.startswith("Q：") else "p"
            if line.startswith("Q："):
                html_parts.append(f"<p><strong>Q：{inline_fmt(line[2:])}</strong></p>")
            else:
                html_parts.append(f"<p>A：{inline_fmt(line[2:])}</p>")
            continue

        # plain paragraph
        flush_list()
        html_parts.append(f"<p>{inline_fmt(line)}</p>")

    flush_list()
    return "\n".join(html_parts)


def inline_fmt(text):
    # bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # link
    text = re.sub(
        r"(https?://[^\s]+)",
        r'<a href="\1" target="_blank" rel="noopener">\1</a>',
        text,
    )
    return text


def build_html(article, content_html):
    slug = article["slug"]
    title = slug
    full_title = title + " — 无忧睡眠"
    desc = article.get("description") or re.sub(r"<.*?>", "", content_html)[:100] + "…"
    desc = desc.replace("\"", "&quot;")
    keywords = article["keywords"]
    date = article["date"]
    og_image = article["og_image"]
    url_path = quote(f"/blog/{slug}.html")
    url_full = f"https://shuimian.xyz{url_path}"
    og_image_full = f"https://shuimian.xyz{og_image}"

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{full_title}</title>
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{keywords}">
  <link rel="stylesheet" href="/css/style.css">
  <link rel="canonical" href="{url_full}">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="zh_CN">
  <meta property="og:site_name" content="无忧睡眠科技">
  <meta property="og:title" content="{full_title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{url_full}">
  <meta property="og:image" content="{og_image_full}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{full_title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{og_image_full}">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "name": "{full_title}",
    "headline": "{title}",
    "description": "{desc}",
    "url": "{url_full}",
    "datePublished": "{date}",
    "image": "{og_image_full}",
    "publisher": {{ "@type": "Organization", "name": "太原无忧睡眠科技有限公司", "url": "https://shuimian.xyz/" }},
    "author": {{ "@type": "Person", "name": "高仰珍", "jobTitle": "中科院认证心理咨询师", "affiliation": {{ "@type": "Organization", "name": "太原无忧睡眠科技有限公司" }} }}
  }}
  </script>
  <style>
    .article-figure {{ margin: 28px 0; text-align: center; }}
    .article-figure img {{ max-width: 100%; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
    .article-figure figcaption {{ font-size: 14px; color: #666; margin-top: 10px; }}
  </style>
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <a href="/" class="logo">无忧睡眠<span>科技</span><span class="dot"></span></a>
    <nav class="nav-links">
      <a href="/">首页</a>
      <a href="/blog/">文章</a>
      <a href="/search.html">搜索</a>
      <a href="/assess/">测评</a>
      <a href="/psqi.html">量表</a>
      <a href="/consultation.html" class="nav-cta">预约</a>
      <a href="/faq.html">常见问题</a>
      <a href="/cases.html">案例</a>
      <a href="/about.html">关于</a>
    </nav>
  </div>
</header>

<main class="article-page container">
  <a href="/blog/" class="back-link">← 返回文章列表</a>

  {content_html}

  <div class="cta-box">
    <h3>看了文章还想更深入了解自己的失眠类型？</h3>
    <p>花2分钟做个免费测评，了解根源，比看100篇文章更管用。</p>
    <a href="/assess/" class="btn btn-warm">开始免费测评 →</a>
  </div>
</main>

<footer class="site-footer">
  <div class="footer-brand">无忧睡眠科技</div>
  <p>不靠药物睡好觉 · 56天有人陪你做</p>
  <div class="footer-links">
    <a href="/">首页</a>
    <a href="/blog/">文章</a>
    <a href="/assess/">测评</a>
  </div>
  <p class="footer-copy">&copy; 2026 太原无忧睡眠科技有限公司 · 版权所有</p>
  <div style="text-align:center;font-size:12px;color:#999;padding:12px 0;border-top:1px solid rgba(255,255,255,.1);margin-top:8px;">
    太原无忧睡眠科技有限公司 · 晋ICP备2025055518号-1 · 官网：shuimian.xyz
  </div>
</footer>

</body>
</html>'''


def generate_article_pages():
    for art in ARTICLES:
        content = parse_md(art["md"])
        # 提取 h1 作为页面主标题，其余作为正文
        html = build_html(art, content)
        path = os.path.join(WEB, "blog", f"{art['slug']}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("generated:", path)


def update_blog_index():
    idx_path = os.path.join(WEB, "blog", "index.html")
    with open(idx_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 更新 logo
    html = html.replace(
        '<a href="/" class="logo">无忧<span>睡眠</span><span class="dot"></span></a>',
        '<a href="/" class="logo">无忧睡眠<span>科技</span><span class="dot"></span></a>'
    )

    # 在症状拆解部分追加两篇新文章
    marker = '<li><span class="list-num">09</span><a href="晚上睡不着白天困怎么办.html">晚上睡不着白天困怎么办？</a></li>'
    if marker in html and '睡眠浅易醒怎么改善.html' not in html:
        new_items = '''      <li><span class="list-num">10</span><a href="睡眠浅易醒怎么改善.html">睡眠浅易醒怎么改善？先搞清楚你是“睡得浅”还是“醒得多”</a></li>
      <li><span class="list-num">11</span><a href="职场女性失眠3个隐藏诱因.html">职场女性失眠的3个隐藏诱因：不是你想太多，是白天在偷偷耗你</a></li>'''
        html = html.replace(marker, marker + "\n" + new_items)
        print("updated blog/index.html")
    else:
        print("blog/index.html already updated or marker not found")

    # 更新页脚品牌名
    html = html.replace('<div class="footer-brand">无忧睡眠</div>', '<div class="footer-brand">无忧睡眠科技</div>')

    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(html)


def update_search_json():
    search_path = os.path.join(WEB, "search.json")
    with open(search_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 移除旧条目（如果存在）
    data = [d for d in data if d["url"] not in (
        "/blog/睡眠浅易醒怎么改善.html",
        "/blog/职场女性失眠3个隐藏诱因.html",
    )]

    data.append({
        "title": "睡眠浅易醒怎么改善？先搞清楚你是“睡得浅”还是“醒得多”",
        "url": "/blog/睡眠浅易醒怎么改善.html",
        "description": "睡眠浅、易醒分两种：频繁夜醒和睡眠感缺失。先判断自己是哪一种，再对应调整。",
        "keywords": ["睡眠浅", "易醒", "睡眠感缺失", "半夜醒", "失眠类型", "CBT-I"],
        "category": "文章",
    })
    data.append({
        "title": "职场女性失眠的3个隐藏诱因：不是你想太多，是白天在偷偷耗你",
        "url": "/blog/职场女性失眠3个隐藏诱因.html",
        "description": "情绪劳动超载、屏幕绑定+消息焦虑、周末补觉陷阱，是职场女性失眠最常见的3个白天漏洞。",
        "keywords": ["职场女性失眠", "情绪劳动", "屏幕绑定", "周末补觉", "生物钟紊乱", "焦虑型失眠"],
        "category": "文章",
    })

    with open(search_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("updated search.json, total entries:", len(data))


if __name__ == "__main__":
    copy_images()
    generate_article_pages()
    update_blog_index()
    update_search_json()
    print("done")
