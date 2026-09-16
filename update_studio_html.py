import os, re

base_dir = '.staging/nong/main_python_set_nong/web'
with open(f'{base_dir}/app.js', encoding='utf-8') as f:
    js = f.read()

sections = re.split(r'\n// -{30,} (.*?)\n', js)

html = ['<script src="app_parts/00_header.js"></script>']
with open(f'{base_dir}/app_parts/00_header.js', 'w', encoding='utf-8') as f:
    f.write(sections[0])

for i in range(1, len(sections), 2):
    name = sections[i].strip()
    filename = re.sub(r'[^a-zA-Z0-9_]+', '_', name.lower()).strip('_')
    html.append(f'<script src="app_parts/{filename}.js"></script>')

with open(f'{base_dir}/index.html', encoding='utf-8') as f:
    idx = f.read()

idx = idx.replace('<script src="app.js"></script>', '\n'.join(html))

with open(f'{base_dir}/index.html', 'w', encoding='utf-8') as f:
    f.write(idx)

os.remove(f'{base_dir}/app.js')

