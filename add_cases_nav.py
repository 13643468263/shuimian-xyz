import os

root = os.path.dirname(os.path.abspath(__file__))
case_link = '<a href="/cases.html">案例</a>'

count = 0
for dirpath, _, filenames in os.walk(root):
    # 跳过隐藏目录与脚本自身
    if '/.git' in dirpath or '\\.git' in dirpath:
        continue
    for fn in filenames:
        if not fn.endswith('.html'):
            continue
        if fn == 'add_cases_nav.py':
            continue
        path = os.path.join(dirpath, fn)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                html = f.read()
        except Exception:
            continue
        if '/cases.html' in html:
            continue  # 已加入口，跳过

        changed = False
        # nav-links: 在「常见问题」后加「案例」
        anchor = '<a href="/faq.html">常见问题</a>'
        if anchor in html:
            html = html.replace(anchor, anchor + '\n      ' + case_link)
            changed = True

        # footer-links: 在「常见问题」后加「案例」（若存在）
        fanchor = '<a href="/faq.html">常见问题</a>'
        if fanchor in html and '<a href="/cases.html">案例</a>' not in html:
            html = html.replace(fanchor, fanchor + '\n    <a href="/cases.html">案例</a>')
            changed = True

        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            count += 1
            print('updated:', os.path.relpath(path, root))

print('total updated:', count)
