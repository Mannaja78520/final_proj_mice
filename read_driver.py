import re
with open('.staging/qc/checks/check_login_anywhere.py', encoding='utf-8') as f:
    text = f.read()
match = re.search(r'DRIVER = .*?\"\"\"', text, re.DOTALL)
if match:
    print(match.group(0))

