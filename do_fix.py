def fix_file(filename, replacements):
    with open(filename, encoding='utf-8') as f:
        text = f.read()
    for old, new in replacements:
        text = text.replace(old, new)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)

fix_file('.staging/qc/checks/check_edge_cases.py', [
    ('var box = document.getElementById("loginHere");',
     'var pwd = document.getElementById("loginPass"); if(pwd){pwd.value="${PASSWORD}"; if(typeof appLogin==="function")appLogin();} var box = document.getElementById("loginHere");')
])

fix_file('.staging/qc/checks/check_studio_tabs.py', [
    ('var box = document.getElementById("loginHere");',
     'var pwd = document.getElementById("loginPass"); if(pwd){pwd.value="${PASSWORD}"; if(typeof appLogin==="function")appLogin();} var box = document.getElementById("loginHere");')
])

fix_file('.staging/qc/checks/check_crash_gate.py', [
    ('var bx=document.getElementById("loginHere"); if(bx) { bx.querySelector(".mlPass").value="${PASSWORD}"; bx.querySelector(".mlGo").click(); }',
     'var pwd = document.getElementById("loginPass"); if(pwd){pwd.value="${PASSWORD}"; if(typeof appLogin==="function")appLogin();}')
])

print("Files patched.")
