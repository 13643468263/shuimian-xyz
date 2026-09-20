# -*- coding: utf-8 -*-
"""官网链接体检（link_check.py）

用途：一键确认「官网全站链接都还活着」，放进每周边检。
两层检查：
  ① 本地检查（默认，离线、秒级）：页面里引用的站内文件，在仓库里是否真的存在
  ② 线上检查（加 --online）：再对 https://shuimian.xyz 实测每个路径的状态码

为什么两层都要：
  - ① 能抓「文件被删/改名」这类，不用联网，最快
  - ② 能抓「本地有但没推上去 / CDN 没生效」这类，慢但准

用法：
  python scripts/link_check.py            # 只跑本地
  python scripts/link_check.py --online   # 本地 + 线上实测

退出码：0 = 全通；1 = 有断链（方便接自动化）
注意：中文路径必须做 URL 编码，否则 urllib 会直接抛 UnicodeEncodeError。
"""
import os
import re
import sys
import ssl
import urllib.request
import urllib.error
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://shuimian.xyz"
ONLINE = "--online" in sys.argv

# 站点公开区，脚本自身与备份目录不参与
SKIP_DIRS = {".git", "node_modules", "__pycache__", "scripts", "_backup_beian_20260920"}
BACKUP_PREFIX = "shuimian-xyz_broken-backup"

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49 NetType/WIFI Language/zh_CN")

LINK_ATTR = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"')
LINK_JSON = re.compile(r'https?://(?:www\.)?shuimian\.xyz(/[^\s"\'\\)\],，。;；<>）】」》]*)')
# 行尾易被一起吃进来的标点（中英文括号、逗号、句号等）
TRAILING = '）】」》.,;，。、*\u3000'


def norm(raw):
    """归一化：去域名前缀 / 去 query 与锚点 / 剥尾部标点 / 解码百分号编码"""
    if "shuimian.xyz" in raw:
        raw = raw.split("shuimian.xyz", 1)[1] or "/"
    raw = raw.split("#")[0].split("?")[0]
    raw = raw.rstrip(TRAILING)
    if raw and not raw.startswith("/"):
        raw = "/" + raw
    return urllib.parse.unquote(raw)


def collect():
    """返回 {路径: {来源文件}}，路径以 / 开头"""
    refs = {}
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns
                  if d not in SKIP_DIRS and not d.startswith(BACKUP_PREFIX)]
        for fn in fns:
            if not fn.lower().endswith((".html", ".htm", ".json", ".xml", ".txt")):
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > 4_000_000:
                    continue
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            rel = os.path.relpath(p, ROOT)
            for m in list(LINK_ATTR.finditer(txt)) + list(LINK_JSON.finditer(txt)):
                raw = m.group(1)
                if "://" in raw and "shuimian.xyz" not in raw:
                    continue          # 外链不管
                if raw.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
                    continue
                if not raw.startswith("/") and "shuimian.xyz" not in raw:
                    continue          # 相对路径不查（本站全用绝对路径）
                path = norm(raw)
                if not path.startswith("/") or any(c in path for c in "{}*$ "):
                    continue          # 占位符 / 非法路径
                refs.setdefault(path, set()).add(rel)
    return refs


def local_exists(path):
    rel = path.lstrip("/")
    if rel == "" or path.endswith("/"):
        rel = os.path.join(rel, "index.html")
    return os.path.exists(os.path.join(ROOT, rel.replace("/", os.sep)))


def online_status(path):
    url = BASE + urllib.parse.quote(path, safe="/")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}),
                                   timeout=25, context=ctx)
        return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"ERR:{type(e).__name__}"


def main():
    refs = collect()
    print(f"[1/2] 本地存在性检查 —— 站内引用 {len(refs)} 个不同路径")
    missing = []
    for path in sorted(refs):
        if not local_exists(path):
            missing.append((path, sorted(refs[path])[:3]))
    if missing:
        for path, src in missing:
            print(f"  🔴 本地缺失  {path}   ← {src}")
    else:
        print("  ✅ 全部存在")

    bad_online = []
    if ONLINE:
        print(f"\n[2/2] 线上可访问性检查 —— {len(refs)} 个路径")
        for path in sorted(refs):
            st = online_status(path)
            if st != 200:
                bad_online.append((path, st, sorted(refs[path])[:3]))
                print(f"  🔴 {st}  {path}   ← {sorted(refs[path])[:3]}")
        if not bad_online:
            print("  ✅ 全部 200")
    else:
        print("\n[2/2] 线上检查已跳过（加 --online 启用）")

    print("\n=== 结论 ===")
    if not missing and not bad_online:
        print("官网链接全通 ✅")
        return 0
    print(f"需处理：本地缺失 {len(missing)} 个，线上非200 {len(bad_online)} 个")
    return 1


if __name__ == "__main__":
    sys.exit(main())
