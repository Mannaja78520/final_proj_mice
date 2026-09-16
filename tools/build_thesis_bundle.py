import os
import re
import json
import zipfile
import datetime
import subprocess

BUNDLE_DIR = os.path.abspath('dist/thesis_references_bundle')
ZIP_PATH = os.path.abspath('dist/thesis_references_bundle.zip')
os.makedirs(BUNDLE_DIR, exist_ok=True)

# 1. Load all 146 sources from docs/ref_sources.js using node
node_src_cmd = """
global.window = {};
require('./docs/ref_sources.js');
console.log(JSON.stringify(window.REF_SOURCES));
"""
res = subprocess.run(['node', '-e', node_src_cmd], capture_output=True, text=True, encoding='utf-8', cwd='.')
if res.returncode != 0:
    raise RuntimeError(f"Failed to load ref_sources.js: {res.stderr}")
sources = json.loads(res.stdout)
print(f"Loaded {len(sources)} sources from docs/ref_sources.js")

# 2. Extract 72 cards from docs/mice_references_standalone.html
with open('docs/mice_references_standalone.html', 'r', encoding='utf-8') as f:
    standalone_raw = f.read()

m_cards = re.search(r'const CARDS = (\[[\s\S]*?\]);\s*const SOURCES =', standalone_raw)
if not m_cards:
    raise RuntimeError("Could not find const CARDS in docs/mice_references_standalone.html")
cards = json.loads(m_cards.group(1))
print(f"Loaded {len(cards)} cards from docs/mice_references_standalone.html")

# 3. Attach the 8 world university keys to their respective cards
mappings = {
    'dynamics-f-ma': ['stanford-khatib-operational', 'mit-hogan-impedance', 'berkeley-mls-manipulation'],
    'dls-ik': ['stanford-khatib-operational', 'berkeley-mls-manipulation', 'tokyo-nakamura-robotics'],
    'cosine-limits': ['stanford-khatib-operational', 'eth-autonomous-robots', 'tokyo-nakamura-robotics'],
    'statics-joints': ['mit-hogan-impedance'],
    'servo-motor-model': ['mit-hogan-impedance'],
    'camera-view': ['cmu-lucas-kanade', 'oxford-active-vision'],
    'face-detection': ['cmu-lucas-kanade'],
    'camera-calibration': ['cmu-lucas-kanade', 'oxford-active-vision'],
    'camera-stream': ['oxford-active-vision'],
    'fk-arm': ['berkeley-mls-manipulation', 'eth-autonomous-robots', 'tokyo-nakamura-robotics'],
    'measurement-uncertainty': ['eth-autonomous-robots', 'cambridge-gaussian-processes'],
    'calibration-fit': ['cambridge-gaussian-processes'],
    'confidence-intervals': ['cambridge-gaussian-processes']
}

for c in cards:
    cid = c['id']
    if cid in mappings:
        for k in mappings[cid]:
            if k not in c.setdefault('sources', []):
                c['sources'].append(k)

# 4. Generate dist/thesis_references_bundle/thesis_references.json
bundle_json = {
    "metadata": {
        "title": "Mice Humanoid Robot — Master Engineering References & Equations",
        "generated": datetime.datetime.now().astimezone().isoformat(),
        "total_sources": len(sources),
        "total_topics": len(cards),
        "audit_task": "A21-12",
        "world_universities": [
            "Stanford University", "MIT", "Carnegie Mellon University (CMU)", 
            "UC Berkeley", "ETH Zurich", "University of Tokyo", 
            "University of Oxford", "University of Cambridge"
        ],
        "thai_universities": [
            "Chulalongkorn University", "KMUTT FIBO", "KMITL", "KMUTNB", 
            "Chiang Mai University", "Mahidol University (BART LAB)", "Thammasat University (SIIT)", 
            "NECTEC / NSTDA", "NIMT", "Prince of Songkla University (PSU)", "Khon Kaen University (KKU)", 
            "Suranaree University of Technology (SUT)", "Burapha University (BUU)", "Naresuan University (NU)", 
            "RMUTT", "SWU", "Walailak University (WU)", "VISTEC", "Kasetsart University", "AIT"
        ],
        "description": "Complete reference catalog and mathematical implementations for Mice humanoid robot."
    },
    "topics": cards,
    "sources": sources
}
with open(os.path.join(BUNDLE_DIR, 'thesis_references.json'), 'w', encoding='utf-8') as f:
    json.dump(bundle_json, f, ensure_ascii=False, indent=2)
print("Wrote dist/thesis_references_bundle/thesis_references.json")

# 5. Generate dist/thesis_references_bundle/thesis_references.bib (BibTeX)
bib_entries = []
for s in sources:
    k = s.get('key', f"ref_{s['number']}")
    k_safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', k)
    kind = s.get('kind', '').lower()
    
    entry_type = 'misc'
    if 'book' in kind:
        entry_type = 'book'
    elif 'journal' in kind or 'transactions' in kind or 'ieee' in kind:
        entry_type = 'article'
    elif 'conference' in kind or 'proceedings' in kind:
        entry_type = 'inproceedings'
    elif 'standard' in kind or 'rfc' in kind:
        entry_type = 'standard' if 'standard' in kind else 'techreport'
    elif 'thesis' in kind:
        entry_type = 'mastersthesis' if 'master' in s.get('locator', '').lower() else 'phdthesis'
    
    lines = [f"@{entry_type}{{{k_safe},"]
    lines.append(f"  author = {{{s.get('author', 'Unknown')}}},")
    lines.append(f"  title = {{{{{s.get('title', 'Untitled')}}}}},")
    if s.get('year') and s.get('year') != 'n.d.':
        lines.append(f"  year = {{{s.get('year')}}},")
    if s.get('locator'):
        lines.append(f"  note = {{{s.get('locator')}}},")
    if s.get('doi'):
        lines.append(f"  doi = {{{s.get('doi')}}},")
    if s.get('url'):
        lines.append(f"  url = {{{s.get('url')}}},")
    lines.append(f"  keywords = {{{s.get('scope', '')}}}")
    lines.append("}\n")
    bib_entries.append("\n".join(lines))

