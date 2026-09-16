import os

def update_index():
    path = '.staging/nong/main_python_set_nong/web/index.html'
    with open(path, encoding='utf-8') as f:
        text = f.read()
    
    # Insert timeDrag before timeline
    if 'id="timeDrag"' not in text:
        text = text.replace('<div id="timeline">', '<div id="timeDrag" title="drag to resize the timeline"></div>\n<div id="timeline">')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print("Updated index.html")

def update_css():
    path = '.staging/nong/main_python_set_nong/web/style.css'
    with open(path, encoding='utf-8') as f:
        text = f.read()
    
    if '#timeDrag' not in text:
        css = """#timeDrag{
  flex:0 0 auto;height:14px;cursor:row-resize;touch-action:none;
  background:linear-gradient(to bottom,
    transparent 6px, var(--line) 6px, var(--line) 8px, transparent 8px);
}"""
        text = text.replace('#timeline{', css + '\n#timeline{')
        # modify timeline CSS to have overflow-y:auto and flex-shrink:0
        text = text.replace('#timeline{border-top:1px solid var(--line);background:var(--card);padding:8px 12px}',
                            '#timeline{background:var(--card);padding:8px 12px;overflow-y:auto;flex-shrink:0}')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print("Updated style.css")

def update_notices():
    path = '.staging/nong/main_python_set_nong/web/app_parts/notices.js'
    with open(path, encoding='utf-8') as f:
        text = f.read()
    
    if 'initTimeDrag' not in text:
        code = """
// draggable divider: make the timeline taller or shorter (remembered)
function initTimeDrag() {
  const timePanel = $("timeline"), handle = $("timeDrag");
  const saved = +localStorage.getItem("nong_timeh");
  if (saved) timePanel.style.height = Math.min(600, Math.max(100, saved)) + "px";
  
  const MINH = 100, MAXH = 600, STEP = 16;
  handle.setAttribute("role", "separator");
  handle.setAttribute("aria-orientation", "horizontal");
  handle.setAttribute("aria-label", "Resize the timeline");
  handle.setAttribute("tabindex", "0");
  const announce = () => {
    handle.setAttribute("aria-valuenow", parseInt(timePanel.style.height) || 200);
    handle.setAttribute("aria-valuemin", MINH);
    handle.setAttribute("aria-valuemax", MAXH);
  };
  const setHeight = (h, remember) => {
    timePanel.style.height = Math.min(MAXH, Math.max(MINH, h)) + "px";
    announce();
    resize();                       // keep the 3D canvas matched to the viewport
    if (remember) localStorage.setItem("nong_timeh", parseInt(timePanel.style.height) || 200);
  };
  announce();

  handle.addEventListener("keydown", (e) => {
    const now = parseInt(timePanel.style.height) || 200;
    let h = null;
    if (e.key === "ArrowUp")  h = now + STEP;
    else if (e.key === "ArrowDown") h = now - STEP;
    else if (e.key === "Home")  h = 200;
    else if (e.key === "PageUp") h = now + STEP * 4;
    else if (e.key === "PageDown") h = now - STEP * 4;
    if (h === null) return;
    e.preventDefault();
    setHeight(h, true);
  });

  handle.addEventListener("dblclick", () => {
    timePanel.style.height = ""; // let it size to content
    localStorage.removeItem("nong_timeh");
    resize();
  });

  let dragging = false;
  handle.addEventListener("pointerdown", (e) => {
    dragging = true;
    handle.setPointerCapture(e.pointerId);
  });
  handle.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    // We want the height to increase as we drag UP.
    // The pointer Y is from the top. So the space from the bottom is window.innerHeight - e.clientY
    // Wait, the handle itself takes space. Let's just use window.innerHeight - e.clientY.
    setHeight(window.innerHeight - e.clientY, false);
  });
  handle.addEventListener("pointerup", () => {
    dragging = false;
    localStorage.setItem("nong_timeh", parseInt(timePanel.style.height) || 200);
  });
}
"""
        text = text + '\n' + code
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print("Updated notices.js")

def update_boot():
    path = '.staging/nong/main_python_set_nong/web/app_parts/boot.js'
    with open(path, encoding='utf-8') as f:
        text = f.read()
        
    if 'initTimeDrag();' not in text:
        text = text.replace('initSideDrag();', 'initSideDrag();\n  initTimeDrag();')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print("Updated boot.js")

if __name__ == '__main__':
    update_index()
    update_css()
    update_notices()
    update_boot()
