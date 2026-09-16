import re
text = open('.staging-promote-20260915/qc/checks/check_dev_tools.py', encoding='utf-8').read()
idx = text.find('box')
print(text[idx:idx+1000])