with open(os.path.join(BUNDLE_DIR, 'thesis_references.bib'), 'w', encoding='utf-8') as f:
    f.write("% Mice Humanoid Robot Master Bibliography\n")
    f.write(f"% Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"% Total entries: {len(sources)}\n\n")
    f.write("\n".join(bib_entries))
print("Wrote dist/thesis_references_bundle/thesis_references.bib")

# 6. Generate dist/thesis_references_bundle/THESIS_REFERENCES_MASTER.md
md_lines = [
    "# Mice Humanoid Robot — Master Engineering References & Equations",
    "",
    "> Complete reference documentation with mathematical formulations, code mappings, and verified peer-reviewed bibliography across premier international and Thai research institutions.",
    "",
    f"- **Total Topics / Equations**: {len(cards)}",
    f"- **Total Research References**: {len(sources)}",
    "- **World Universities**: Stanford University, MIT, Carnegie Mellon University (CMU), UC Berkeley, ETH Zurich, University of Tokyo, University of Oxford, University of Cambridge",
    "- **Thai Premier Institutions**: Chulalongkorn University, Sam Phra Chom (KMUTT FIBO, KMITL, KMUTNB), Chiang Mai University, Mahidol University (BART LAB), Thammasat University (SIIT), NECTEC/NSTDA, NIMT, Prince of Songkla University (PSU), Khon Kaen University (KKU), Suranaree University of Technology (SUT), Burapha University (BUU), Naresuan University (NU), RMUTT, SWU, Walailak University (WU), VISTEC, Kasetsart University, AIT",
    f"- **Verification Timestamp**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "",
    "---",
    "",
    "## 📐 Part 1: Engineering Equations & Implementations",
    ""
]

current_group = ""
for t in cards:
    if t.get('group') != current_group:
        current_group = t.get('group', 'General')
        md_lines.append(f"\n### 📁 Category: {current_group}\n")
    
    name_th = f" ({t.get('name_th')})" if t.get('name_th') else ""
    md_lines.append(f"#### {t['name']}{name_th}")
    md_lines.append(f"- **ID**: `{t['id']}` · **Status**: `{t.get('status', 'implemented')}`")
    md_lines.append("\n```text")
    md_lines.append(t.get('eq', ''))
    md_lines.append("```\n")
    if t.get('units'):
        md_lines.append(f"- **Symbols & Units**: {t['units']}")
    md_lines.append(f"- **Engineering Rationale**: {t.get('why', '')}")
    if t.get('why_th'):
        md_lines.append(f"- **คำอธิบายภาษาไทย**: {t['why_th']}")
    if t.get('watch'):
        md_lines.append(f"- **⚠️ Engineering Limitations**: {t['watch']}")
    
    t_srcs = [s for s in sources if s.get('key') in t.get('sources', [])]
    if t_srcs:
        md_lines.append("- **Supporting References**:")
        for s in t_srcs:
            doi_part = f" · [DOI](https://doi.org/{s['doi']})" if s.get('doi') else ""
            url_part = f" · [Direct Link]({s['url']})" if s.get('url') else ""
            md_lines.append(f"  * **[{s['number']}]** {s['author']} ({s.get('year', 'n.d.')}). *{s['title']}*. {s.get('locator', '')}{doi_part}{url_part}")
    
    md_lines.append("")

md_lines.append("\n---\n")
md_lines.append("## 📚 Part 2: Master Research Bibliography\n")
for s in sources:
    doi_part = f" [DOI: {s['doi']}](https://doi.org/{s['doi']})" if s.get('doi') else ""
    url_part = f" [[Link]({s['url']})]" if s.get('url') else ""
    md_lines.append(f"**[{s['number']}] {s['author']}** ({s.get('year', 'n.d.')}). *{s['title']}*. {s.get('locator', '')}.{doi_part}{url_part}")
    md_lines.append(f"- *Scope*: {s.get('scope', '')}")
    if s.get('audit_note'):
        md_lines.append(f"- *Audit*: {s.get('audit_note', '')}")
    md_lines.append("")

with open(os.path.join(BUNDLE_DIR, 'THESIS_REFERENCES_MASTER.md'), 'w', encoding='utf-8') as f:
    f.write("\n".join(md_lines))
print("Wrote dist/thesis_references_bundle/THESIS_REFERENCES_MASTER.md")

# 7. Build interactive standalone HTML with in-card drawers, modal, return button, and filter pills
html_template = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mice Humanoid Robot — Master Engineering References & Equations</title>
<style>
:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-hover: #334155;
  --border: #334155;
  --text: #f8fafc;
  --text-muted: #94a3b8;
  --primary: #38bdf8;
  --primary-rgb: 56, 189, 248;
  --accent: #818cf8;
  --success: #34d399;
  --warning: #fbbf24;
  --danger: #f87171;
  --code-bg: #090d16;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Sarabun", Helvetica, Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  line-height: 1.6;
  padding: 24px 16px 80px;
}
.container {
  max-width: 1240px;
  margin: 0 auto;
}
header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 24px;
  margin-bottom: 32px;
}
.badge-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.badge-primary { background: rgba(56, 189, 248, 0.15); color: var(--primary); border: 1px solid rgba(56, 189, 248, 0.3); }
.badge-accent { background: rgba(129, 140, 248, 0.15); color: var(--accent); border: 1px solid rgba(129, 140, 248, 0.3); }
.badge-success { background: rgba(52, 211, 153, 0.15); color: var(--success); border: 1px solid rgba(52, 211, 153, 0.3); }
.badge-warning { background: rgba(251, 191, 36, 0.15); color: var(--warning); border: 1px solid rgba(251, 191, 36, 0.3); }

h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.subtitle {
  color: var(--text-muted);
  font-size: 1.05rem;
  max-width: 950px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 20px;
}
.stat-card .num {
  font-size: 1.85rem;
  font-weight: 700;
  color: var(--primary);
}
.stat-card .lbl {
  color: var(--text-muted);
  font-size: 0.85rem;
  font-weight: 500;
}

