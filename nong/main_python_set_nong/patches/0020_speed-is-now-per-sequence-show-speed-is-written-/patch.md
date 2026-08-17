# Patch 0020

- **when:** 2026-08-03 13:37
- **change:** Speed is now per SEQUENCE: Show speed is written into the sequence file as its first '- speed:' step and restored when re-editing, so each sequence keeps its own pace and a chain sets the speed again at every hand-over instead of sequence B inheriting whatever A left the module on. parseSeqYaml understands the speed step instead of counting it as unsupported.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 20`
