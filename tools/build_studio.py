import glob
import re

base_dir = '.staging/nong/main_python_set_nong/web'

sections = ['00_header', 'notices', 'rig_data', 'state', 'scene', 'build_rig', 'gizmo_rings', 'picking_drag', 'ik_4_dof_arm', 'collisions', 'sliders', 'timing', 'timeline', 'yaml_export', 'rig_setup_ui', 'edit_existing_sequences', 'music_on_a_keyframe', 'project_save_load', 'stl_meshes', 'robot_link', 'main_loop', 'boot']

out = []
for s in sections:
    out.append(open(f'{base_dir}/app_parts/{s}.js', encoding='utf-8').read())

with open(f'{base_dir}/app.js', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

with open(f'{base_dir}/index.html', encoding='utf-8') as f:
    idx = f.read()

idx = re.sub(r'<script src="app_parts/.*?"></script>\n?', '', idx)

# Check if app.js is already there
if '<script src="app.js"></script>' not in idx:
    idx = idx.replace('</body>', '<script src="app.js"></script>\n</body>')

with open(f'{base_dir}/index.html', 'w', encoding='utf-8') as f:
    f.write(idx)

