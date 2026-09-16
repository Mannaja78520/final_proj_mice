import re
text = open('nong/main_python_set_nong/web/index.html', encoding='utf-8').read()
tabs = re.findall(r'<div id="tab([^"]+)"', text)
print(tabs)

