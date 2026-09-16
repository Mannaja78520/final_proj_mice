import re
from pathlib import Path

text = Path('docs/PLAN.html').read_text(encoding='utf-8')
i = text.find('<pre id="state"><code>')
j = text.find('</code></pre>', i)
raw = text[i:j]

# HTML entity replacements
raw = raw.replace('&', '&')
raw = raw.replace('<', '<')
raw = raw.replace('>', '>')
raw = raw.replace('"', '"')
raw = raw.replace(''', "'")

for line in raw.split('\n'):
    if ': todo' in line or ': doing' in line:
        print(line.strip())