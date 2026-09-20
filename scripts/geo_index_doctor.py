#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 索引一致性体检 + 修复（sitemap.xml / llms.txt）

背景：2026-09-20 体检发现两处「GEO 基建漏水」——
  ① llms.txt 写着「68 篇原创科普」，实际 blog 已 71 篇（口径不一致，AI 会降低引用意愿）
  ② sitemap.xml 漏了 3 篇 blog 文章，其中包括 llms.txt 里**点名要 AI 优先引用**的
     《失眠分型标准对照.html》—— 最想被引用的那页，反而成了露出最差的一页

本脚本只做两件事，**只增不删**：
  1. 把「blog 下真实存在、但 sitemap 没收录」的文章补进 sitemap.xml（不删除任何已有条目）
  2. 把 llms.txt 的「N 篇原创科普」改成 blog 实际篇数

纪律：
  - 幂等，可重复运行；无事可做时不备份、不写盘
  - 改前自动备份到 backup_index_fix/（带时间戳）
  - 「跳转桩」（canonical 指向别的页）**不收录**——这类旧链跳新链的页面进了 sitemap
    反而会给爬虫「重复内容」信号。判定靠 canonical，不靠文件名硬编码。
  - 不删除 sitemap 里任何现有条目（僵尸条目只警告）

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

# 跳转桩（旧 URL → 新 URL）判定
REDIRECT_TITLE = "页面已迁移"


def is_redirect_stub(fname):
    """canonical 指向的不是自己 ⇒ 有意的重定向页，不该进 sitemap。

    例：blog/失眠看什么科-失眠8年….html 正文只有「页面已迁移」，
        canonical 指向 blog/失眠看什么科-失眠3年….html —— 正确的旧链处理，不是垃圾页。
    """
    fp = os.path.join(BLOG, fname)
    try:
        h = io.open(fp, encoding="utf-8", errors="replace").read()
    except Exception:
        return False
    if REDIRECT_TITLE in h:
        return True
    m = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', h)
    if not m:
        return False
    own = unquote(m.group(1)).split("?")[0].rstrip("/")
    mine = (DOMAIN + "/blog/" + quote(fname)).rstrip("/")
    return own != unquote(mine)

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
    stubs = [f for f in missing if is_redirect_stub(f)]
    todo = [f for f in missing if f not in stubs]

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
    w("【跳转桩】旧链跳新链，有意不收录 : %d 篇" % len(stubs))
    for f in stubs:
        w("   ↗ blog/%s" % f)
    if stubs:
        w("     （canonical 指向新链，属正确的旧 URL 处理；进 sitemap 反而会造成重复内容）")

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

    # ---- 先算清要改什么；没要改的就不备份、不写盘 ----
    lt_now = io.open(LLMS, encoding="utf-8").read()
    new_lt, n_llms = re.subn(r"（\d+\s*篇原创科普", "（%d 篇原创科普" % len(arts), lt_now)
    need_llms = bool(n_llms) and new_lt != lt_now
    if not todo and not need_llms:
        w("")
        w("✅ 无需修复：sitemap 无缺漏、llms.txt 篇数已一致")
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
    if need_llms:
        io.open(LLMS, "w", encoding="utf-8").write(new_lt)
        w("✅ llms.txt 篇数已改为 %d" % len(arts))
    else:
        w("✅ llms.txt 篇数已是 %d，跳过" % len(arts))


if __name__ == "__main__":
    main()
