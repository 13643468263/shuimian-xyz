import re
from pathlib import Path

root = Path("C:/Users/高仰珍/WorkBuddy/2026-07-07-07-26-29/shuimian-xyz")
files = list(root.glob("*.html")) + list(root.rglob("*.html"))

changed = []
pattern = re.compile(r'(<a\s+[^>]*?>)训练营(</a>)')

for f in files:
    text = f.read_text(encoding="utf-8")
    new_text, n = pattern.subn(r'\1睡眠力训练营\2', text)
    if n:
        f.write_text(new_text, encoding="utf-8")
        changed.append((f.relative_to(root), n))

print("Changed files:")
for rel, n in changed:
    print(f"  {rel}: {n} replacements")
