with open('.staging/nong/main_python_set_nong/web/index.html', encoding='utf-8') as f:
    text = f.read().encode('ascii', 'ignore').decode()
for line in text.split('\n'):
    if 'id=' in line and 'login' in line.lower():
        print(line.strip())
