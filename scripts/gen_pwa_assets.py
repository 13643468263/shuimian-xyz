# -*- coding: utf-8 -*-
"""无忧睡眠科技 · PWA 可安装壳（2026-11-07）

🔴 定位：不是新产品、不是新产品线，只是给「已有 12 题测评」加一个能装到手机桌面的入口。
   不新增后端、不新增账号、不新增内容、不动 DNS／备案、不花钱。

🔴 最关键的安全约束：service worker **只处理同源 GET**。
   留资提交是跨域 POST（→ wuyousleep.net/.cloud/database/rest/domestic_leads），
   SW 一律不拦截，避免重演 2026-10-04~10-18「前端提交被拦、14 天留资全漏」。

幂等：可反复运行；已注入过 manifest 的页面不会重复注入。
"""
import os
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "images")
FE = "C:/Windows/Fonts/seguiemj.ttf"

TOP = (14, 30, 58)
BOT = (36, 76, 132)
STAR = (226, 236, 252, 190)

MANIFEST = {
    "name": "无忧睡眠科技 · 失眠分型测评",
    "short_name": "无忧睡眠",
    "description": "2分钟12题，先分清你是哪一种失眠，再动手。",
    "start_url": "/assess/?src=pwa",
    "scope": "/",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#0E1E3A",
    "theme_color": "#0E1E3A",
    "lang": "zh-CN",
    "icons": [
        {"src": "/images/app-icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/images/app-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/images/app-icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        {"src": "/images/app-icon-180.png", "sizes": "180x180", "type": "image/png", "purpose": "any"},
    ],
}

SW = """/* 无忧睡眠 PWA · v1 —— 只缓存同源 GET 静态资源 */
const CACHE = 'wuyou-pwa-v1';
const PRECACHE = ['/', '/assess/', '/manifest.webmanifest', '/images/app-icon-192.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  // 🔴 绝不拦截：非 GET（留资 POST）、跨域（wuyousleep.net 数据库 API）
  if (req.method !== 'GET') return;
  let u;
  try { u = new URL(req.url); } catch (err) { return; }
  if (u.origin !== self.location.origin) return;

  e.respondWith(
    caches.match(req).then((hit) => {
      if (hit) return hit;
      return fetch(req).then((res) => {
        if (res && res.ok && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => caches.match('/assess/'));
    })
  );
});
"""

HEAD_TAGS = """  <link rel="manifest" href="/manifest.webmanifest">
  <meta name="theme-color" content="#0E1E3A">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="无忧睡眠">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="apple-touch-icon" href="/images/app-icon-180.png">
"""
SW_REG = """<script>
/* PWA 注册：失败静默，不影响任何已有功能 */
if ('serviceWorker' in navigator && location.protocol === 'https:') {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  });
}
</script>
"""


def make_icon(size, maskable=False):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    for y in range(size):
        k = y / max(1, size - 1)
        c = tuple(int(TOP[i] + (BOT[i] - TOP[i]) * k) for i in range(3))
        d.line([(0, y), (size, y)], fill=c + (255,))

    # maskable：图形收进中心 80% 安全区，系统裁圆时不会切掉
    scale = 0.78 if maskable else 1.0
    ef = ImageFont.truetype(FE, int(size * 0.52 * scale))
    moon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    md = ImageDraw.Draw(moon)
    t = "🌙"
    b = md.textbbox((0, 0), t, font=ef)
    w, h = b[2] - b[0], b[3] - b[1]
    md.text(((size - w) / 2 - b[0], (size - h) / 2 - b[1] - size * 0.01),
            t, font=ef, embedded_color=True)
    im.alpha_composite(moon)

    for fx, fy, r in [(0.22, 0.20, 0.010), (0.79, 0.26, 0.008), (0.76, 0.75, 0.007)]:
        x, y, rr = int(size * fx), int(size * fy), max(2, int(size * r))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=STAR)
    return im.convert("RGB")


def inject(rel):
    p = os.path.join(ROOT, rel)
    s = open(p, encoding="utf-8").read()
    changed = []
    if 'rel="manifest"' not in s:
        assert "</head>" in s, rel + " 缺 </head>"
        s = s.replace("</head>", HEAD_TAGS + "</head>", 1)
        changed.append("head")
    if "serviceWorker.register('/sw.js')" not in s:
        assert "</body>" in s, rel + " 缺 </body>"
        s = s.replace("</body>", SW_REG + "</body>", 1)
        changed.append("body")
    if changed:
        open(p, "w", encoding="utf-8").write(s)
    print("  注入", rel, "→", "+".join(changed) if changed else "已是最新（幂等跳过）")


def build():
    os.makedirs(IMG_DIR, exist_ok=True)
    for size, name, mask in [(192, "app-icon-192.png", False),
                             (512, "app-icon-512.png", False),
                             (512, "app-icon-maskable-512.png", True),
                             (180, "app-icon-180.png", False)]:
        make_icon(size, mask).save(os.path.join(IMG_DIR, name), quality=95)
        print("  图标", name, size)

    with open(os.path.join(ROOT, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=2)
    print("  manifest.webmanifest")

    with open(os.path.join(ROOT, "sw.js"), "w", encoding="utf-8") as f:
        f.write(SW)
    print("  sw.js（只拦同源 GET，POST/跨域一律放行）")

    inject("index.html")
    inject(os.path.join("assess", "index.html"))
    print("✅ PWA 资产生成完毕")


if __name__ == "__main__":
    build()
