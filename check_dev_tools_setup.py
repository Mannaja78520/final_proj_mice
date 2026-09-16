import re
text = open('.staging-promote-20260915/qc/checks/check_dev_tools.py', encoding='utf-8').read()
for i, line in enumerate(text.splitlines()):
    if 'qc/checks' in line:
        print("\n".join(text.splitlines()[i:i+20]))
        break