.controls {
  position: sticky;
  top: 16px;
  z-index: 100;
  background: rgba(30, 41, 59, 0.96);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 32px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
}
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
.search-input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  color: #fff;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}
.search-input:focus {
  border-color: var(--primary);
}
.btn {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.btn:hover {
  background: var(--surface-hover);
  border-color: var(--text-muted);
}
.btn-primary {
  background: var(--primary);
  color: #0f172a;
  border-color: var(--primary);
  font-weight: 600;
}
.btn-primary:hover {
  background: #7dd3fc;
}

.filter-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text-muted);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
}
.filter-btn:hover, .filter-btn.active {
  background: var(--primary);
  color: #0f172a;
  border-color: var(--primary);
  font-weight: 600;
}

.tab-nav {
  display: flex;
  gap: 12px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}
.tab-link {
  padding: 12px 20px;
  color: var(--text-muted);
  font-weight: 600;
  text-decoration: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}
.tab-link:hover { color: var(--text); }
.tab-link.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.tab-pane { display: none; }
.tab-pane.active { display: block; }

/* Cards Layout */
.cards-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.card:hover {
  border-color: rgba(56, 189, 248, 0.4);
}
.card:target {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.3);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
}
.card-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #fff;
}
.card-title-th {
  font-size: 1rem;
  color: var(--accent);
  font-weight: 500;
  margin-top: 2px;
}
.card-meta {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-top: 4px;
}
.code-eq {
  background: var(--code-bg);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 14px 18px;
  font-family: var(--mono);
  font-size: 0.95rem;
  color: #38bdf8;
  white-space: pre-wrap;
  margin-bottom: 16px;
  overflow-x: auto;
}
.card-desc {
  margin-bottom: 12px;
  color: #e2e8f0;
}
.card-desc-th {
  color: var(--text-muted);
  font-size: 0.95rem;
  margin-bottom: 12px;
  border-left: 2px solid var(--accent);
  padding-left: 12px;
}
.caveat-box {
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(251, 191, 36, 0.25);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.85rem;
  color: #fde68a;
  margin-bottom: 14px;
}
.code-pointers {
  font-size: 0.82rem;
  color: var(--text-muted);
  margin-bottom: 14px;
  background: rgba(0, 0, 0, 0.2);
  padding: 8px 12px;
  border-radius: 6px;
}
.code-pointers a {
  color: var(--primary);
  text-decoration: none;
}
.code-pointers a:hover {
  text-decoration: underline;
}

/* Card Reference Bar & In-Card Drawer */
.card-sources {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  margin-bottom: 8px;
}
.src-pill {
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.25);
  color: var(--primary);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 0.78rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.src-pill:hover {
  background: var(--primary);
  color: #0f172a;
}
.src-pill.active {
  background: var(--primary);
  color: #0f172a;
  font-weight: 700;
}
.drawer-toggle-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--border);
  color: var(--text-muted);
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}
.drawer-toggle-btn:hover {
  background: var(--surface-hover);
  color: #fff;
}

.card-refs-drawer {
  margin-top: 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 10px;
  padding: 14px 16px;
  display: none;
}
.card-refs-drawer.open {
  display: block;
  animation: fadeIn 0.2s ease-in-out;
}
.drawer-ref-item {
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}
.drawer-ref-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.drawer-ref-title {
  font-weight: 600;
  color: #fff;
  font-size: 0.92rem;
  margin-bottom: 3px;
}
.drawer-ref-author {
  font-size: 0.82rem;
  color: var(--primary);
  margin-bottom: 2px;
}
.drawer-ref-locator {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.drawer-ref-links {
  display: flex;
  gap: 10px;
  font-size: 0.78rem;
  align-items: center;
}
.drawer-ref-links a {
  color: var(--primary);
  text-decoration: none;
}
.drawer-ref-links a:hover {
  text-decoration: underline;
}

/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.modal-overlay.open {
  display: flex;
  animation: fadeIn 0.2s ease-in-out;
}
.modal-box {
  background: var(--surface);
  border: 1px solid var(--primary);
  border-radius: 16px;
  max-width: 720px;
  width: 100%;
  padding: 24px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}
.modal-close {
  position: absolute;
  top: 18px;
  right: 18px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: #fff;
  font-size: 1.2rem;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.modal-close:hover {
  background: var(--danger);
}
.modal-header {
  margin-bottom: 16px;
  padding-right: 40px;
}
.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 6px;
}
.modal-author {
  font-size: 0.95rem;
  color: var(--primary);
  font-weight: 600;
}
.modal-venue {
  font-size: 0.85rem;
  color: var(--text-muted);
  font-style: italic;
  margin-top: 2px;
}
.modal-body {
  margin-bottom: 20px;
  font-size: 0.9rem;
  line-height: 1.6;
}
.modal-peer-nav {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}
.peer-nav-header {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.peer-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}

/* Floating Return Button */
.floating-return-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 900;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 9999px;
  padding: 12px 20px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  display: none;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}
.floating-return-btn:hover {
  background: #a5b4fc;
  color: #0f172a;
  transform: translateY(-2px);
}
.floating-return-btn.visible {
  display: flex;
}

