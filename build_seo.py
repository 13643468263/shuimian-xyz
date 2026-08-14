#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无忧睡眠站 SEO 基建补丁 v2（替代旧 seo_update.py，使用相对路径，可重复运行）
1. 全量重建 sitemap.xml（核心静态页 + 全部 blog 文章）
2. 为每篇 blog 文章注入「相关阅读」互链（基于标签匹配，传递权重、辅助收录）
3. 将 JSON-LD 的 @type Article 升级为更规范的 BlogPosting
幂等：已含「相关阅读」的页面跳过互链注入。
"""
import os, re
from urllib.parse import quote

BLOG = "blog"
DOMAIN = "https://shuimian.xyz"

# 核心静态页（纳入 sitemap）
STATIC_PAGES = [
    ("/", 1.0, "weekly"),
    ("/assess/", 0.9, "weekly"),
    ("/psqi.html", 0.9, "monthly"),
    ("/consultation.html", 0.9, "monthly"),
    ("/camp.html", 0.8, "monthly"),
    ("/cases.html", 0.8, "monthly"),
    ("/faq.html", 0.8, "monthly"),
    ("/about.html", 0.8, "monthly"),
    ("/manual-get.html", 0.8, "monthly"),
    ("/blog/", 0.8, "monthly"),
    ("/search.html", 0.5, "monthly"),
]

# 标签规则：标签 -> 触发关键词
TAG_RULES = [
    ("职场女性", ["职场女性"]),
    ("宝妈育儿", ["宝妈", "产后", "陪睡妈妈", "陪睡"]),
    ("倒班轮班", ["倒班", "轮班"]),
    ("学生考生", ["考研", "高考", "考前", "高中生", "大学生", "学生"]),
    ("中老年", ["老年", "退休", "中年"]),
    ("互联网职场", ["程序员", "互联网", "教师", "销售", "业务", "公务员", "体制", "自由职业", "居家"]),
    ("高压创业", ["高压", "创业者", "创业"]),
    ("咖啡因", ["咖啡因"]),
    ("运动", ["运动"]),
    ("认床环境", ["认床"]),
    ("声音敏感", ["声音"]),
    ("更年期女性", ["更年期"]),
    ("安眠药", ["安眠药", "依赖", "长期吃"]),
    ("CBT-I方法", ["CBT-I", "刺激控制", "睡眠限制", "睡眠日记", "认知重构", "PSQI", "分型", "测出失眠分型"]),
    ("焦虑抑郁", ["焦虑", "抑郁"]),
    ("亲历康复", ["康复", "3年", "8年"]),
    ("熬夜", ["报复性熬夜", "熬夜"]),
    ("午睡", ["午睡"]),
    ("睡眠浅易醒", ["睡眠浅", "易醒"]),
    ("时差出差", ["跨时区", "出差", "时差"]),
    ("睡眠科普", ["半夜", "似睡非睡", "习惯性", "压力大", "怎么办", "改善", "障碍", "神经疲劳",
               "四型", "哪一型", "遗传", "做梦", "喝酒", "空调", "吃什么", "倒退", "神经衰弱",
               "长期熬夜", "睡不着", "睡前", "如何改善", "心理咨询", "看什么科", "经常失眠",
               "调理", "睡眠质", "身体很累"]),
]

GENERIC = "睡眠科普"

def tag_article(name):
    tags = []
    for tag, kws in TAG_RULES:
        for kw in kws:
            if kw in name:
                tags.append(tag)
                break
    if not tags:
        tags = [GENERIC]
    return tags

def main():
    files = [f for f in os.listdir(BLOG) if f.endswith('.html') and f != 'index.html']
    meta = {}
    for f in files:
        h = open(os.path.join(BLOG, f), encoding='utf-8', errors='ignore').read()
        m = re.search(r'<title>(.*?)</title>', h, re.S)
        title = m.group(1).strip() if m else f[:-5]
        disp = title.replace(" — 无忧睡眠", "").replace(" —无忧睡眠", "").replace(" | 无忧睡眠", "").strip()
        if not disp:
            disp = f[:-5]
        meta[f] = {"disp": disp, "tags": tag_article(f), "html": h}

    def related(f, n=3):
        a = set(meta[f]["tags"]) - {GENERIC}
        scored = []
        for o, info in meta.items():
            if o == f:
                continue
            b = set(info["tags"]) - {GENERIC}
            common = len(a & b)
            scored.append((common, info["disp"], o))
        scored.sort(key=lambda x: (-x[0], x[1]))
        top = [s for s in scored if s[0] > 0][:n]
        if len(top) < n:
            top += [s for s in scored if s[0] == 0][:n - len(top)]
        return top[:n]

    # 1) 互链注入 + BlogPosting 升级
    linked = 0
    for f in files:
        h = meta[f]["html"]
        if '相关阅读' in h:
            continue  # 已注入，跳过
        rel = related(f)
        items = "".join(
            f'      <li style="padding:10px 0;border-bottom:1px solid #ece6d8;">'
            f'<a href="/blog/{quote(o)}" style="color:#2c3e50;text-decoration:none;font-weight:500;">{d}</a></li>'
            for _, d, o in rel
        )
        block = (
            '  <section class="related-posts" style="margin:36px 0;padding:24px;'
            'background:#f7f4ea;border-radius:12px;">\n'
            '    <h3 style="margin:0 0 8px;font-size:18px;color:#333;">相关阅读</h3>\n'
            '    <ul style="list-style:none;padding:0;margin:0;">\n'
            f'{items}    </ul>\n'
            '  </section>\n'
        )
        if '</main>' in h:
            h = h.replace('</main>', '</main>\n' + block, 1)
        else:
            h = h.replace('</body>', block + '</body>', 1)
        # BlogPosting 升级（仅文章页，不动 CollectionPage）
        h = h.replace('"@type": "Article"', '"@type": "BlogPosting"')
        open(os.path.join(BLOG, f), 'w', encoding='utf-8').write(h)
        linked += 1

    # 2) 重建 sitemap
    urls = []
    for path, pri, cf in STATIC_PAGES:
        urls.append(f'  <url>\n    <loc>{DOMAIN}{path}</loc>\n    <changefreq>{cf}</changefreq>\n    <priority>{pri}</priority>\n  </url>')
    for f in files:
        urls.append(f'  <url>\n    <loc>{DOMAIN}/blog/{quote(f)}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>')
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(urls) + '\n</urlset>\n'
    )
    open("sitemap.xml", 'w', encoding='utf-8').write(sitemap)

    print(f"✅ 互链注入: {linked} 篇")
    print(f"✅ sitemap 重建: {len(urls)} 个 url（静态页 {len(STATIC_PAGES)} + 文章 {len(files)}）")

if __name__ == "__main__":
    main()
