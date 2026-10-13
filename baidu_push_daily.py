# -*- coding: utf-8 -*-
"""百度每日推送 10 条（API 配额 10 条/天）

用法：
  python baidu_push_daily.py --dry   只显示本次会推哪些（不推）
  python baidu_push_daily.py         真推

背景（2026-10-12 实测）：
  - sitemap 通道配额 = 0（输入框禁用，无法提交）
  - API 通道可用，配额 10 条/天
  - 故：每天推 10 条未推过的 URL，9 天可推完 sitemap 的 89 条
"""
import json
import os
import sys
import datetime
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

BASE    = r"E:\无忧睡眠\10-测评系统\官网迁移包\shuimian-xyz"
SITEMAP = os.path.join(BASE, "sitemap.xml")
RECORD  = os.path.join(BASE, "_baidu_pushed.json")
SITE    = "https://shuimian.xyz"
TOKEN   = "JPB4zoptoerQoz5k"
API     = "http://data.zz.baidu.com/urls?site=%s&token=%s" % (SITE, TOKEN)
NS      = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
QUOTA   = 10

# 2026-10-12 当天已手工推送的 9 个 URL（初始化用，避免重复推）
INIT_PUSHED = [
    "https://shuimian.xyz/",
    "https://shuimian.xyz/assess/",
    "https://shuimian.xyz/psqi.html",
    "https://shuimian.xyz/consultation.html",
    "https://shuimian.xyz/camp.html",
    "https://shuimian.xyz/cases.html",
    "https://shuimian.xyz/faq.html",
    "https://shuimian.xyz/about.html",
    "https://shuimian.xyz/manual-get.html",
]


def load_urls():
    root = ET.parse(SITEMAP).getroot()
    out = []
    for e in root.findall(".//sm:loc", NS):
        if e.text and e.text.strip():
            out.append(e.text.strip())
    return out


def load_rec():
    if os.path.exists(RECORD):
        try:
            return json.load(open(RECORD, encoding="utf-8"))
        except Exception:
            pass
    rec = {"pushed": list(INIT_PUSHED), "log": [{"date": "2026-10-12", "note": "手工推送 9 条（首页+8 核心页），配额用完"}]}
    json.dump(rec, open(RECORD, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return rec


def save_rec(r):
    json.dump(r, open(RECORD, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    dry = "--dry" in sys.argv
    urls = load_urls()
    rec = load_rec()
    done = set(rec.get("pushed", []))
    todo = [u for u in urls if u not in done]

    print("sitemap 共 %d 条 ｜ 已推 %d 条 ｜ 待推 %d 条" % (len(urls), len(done), len(todo)))
    if not todo:
        print("✅ 全部推完，无需操作")
        return

    batch = todo[:QUOTA]
    print("\n本次推送 %d 条：" % len(batch))
    for u in batch:
        print("   -", u)

    if dry:
        print("\n[--dry] 未真正推送（去掉 --dry 才执行）")
        return

    body = "\n".join(batch).encode("utf-8")
    req = urllib.request.Request(
        API, data=body,
        headers={"Content-Type": "text/plain", "User-Agent": "curl/8.0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            txt = r.read().decode("utf-8", "ignore")
        print("\n返回:", txt)
        d = json.loads(txt)
        ok = d.get("success", 0)
        if ok:
            rec.setdefault("pushed", []).extend(batch[:ok])
            rec.setdefault("log", []).append({
                "date": datetime.date.today().isoformat(),
                "success": ok, "remain": d.get("remain"),
            })
            save_rec(rec)
            total = len(set(rec["pushed"]))
            print("\n✅ 本次成功 %d 条 ｜ 累计已推 %d / %d ｜ 剩余 %d 条待推" % (ok, total, len(urls), len(urls) - total))
        else:
            print("\n⚠️ 无成功条数（可能配额已用完）：", d.get("message", ""))
    except urllib.error.HTTPError as e:
        print("HTTPError", e.code, e.read().decode("utf-8", "ignore"))
    except Exception as e:
        print("失败:", type(e).__name__, e)


if __name__ == "__main__":
    main()
