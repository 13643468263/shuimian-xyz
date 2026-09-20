#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 索引一致性体检 + 修复（sitemap.xml / llms.txt）

背景：2026-09-20 体检发现两处「GEO 基建漏水」——
  ① llms.txt 写着「68 篇原创科普」，实际 blog 已 71 篇（口径不一致，AI 会降低引用意愿）
  ② sitemap.xml 漏了 5 篇 blog 文章，其中包括 llms.txt 里**点名要 AI 优先引用**的
     《失眠分型标准对照.html》—— 最想被引用的那页，反而是露出最差的一页

本脚本只做两件事，**只增不删**：
  1. 把「blog 下真实存在、但 sitemap 没收录」的文章补进 sitemap.xml（不删除任何已有条目）
  2. 把 llms.txt 的「N 篇原创科普」改成 blog 实际篇数

纪律：
  - 幂等，可重复运行
  - 改前自动备份到 backup_index_fix/（带时间戳）
  - 疑似重复/口径错误的页面（KNOWN_BAD）**不自动收录**，只报警列出，等人工决定
  - 不删除 sitemap 里任何现有条目（多出的条目只警告）

用法：
    python scripts/geo_index_doctor.py          # 只体检，不写盘
    python scripts/geo_index_doctor.py --fix    # 修复
"""
import os, re, io, sys, shutil, time
from urllib.parse import quote, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(ROOT, "blog")
DOMAIN = "https://shuimian.xyz"
SITEMAP = os.path.join(ROOT, "sitemap.xml")
LLMS = os.path.join(ROOT, "llms.txt")

# 疑似重复 / 口径错误，不自动收录（人工决定删或改）
# 说明：创始人失眠史是「3 年」，这两篇标题写「8 年」，与全网口径冲突；
#       且各自已有「3 年」版本在 sitemap 里 ⇒ 疑为模板残留，先不收录、只报警。
KNOWN_BAD = {
    "失眠看什么科-失眠8年我跑了6个科室-总结的经验.html",
    "经常失眠怎么调理-我把8年的经验-总结成这一篇.html",
}

FIX = "--fix" in sys.argv
log = []
def w(s=""):
    log.append(str(s))
    print(s)


def blog_articles():
    return sorted(f for f in os.listdir(BLOG)
                  if f.lower().endswith(".html") and f != "index.html")


def sitemap_locs():
    txt = io.open(SITEMAP, encoding="utf-8").read()
    return txt, re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", txt)


def main():
    arts = blog_articles()
    txt, locs = sitemap_locs()
    listed = set()
    for l in locs:
        p = unquote(l.replace(DOMAIN, "").strip())
        listed.add(p.lstrip("/"))

    missing = [f for f in arts if ("blog/" + f) not in listed]
    todo = [f for f in missing if f not in KNOWN_BAD]
    bad_dup = [f for f in missing if f in KNOWN_BAD]

    m_llms = re.search(r"（\d+\s*篇原创科普", io.open(LLMS, encoding="utf-8").read())
    w("=== GEO 索引一致性体检 ===")
    w("blog 文章实际篇数          : %d" % len(arts))
    w("sitemap 现有条目           : %d" % len(locs))
    w("llms.txt 当前写法          : %s" % (
        m_llms.group(0) if m_llms else "（未找到「N 篇原创科普」写法）"))
    w("")
    w("【缺收录】应补进 sitemap     : %d 篇" % len(todo))
    for f in todo:
        w("   + blog/%s" % f)
    w("【疑似重复/口径错】不自动收录 : %d 篇" % len(bad_dup))
    for f in bad_dup:
        w("   ⚠️ blog/%s" % f)

    # sitemap 里列了但文件不存在的（只警告，不删）
    stale = []
    for l in locs:
        p = unquote(l.replace(DOMAIN, "").strip())
        if p.endswith("/") or p == "":
            continue
        fp = os.path.join(ROOT, p.lstrip("/").replace("/", os.sep))
        if not os.path.isfile(fp):
            stale.append(p)
    if stale:
        w("【僵尸条目】sitemap 列了但文件不存在 : %d 条（只警告，不自动删）" % len(stale))
        for s in stale:
            w("   ? %s" % s)

    if not FIX:
        w("")
        w("（这是体检模式，未写盘。加 --fix 执行修复）")
        return

    # ---- 备份 ----
    bdir = os.path.join(ROOT, "backup_index_fix")
    os.makedirs(bdir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    n_backup = 0
    for p in (SITEMAP, LLMS):
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(bdir, "%s.%s.bak" % (os.path.basename(p), ts)))
            n_backup += 1
    w("")
    w("已备份 %d 个文件 → backup_index_fix/（时间戳 %s）" % (n_backup, ts))

    # ---- 1. 补 sitemap ----
    if todo:
        add = "\n".join(
            '  <url>\n    <loc>%s/blog/%s</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>'
            % (DOMAIN, quote(f)) for f in todo)
        new = txt.replace("</urlset>", add + "\n</urlset>", 1)
        assert new != txt, "sitemap 追加失败：没找到 </urlset>"
        io.open(SITEMAP, "w", encoding="utf-8").write(new)
        w("✅ sitemap 补入 %d 篇" % len(todo))
    else:
        w("✅ sitemap 无缺漏，跳过")

    # ---- 2. 修 llms.txt 篇数 ----
    lt = io.open(LLMS, encoding="utf-8").read()
    new_lt, n = re.subn(r"（\d+\s*篇原创科普", "（%d 篇原创科普" % len(arts), lt)
    if n and new_lt != lt:
        io.open(LLMS, "w", encoding="utf-8").write(new_lt)
        w("✅ llms.txt 篇数已改为 %d" % len(arts))
    else:
        w("✅ llms.txt 篇数已是 %d，跳过" % len(arts))


if __name__ == "__main__":
    main()
