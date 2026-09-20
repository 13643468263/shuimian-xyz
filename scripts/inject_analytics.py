#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给官网全站 HTML 注入统计埋点（幂等、可回滚）

背景：2026-09-20 体检发现官网**零统计埋点**——95 个页面里
      `analytics / tongji / umami / gtag / clarity / busuanzi` 全部 0 命中。
      结果就是「GEO 到底有没有带来人」这个问题根本没法回答（不是没效，是没测）。

站点是纯静态（GitHub Pages），**没有公共 JS 可挂**，
所以必须逐页把埋点代码插进 <head>。本脚本干这件事。

用法：
    1) 把统计服务给的代码存成站点根目录的 analytics_snippet.html
       例：百度统计 →
           <script>
           var _hmt = _hmt || [];
           (function() { var hm = document.createElement("script");
             hm.src = "https://hm.baidu.com/hm.js?你的ID"; ... })();
           </script>
    2) python scripts/inject_analytics.py            # 预览（不写盘）
       python scripts/inject_analytics.py --apply    # 执行（自动备份）
       python scripts/inject_analytics.py --apply --force   # 已注入的强制替换代码

纪律：
  - 幂等：靠 <!-- wb-analytics:start --> 标记判断，重复跑不会插两遍
  - 改前把每个文件备份到 backup_analytics/<时间戳>/
  - 只插 <head>，不动任何正文，插点固定 ⇒ 事后可一键回滚
"""
import os, io, re, sys, shutil, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNIPPET = os.path.join(ROOT, "analytics_snippet.html")
START = "<!-- wb-analytics:start -->"
END = "<!-- wb-analytics:end -->"
SKIP_DIRS = {".git", "backup_index_fix", "backup_analytics", "images", "css"}

APPLY = "--apply" in sys.argv
FORCE = "--force" in sys.argv

log = []
def w(s=""):
    log.append(str(s))
    print(s)


def html_files():
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f.lower().endswith((".html", ".htm")):
                yield os.path.join(dp, f)


def main():
    if not os.path.isfile(SNIPPET):
        w("❌ 找不到埋点代码文件：%s" % SNIPPET)
        w("   请先把统计服务给的代码粘进这个文件，再重跑本脚本。")
        w("   （百度统计：tongji.baidu.com → 管理 → 新增网站 → 复制代码）")
        return 2

    sn = io.open(SNIPPET, encoding="utf-8").read().strip()
    if not sn:
        w("❌ analytics_snippet.html 是空的")
        return 2
    block = "\n  %s\n%s\n  %s\n" % (START, sn, END)

    files = sorted(html_files())
    w("扫描到 %d 个 html 文件" % len(files))
    w("埋点代码长度 = %d 字符" % len(sn))
    w("")

    done, skip, will = [], [], []
    for p in files:
        try:
            h = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception as e:
            w("  ⚠️ 读失败 %s：%s" % (os.path.relpath(p, ROOT), e))
            continue
        if START in h:
            if not FORCE:
                skip.append(p)
                continue
            h2 = re.sub(re.escape(START) + r".*?" + re.escape(END), block.strip(), h, flags=re.S)
            will.append((p, h2))
            continue
        if "</head>" in h:
            h2 = h.replace("</head>", block + "</head>", 1)
        elif "</body>" in h:
            h2 = h.replace("</body>", block + "</body>", 1)
        else:
            w("  ⚠️ 无 </head> 也无 </body>，跳过：%s" % os.path.relpath(p, ROOT))
            continue
        will.append((p, h2))

    w("待注入 = %d 个 ／ 已有埋点跳过 = %d 个" % (len(will), len(skip)))
    for p, _ in will:
        w("   + %s" % os.path.relpath(p, ROOT))

    if not APPLY:
        w("")
        w("（这是预览模式，未写盘。加 --apply 执行）")
        return 0

    if not will:
        w("")
        w("✅ 无需注入，全部页面已带埋点")
        return 0

    ts = time.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(ROOT, "backup_analytics", ts)
    os.makedirs(bdir, exist_ok=True)
    for p, h2 in will:
        rel = os.path.relpath(p, ROOT)
        dst = os.path.join(bdir, rel.replace(os.sep, "__"))
        shutil.copy2(p, dst)
        io.open(p, "w", encoding="utf-8").write(h2)
    w("")
    w("✅ 已注入 %d 个页面；原文件备份在 backup_analytics/%s/" % (len(will), ts))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