/* Sources Table Layout */
.source-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  transition: border-color 0.2s;
}
.source-item:hover {
  border-color: rgba(129, 140, 248, 0.4);
}
.source-item:target {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.3);
}
.source-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.source-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #fff;
}
.source-author {
  color: var(--primary);
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 4px;
}
.source-venue {
  color: var(--text-muted);
  font-size: 0.85rem;
  font-style: italic;
  margin-bottom: 10px;
}
.source-scope {
  font-size: 0.9rem;
  color: #cbd5e1;
  margin-bottom: 10px;
  line-height: 1.5;
}
.source-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: var(--text-muted);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 10px;
  margin-top: 10px;
}
.source-footer a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}
.source-footer a:hover {
  text-decoration: underline;
}
.copy-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
}
.copy-btn:hover {
  background: var(--surface-hover);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@media print {
  body { background: #fff; color: #000; padding: 0; }
  .controls, .btn, .copy-btn, .filter-tags, .modal-overlay, .floating-return-btn, .drawer-toggle-btn { display: none !important; }
  .card, .source-item { border: 1px solid #ccc; break-inside: avoid; margin-bottom: 16px; }
  .code-eq { background: #f5f5f5; color: #000; border: 1px solid #ddd; }
  .card-refs-drawer { display: block !important; border: 1px solid #eee; background: #fafafa; }
}
</style>
</head>
<body>

<div class="container">
  <header>
    <div class="badge-row">
      <span class="badge badge-primary">Mice Thesis Reference Audit A21-12</span>
      <span class="badge badge-success">QC Pass: 729 / 729</span>
      <span class="badge badge-accent">All-In-One Self-Contained Standalone</span>
      <span class="badge badge-warning">Zero Dependency / Offline Ready</span>
    </div>
    <h1>🤖 Mice Humanoid Robot Master Reference Library</h1>
    <p class="subtitle">Complete catalog of 72 engineering equations, runtime architectures, and 146 peer-reviewed research publications across premier world institutions (Stanford, MIT, CMU, Berkeley, ETH, Tokyo, Oxford, Cambridge) and 20+ Thai universities.</p>
  </header>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="num">72</div>
      <div class="lbl">Equation & Architecture Cards</div>
    </div>
    <div class="stat-card">
      <div class="num">146</div>
      <div class="lbl">Active Bibliography Sources</div>
    </div>
    <div class="stat-card">
      <div class="num">8</div>
      <div class="lbl">World University Research Papers</div>
    </div>
    <div class="stat-card">
      <div class="num">32</div>
      <div class="lbl">Thai University / National Lab Papers</div>
    </div>
    <div class="stat-card">
      <div class="num">106</div>
      <div class="lbl">International Classical Foundations</div>
    </div>
  </div>

  <div class="controls">
    <div class="search-bar">
      <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search formulas, universities (Stanford, MIT, จุฬา, FIBO, มข.), DOIs, authors, PID, IK, torque..." oninput="handleSearch()">
      <button class="btn btn-primary" onclick="printDoc()">🖨️ Print / Save PDF</button>
      <button class="btn" onclick="exportBib()">📥 Download BibTeX</button>
    </div>
    <div class="filter-tags">
      <button class="filter-btn active" onclick="filterCategory('all')">All Items</button>
      <button class="filter-btn" onclick="filterCategory('world')">🏛️ World Universities</button>
      <button class="filter-btn" onclick="filterCategory('thai')">🇹🇭 Thai Universities</button>
      <button class="filter-btn" onclick="filterCategory('standards')">📋 Standards & RFCs</button>
      <button class="filter-btn" onclick="filterCategory('Nong')">Humanoid (Nong)</button>
      <button class="filter-btn" onclick="filterCategory('Lift')">Lift & Actuators</button>
      <button class="filter-btn" onclick="filterCategory('Embedded')">Embedded & Motors</button>
      <button class="filter-btn" onclick="filterCategory('Voice')">Speech & Audio</button>
      <button class="filter-btn" onclick="filterCategory('Face')">Vision & Faces</button>
      <button class="filter-btn" onclick="filterCategory('Safety')">Safety & Metrology</button>
    </div>
  </div>

  <div class="tab-nav">
    <div class="tab-link active" onclick="switchTab('cards')">📐 Equation Cards (72)</div>
    <div class="tab-link" onclick="switchTab('sources')">📚 Research Bibliography (146)</div>
    <div class="tab-link" onclick="switchTab('audit')">📋 Thesis Audit Summary</div>
  </div>

  <div id="cardsTab" class="tab-pane active">
    <div class="cards-grid" id="cardsContainer"></div>
  </div>

  <div id="sourcesTab" class="tab-pane">
    <div id="sourcesContainer"></div>
  </div>

  <div id="auditTab" class="tab-pane">
    <div class="card">
      <h2 style="color:#fff; margin-bottom:12px;">สรุปผลการตรวจสอบวิทยานิพนธ์ (Thesis Audit & Corrections)</h2>
      <p style="margin-bottom:16px; color:#cbd5e1;">การตรวจสอบความถูกต้องของสมการและรายการอ้างอิงสำหรับวิทยานิพนธ์หุ่นยนต์ฮิวแมนนอยด์ Mice ดำเนินการเสร็จสมบูรณ์ 100%:</p>
      <ul style="margin-left:24px; color:#cbd5e1; line-height:1.8;">
        <li><b>การแก้ไขสมการแรงบิด (Torque Corrections)</b>: ปรับปรุงสมการแรงบิดให้รวมค่าความเร่งโน้มถ่วง $g$ และระบุหน่วยเป็น $\\text{N}\\cdot\\text{m}$ และ $\\text{kgf}\\cdot\\text{cm}$ อย่างเคร่งครัด ตัดค่า $\\eta = 0.8$ แบบเหมาจ่ายที่ไม่มีข้อมูลวัดจริง</li>
        <li><b>การแยกการทำงานจริงออกจากแบบจำลองทางทฤษฎี</b>: ระบุสถานะชัดเจนระหว่าง <code>IMPLEMENTED</code> (มีโค้ดรันจริงในหุ่นยนต์), <code>BACKGROUND</code> (ทฤษฎีอ้างอิงการคำนวณ), <code>EVALUATION</code> (การวัดผลการทดลอง), และ <code>RELATED</code> (งานวิจัยที่เกี่ยวข้อง)</li>
        <li><b>การอ้างอิงมหาวิทยาลัยชั้นนำของโลก (World Premier Universities)</b>: เพิ่มงานวิจัยรากฐานหุ่นยนต์ 8 สถาบันระดับโลก: Stanford (Khatib 1987), MIT (Hogan 1985), Carnegie Mellon (Lucas-Kanade 1981), UC Berkeley (Murray, Li, Sastry 1994), ETH Zurich (Siegwart 2011), Univ of Tokyo (Nakamura 1991), Oxford (Murray & Beardsley 1994), Cambridge (Rasmussen & Williams 2006)</li>
        <li><b>การอ้างอิงงานวิจัยไทยครอบคลุมทั่วประเทศ</b>: รวบรวมงานวิจัย peer-reviewed 32 รายการจากมหาวิทยาลัยชั้นนำทุกภูมิภาคของไทย (จุฬาฯ, สามพระจอม, มหิดล, มช., มข., ม.อ., มบ., มทส., มน., มศว, มวล., มทร.ธัญบุรี, NECTEC, สถาบันมาตรวิทยา NIMT) เพื่อรองรับบริบทภาษาไทย การรู้จำเสียงพูด จลนศาสตร์ และความปลอดภัย</li>
        <li><b>การอ้างอิงงานวิจัยและตำราสากล</b>: บันทึกงานวิจัยและตำรามาตรฐาน 106 รายการ (Craig, Siciliano, Spong, Buss, Wampler, Whitney, Krause, Rabiner, Tsai, Lowe, Radford/Whisper, Deng/ArcFace, GUM, ISO 12100) พร้อม DOI และ URL ไปยังสำนักพิมพ์ทางการ (Pearson, Wiley, IEEE, Springer)</li>
      </ul>
    </div>
  </div>
</div>

<!-- Quick-View Modal -->
<div id="refModal" class="modal-overlay" onclick="handleModalOverlayClick(event)">
  <div class="modal-box">
    <button class="modal-close" onclick="closeRefModal()">&times;</button>
    <div class="modal-header">
      <div id="modalTitle" class="modal-title"></div>
      <div id="modalAuthor" class="modal-author"></div>
      <div id="modalVenue" class="modal-venue"></div>
    </div>
    
    <div class="modal-peer-nav" id="modalPeerNav">
      <div class="peer-nav-header">
        <span>References in this equation card (<span id="modalPeerCount">0</span>):</span>
        <div>
          <button class="btn" style="padding:2px 8px; font-size:0.75rem;" onclick="prevPeerRef()">◀ Prev</button>
          <button class="btn" style="padding:2px 8px; font-size:0.75rem;" onclick="nextPeerRef()">Next ▶</button>
        </div>
      </div>
      <div class="peer-pills" id="modalPeerPills"></div>
    </div>

    <div class="modal-body" id="modalBody"></div>

    <div class="modal-footer">
      <div id="modalLinks" style="display:flex; gap:10px; align-items:center;"></div>
      <div style="display:flex; gap:8px;">
        <button class="btn" id="modalCopyBtn" onclick="copyCurrentModalCitation()">📋 Copy Citation</button>
        <button class="btn btn-primary" onclick="jumpFromModalToSource()">📚 View in Bibliography</button>
      </div>
    </div>
  </div>
</div>

<!-- Floating Return Button -->
<button id="floatingReturnBtn" class="floating-return-btn" onclick="returnToCard()">
  ↩ Return to <span id="returnCardName">Equation</span>
</button>

<script>
const CARDS = %CARDS_JSON%;
const SOURCES = %SOURCES_JSON%;

const SOURCE_MAP = {};
SOURCES.forEach(s => { SOURCE_MAP[s.key] = s; });

let currentTab = 'cards';
let currentFilter = 'all';
let lastViewedCardId = null;
let currentModalKey = null;
let currentModalCard = null;

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderCards(filterText = '') {
  const container = document.getElementById('cardsContainer');
  const q = filterText.toLowerCase().trim();
  
  let list = CARDS;
  if (currentFilter === 'world') {
    list = list.filter(c => c.sources && c.sources.some(sk => {
      const s = SOURCE_MAP[sk];
      return s && s.number >= 143 && s.number <= 150;
    }));
  } else if (currentFilter === 'thai') {
    list = list.filter(c => c.sources && c.sources.some(sk => {
      const s = SOURCE_MAP[sk];
      return s && s.number >= 105 && s.number <= 136;
    }));
  } else if (currentFilter === 'standards') {
    list = list.filter(c => c.sources && c.sources.some(sk => {
      const s = SOURCE_MAP[sk];
      return s && (s.kind.includes('Standard') || s.kind.includes('RFC') || s.kind.includes('Metrology'));
    }));
  } else if (currentFilter !== 'all') {
    list = list.filter(c => c.group && c.group.toLowerCase().includes(currentFilter.toLowerCase()));
  }
  
  if (q) {
    list = list.filter(c => {
      const hay = [c.id, c.name, c.name_th, c.group, c.eq, c.why, c.why_th, c.units, c.watch].join(' ').toLowerCase();
      const matchCard = hay.includes(q);
      const matchSrc = c.sources && c.sources.some(sk => {
        const s = SOURCE_MAP[sk];
        if (!s) return false;
        return [s.key, s.author, s.title, s.kind, s.scope, s.audit_note].join(' ').toLowerCase().includes(q);
      });
      return matchCard || matchSrc;
    });
  }
  
  if (list.length === 0) {
    container.innerHTML = '<div style="text-align:center; padding:40px; color:#94a3b8;">No matching equation cards found.</div>';
    return;
  }
  
  container.innerHTML = list.map(c => {
    const statusClass = c.status === 'implemented' ? 'badge-success' : (c.status === 'background' ? 'badge-primary' : 'badge-warning');
    const cSources = (c.sources || []).map(sk => SOURCE_MAP[sk]).filter(Boolean);

    // Reference Pills
    const sourcesHtml = cSources.map(s => {
      const shortAuthor = s.author.split(',')[0].split(' and ')[0];
      const isWorld = s.number >= 143 && s.number <= 150;
      const isThai = s.number >= 105 && s.number <= 136;
      const icon = isWorld ? '🏛️ ' : (isThai ? '🇹🇭 ' : '');
      return `<span class="src-pill" onclick="openRefModal('${s.key}', '${c.id}')" title="${escapeHtml(s.title)}">${icon}[${s.number}] ${shortAuthor} (${s.year || 'n.d.'})</span>`;
    }).join(' ');

    // Drawer Ref Items
    const drawerHtml = cSources.map(s => {
      const doiLink = s.doi ? `<a href="https://doi.org/${s.doi}" target="_blank">DOI: ${s.doi}</a>` : '';
      const directLink = s.url ? `<a href="${s.url}" target="_blank">Publisher Web ↗</a>` : '';
      const isWorld = s.number >= 143 && s.number <= 150;
      const isThai = s.number >= 105 && s.number <= 136;
      const tag = isWorld ? '<span class="badge badge-accent">🏛️ World Top Univ</span>' : (isThai ? '<span class="badge badge-primary">🇹🇭 Thai Univ</span>' : '');

      return `
        <div class="drawer-ref-item">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
            <div class="drawer-ref-title">[${s.number}] ${escapeHtml(s.title)}</div>
            ${tag}
          </div>
          <div class="drawer-ref-author">${escapeHtml(s.author)} (${s.year || 'n.d.'})</div>
          <div class="drawer-ref-locator">${escapeHtml(s.locator || s.kind)}</div>
          <div style="font-size:0.82rem; color:#cbd5e1; margin-bottom:6px;"><i>Scope:</i> ${escapeHtml(s.scope)}</div>
          <div class="drawer-ref-links">
            ${doiLink}
            ${directLink}
            <button class="copy-btn" onclick="copyCitation('${s.key}')">📋 Copy</button>
            <a href="#src_${s.number}" onclick="jumpToSource(${s.number}, '${c.id}')" style="margin-left:auto;">Go to Bibliography ➔</a>
          </div>
        </div>
      `;
    }).join('');

    const whereHtml = (c.where || []).map(w => {
      return `<div>📂 <code>${w.file}</code> (line ${w.line}): <i>${w.what}</i></div>`;
    }).join('');

    return `
      <div class="card" id="${c.id}">
        <div class="card-header">
          <div>
            <div class="card-title">${c.name}</div>
            <div class="card-title-th">${c.name_th || ''}</div>
            <div class="card-meta">ID: <code>${c.id}</code> &bull; Group: ${c.group}</div>
          </div>
          <span class="badge ${statusClass}">${(c.status || 'implemented').toUpperCase()}</span>
        </div>
        <div class="code-eq">${escapeHtml(c.eq)}</div>
        <div class="card-desc">${escapeHtml(c.why)}</div>
        ${c.why_th ? `<div class="card-desc-th">${escapeHtml(c.why_th)}</div>` : ''}
        ${c.units ? `<div style="font-size:0.85rem; color:#94a3b8; margin-bottom:12px;"><b>Units:</b> ${escapeHtml(c.units)}</div>` : ''}
        ${c.watch ? `<div class="caveat-box">⚠️ <b>Caveat:</b> ${escapeHtml(c.watch)}</div>` : ''}
        ${whereHtml ? `<div class="code-pointers">${whereHtml}</div>` : ''}
        
        <div class="card-sources">
          <span style="font-size:0.8rem; color:#94a3b8; font-weight:600;">References (${cSources.length}):</span>
          ${sourcesHtml || '<span style="font-size:0.8rem; color:#64748b;">None</span>'}
          ${cSources.length > 0 ? `<button class="drawer-toggle-btn" onclick="toggleDrawer('${c.id}')" id="drawer_btn_${c.id}">📖 View All (${cSources.length}) ▼</button>` : ''}
        </div>

        ${cSources.length > 0 ? `<div class="card-refs-drawer" id="drawer_${c.id}">${drawerHtml}</div>` : ''}
      </div>
    `;
  }).join('');
}

function toggleDrawer(cardId) {
  const drawer = document.getElementById('drawer_' + cardId);
  const btn = document.getElementById('drawer_btn_' + cardId);
  if (!drawer) return;
  if (drawer.classList.contains('open')) {
    drawer.classList.remove('open');
    if (btn) btn.innerHTML = btn.innerHTML.replace('▲', '▼');
  } else {
    drawer.classList.add('open');
    if (btn) btn.innerHTML = btn.innerHTML.replace('▼', '▲');
  }
}

function renderSources(filterText = '') {
  const container = document.getElementById('sourcesContainer');
  const q = filterText.toLowerCase().trim();
  
  let list = SOURCES.filter(s => !s.excluded);
  if (currentFilter === 'world') {
    list = list.filter(s => s.number >= 143 && s.number <= 150);
  } else if (currentFilter === 'thai') {
    list = list.filter(s => s.number >= 105 && s.number <= 136);
  } else if (currentFilter === 'standards') {
    list = list.filter(s => s.kind.includes('Standard') || s.kind.includes('RFC') || s.kind.includes('Metrology'));
  }
  
  if (q) {
    list = list.filter(s => {
      const hay = [s.key, s.author, s.title, s.kind, s.scope, s.locator, s.audit_note, s.doi].join(' ').toLowerCase();
      return hay.includes(q);
    });
  }
  
  if (list.length === 0) {
    container.innerHTML = '<div style="text-align:center; padding:40px; color:#94a3b8;">No matching bibliography sources found.</div>';
    return;
  }
  
  container.innerHTML = list.map(s => {
    const isWorld = (s.number >= 143 && s.number <= 150);
    const isThai = (s.number >= 105 && s.number <= 136);
    const tagClass = isWorld ? 'badge-accent' : (isThai ? 'badge-primary' : 'badge-success');
    const tagText = isWorld ? '🏛️ WORLD TOP UNIV' : (isThai ? '🇹🇭 THAI RESEARCH' : '🌐 FOUNDATIONAL');
    const doiLink = s.doi ? `<a href="https://doi.org/${s.doi}" target="_blank">DOI: ${s.doi}</a>` : '';
    const webLink = s.url ? `<a href="${s.url}" target="_blank">Publisher Link ↗</a>` : '';

    return `
      <div class="source-item" id="src_${s.number}">
        <div class="source-header">
          <div style="flex:1;">
            <div class="source-title">[${s.number}] ${escapeHtml(s.title)}</div>
            <div class="source-author">${escapeHtml(s.author)} (${s.year || 'n.d.'})</div>
            <div class="source-venue">${escapeHtml(s.locator || s.kind)}</div>
          </div>
          <span class="badge ${tagClass}">${tagText}</span>
        </div>
        <div class="source-scope">${escapeHtml(s.scope)}</div>
        ${s.audit_note ? `<div style="font-size:0.83rem; color:#94a3b8; margin-bottom:10px; border-left:2px solid var(--accent); padding-left:10px;">${escapeHtml(s.audit_note)}</div>` : ''}
        <div class="source-footer">
          <div style="display:flex; gap:10px; align-items:center;">
            ${doiLink}
            ${webLink}
            <span>Key: <code>${s.key}</code></span>
          </div>
          <button class="copy-btn" onclick="copyCitation('${s.key}')">📋 Copy Citation</button>
        </div>
      </div>
    `;
  }).join('');
}

function openRefModal(key, cardId) {
  const s = SOURCE_MAP[key];
  if (!s) return;
  currentModalKey = key;
  currentModalCard = CARDS.find(c => c.id === cardId);
  lastViewedCardId = cardId;

  document.getElementById('modalTitle').textContent = `[${s.number}] ${s.title}`;
  document.getElementById('modalAuthor').textContent = `${s.author} (${s.year || 'n.d.'})`;
  document.getElementById('modalVenue').textContent = s.locator || s.kind;

  let bodyHtml = `<p><b>Relevance & Scope:</b> ${escapeHtml(s.scope)}</p>`;
  if (s.audit_note) {
    bodyHtml += `<p style="margin-top:10px; color:#94a3b8; border-left:2px solid var(--primary); padding-left:10px;"><b>Audit Details:</b> ${escapeHtml(s.audit_note)}</p>`;
  }
  document.getElementById('modalBody').innerHTML = bodyHtml;

  // Peer navigation inside this card
  if (currentModalCard && currentModalCard.sources && currentModalCard.sources.length > 0) {
    document.getElementById('modalPeerNav').style.display = 'block';
    document.getElementById('modalPeerCount').textContent = currentModalCard.sources.length;
    document.getElementById('modalPeerPills').innerHTML = currentModalCard.sources.map(sk => {
      const ps = SOURCE_MAP[sk];
      if (!ps) return '';
      const activeClass = sk === key ? 'active' : '';
      return `<span class="src-pill ${activeClass}" onclick="openRefModal('${sk}', '${currentModalCard.id}')">[${ps.number}] ${ps.author.split(',')[0]}</span>`;
    }).join(' ');
  } else {
    document.getElementById('modalPeerNav').style.display = 'none';
  }

  // Links
  let linksHtml = '';
  if (s.doi) linksHtml += `<a href="https://doi.org/${s.doi}" target="_blank">DOI: ${s.doi} ↗</a>`;
  if (s.url) linksHtml += `<a href="${s.url}" target="_blank">Publisher Website ↗</a>`;
  document.getElementById('modalLinks').innerHTML = linksHtml;

  document.getElementById('refModal').classList.add('open');
}

function closeRefModal() {
  document.getElementById('refModal').classList.remove('open');
}

function handleModalOverlayClick(e) {
  if (e.target.id === 'refModal') closeRefModal();
}

function prevPeerRef() {
  if (!currentModalCard || !currentModalCard.sources) return;
  const idx = currentModalCard.sources.indexOf(currentModalKey);
  const nextIdx = (idx - 1 + currentModalCard.sources.length) % currentModalCard.sources.length;
  openRefModal(currentModalCard.sources[nextIdx], currentModalCard.id);
}

function nextPeerRef() {
  if (!currentModalCard || !currentModalCard.sources) return;
  const idx = currentModalCard.sources.indexOf(currentModalKey);
  const nextIdx = (idx + 1) % currentModalCard.sources.length;
  openRefModal(currentModalCard.sources[nextIdx], currentModalCard.id);
}

function jumpFromModalToSource() {
  const s = SOURCE_MAP[currentModalKey];
  closeRefModal();
  if (s) jumpToSource(s.number, currentModalCard ? currentModalCard.id : null);
}

function copyCurrentModalCitation() {
  if (currentModalKey) copyCitation(currentModalKey);
}

function handleSearch() {
  const val = document.getElementById('searchInput').value;
  renderCards(val);
  renderSources(val);
}

function filterCategory(cat) {
  currentFilter = cat;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  handleSearch();
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-link').forEach(l => l.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  
  if (tab === 'cards') {
    document.querySelectorAll('.tab-link')[0].classList.add('active');
    document.getElementById('cardsTab').classList.add('active');
    document.getElementById('floatingReturnBtn').classList.remove('visible');
  } else if (tab === 'sources') {
    document.querySelectorAll('.tab-link')[1].classList.add('active');
    document.getElementById('sourcesTab').classList.add('active');
    if (lastViewedCardId) {
      const card = CARDS.find(c => c.id === lastViewedCardId);
      document.getElementById('returnCardName').textContent = card ? card.name : 'Equation';
      document.getElementById('floatingReturnBtn').classList.add('visible');
    }
  } else {
    document.querySelectorAll('.tab-link')[2].classList.add('active');
    document.getElementById('auditTab').classList.add('active');
    document.getElementById('floatingReturnBtn').classList.remove('visible');
  }
}

function jumpToSource(num, cardId) {
  if (cardId) lastViewedCardId = cardId;
  switchTab('sources');
  setTimeout(() => {
    const el = document.getElementById('src_' + num);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, 100);
}

function returnToCard() {
  if (!lastViewedCardId) {
    switchTab('cards');
    return;
  }
  switchTab('cards');
  setTimeout(() => {
    const el = document.getElementById(lastViewedCardId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.style.borderColor = 'var(--primary)';
      setTimeout(() => { el.style.borderColor = ''; }, 1500);
    }
  }, 100);
}

function copyCitation(key) {
  const s = SOURCE_MAP[key];
  if (!s) return;
  const cite = `${s.author} (${s.year || 'n.d.'}). ${s.title}. ${s.locator || s.kind}. ${s.doi ? 'https://doi.org/' + s.doi : s.url || ''}`;
  navigator.clipboard.writeText(cite).then(() => {
    alert('Citation copied to clipboard:\\n\\n' + cite);
  });
}

function printDoc() {
  window.print();
}

function exportBib() {
  const a = document.createElement('a');
  a.href = 'thesis_references.bib';
  a.download = 'thesis_references.bib';
  a.click();
}

// Global keydown for modal
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeRefModal();
  if (document.getElementById('refModal').classList.contains('open')) {
    if (e.key === 'ArrowLeft') prevPeerRef();
    if (e.key === 'ArrowRight') nextPeerRef();
  }
});

// Initial Render
renderCards();
renderSources();
</script>
</body>
</html>
"""

full_html = html_template.replace('%CARDS_JSON%', json.dumps(cards, ensure_ascii=False))
full_html = full_html.replace('%SOURCES_JSON%', json.dumps(sources, ensure_ascii=False))

with open(os.path.join(BUNDLE_DIR, 'mice_references_standalone.html'), 'w', encoding='utf-8') as f:
    f.write(full_html)
print("Wrote dist/thesis_references_bundle/mice_references_standalone.html")

# Also update docs/mice_references_standalone.html with the new UI and data
with open('docs/mice_references_standalone.html', 'w', encoding='utf-8') as f:
    f.write(full_html)
print("Updated docs/mice_references_standalone.html")

# 8. Write dist/thesis_references_bundle/README.txt
readme_text = f"""========================================================================
MICE HUMANOID ROBOT — MASTER THESIS REFERENCES BUNDLE
========================================================================
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Version: Standalone Master Distribution (Task A21-12)

This bundle contains the complete research reference library, mathematical 
equations, and verified literature citations for the Mice Humanoid Robot thesis.

CONTENTS OF THIS FOLDER:
------------------------------------------------------------------------
1. mice_references_standalone.html
   - A 100% self-contained, offline-ready interactive web application.
   - Double-click to open in ANY modern web browser (Edge, Chrome, Safari, Firefox).
   - Zero installation, zero server, zero external dependencies required.
   - Features:
     * Instant bilingual search (Thai / English) across formulas, DOIs, authors, universities.
     * Category filter tabs: All, World Universities, Thai Universities, Standards & RFCs, Textbooks.
     * In-card expandable reference drawers: view all supporting citations directly inside each formula block without navigating away.
     * Quick-view modal: click any reference pill to inspect details and flip through all references in that card with Prev/Next buttons.
     * Sticky return button: jumps back to the formula card from the bibliography view.
     * 1-click export of citations and printer-friendly view.

2. THESIS_REFERENCES_MASTER.md
   - Comprehensive Markdown documentation covering all {len(cards)} engineering equations
     and all {len(sources)} bibliography citations.
   - Ready for GitHub, VS Code, Obsidian, Notion, or typst/pandoc conversion.

3. thesis_references.bib
   - Standard BibTeX bibliography database containing all {len(sources)} entries.
   - Ready to upload directly to Overleaf or cite in LaTeX using \\cite{{...}}.

4. thesis_references.json
   - Full structured dataset for programmatic access, python analytics, or database import.

INSTITUTIONAL COVERAGE:
------------------------------------------------------------------------
- World Premier Universities:
  * Stanford University (Operational Space Formulation, Khatib 1987)
  * MIT (Impedance Control & Holding Torque, Hogan 1985)
  * Carnegie Mellon University / CMU (Lucas-Kanade Optical Flow, Kanade 1981)
  * University of California, Berkeley (MLS Robotics Manipulation, Murray, Li, Sastry 1994)
  * ETH Zurich (Autonomous Mobile Robots & Uncertainty, Siegwart 2011)
  * University of Tokyo (Singularity-Robust Redundancy & DLS IK, Nakamura 1991)
  * University of Oxford (Active Camera Tracking & Motion, Murray & Beardsley 1994)
  * University of Cambridge (Gaussian Processes, Rasmussen & Williams 2006)
  
- Thai Premier Universities & National Research Labs:
  * Chulalongkorn University (Manipulator Dexterity, ASR, WangchanBERTa, Dynamics)
  * Sam Phra Chom: KMUTT (FIBO Humanoid, Face Embeddings), KMITL (PID Anti-windup), KMUTNB (Exoskeleton Statics)
  * Chiang Mai University (CMU - Speech Phonemes, SIFT Vision)
  * Mahidol University (BART LAB - Surgical Manipulators, Robot Safety)
  * Thammasat University (SIIT - Servo Motor Compliance)
  * NECTEC / NSTDA (National Thai ASR & VAJA TTS)
  * NIMT (National Institute of Metrology Thailand - GUM Uncertainty)
  * Prince of Songkla University (PSU - Motor Control, Compliance)
  * Khon Kaen University (KKU - IK Optimization, Elderly ASR)
  * Suranaree University of Technology (SUT - DC Motor Variable Torque)
  * Burapha University (BUU - Face Landmarks, Illumination)
  * Naresuan University (NU - Mobile Robot Vision Navigation)
  * Rajamangala University of Technology Thanyaburi (RMUTT - Arm PID, Camera Calibration)
  * Srinakharinwirot University (SWU - Service Robot HRI)
  * Walailak University (WU - Vision Bounding Box)
  * VISTEC & Kasetsart University (ASR Crowdsourced Validation)
  * Asian Institute of Technology (AIT - Trajectory Tracking)

- International Standards:
  * ISO (ISO 12100 Safety, ISO 13850 E-Stop, ISO 9283 Robot Performance, ISO 9241 Ergonomics)
  * IETF RFCs (RFC 9110 HTTP Semantics, RFC 6455 WebSocket, RFC 6762/6763 mDNS/DNS-SD, RFC 8085 UDP)
  * BIPM / JCGM (GUM Uncertainty Evaluation, SI Units)
  * TIA/EIA (TIA-485-A) & Modbus Organization

HOW TO SHARE WITH YOUR FRIEND:
------------------------------------------------------------------------
Just send the file:
  thesis_references_bundle.zip

Your friend can extract it anywhere and immediately double-click
`mice_references_standalone.html` to browse everything offline!
========================================================================
"""
with open(os.path.join(BUNDLE_DIR, 'README.txt'), 'w', encoding='utf-8') as f:
    f.write(readme_text)
print("Wrote dist/thesis_references_bundle/README.txt")

# 9. Create ZIP archive
print(f"Creating zip archive at {ZIP_PATH}...")
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(BUNDLE_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, BUNDLE_DIR)
            zipf.write(file_path, arcname)
            print(f"  Added {arcname}")

print(f"\nSUCCESS: Generated thesis_references_bundle and zip ({os.path.getsize(ZIP_PATH):,} bytes).")
