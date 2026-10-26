"""Group choreography, camera/body separation and physical collision envelopes."""
import json
import subprocess
from pathlib import Path
import qc as F

AREA='studio'
TITLE='group video preserves waist/shoulders and never averages incompatible routines'
SLOW=False


def run(t):
    root=Path(__file__).resolve().parents[2]
    result=subprocess.run(['node',str(root/'qc/data/video_group.cjs')],cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=90)
    for line in result.stdout.splitlines():
        if line.startswith('PASS '):t.ok(True,line[5:],'actual Studio JS with real THREE kinematics')
        elif line.startswith('FAIL '):t.ok(False,line[5:],'actual Studio JS')
    t.eq(result.returncode,0,'video/body/collision regression fixture completes')
    t.ok('RESULT ' in result.stdout,'fixture reports completion',result.stderr[-300:])
