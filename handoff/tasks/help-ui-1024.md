# Help matches the actual prize and recognition screens

Owner: codex:10242258-597a
Updated: 2026-10-24
Branch: codex/help-ui-1024
Tree: E:/final_proj/mice/code/.staging-help-ui-1024
Last commit: 2bd3299 baseline
Plan: A48-15

## Goal
Human: Help is broken and confusing; prize app and FaceReg differ from Help.
Human correction: ONE fixed Hall at Receive; FOUR magnets on wheel; Drop has no Hall; Receive and Drop are on the same side.

## Doing now
Repair only Help faces/gacha sources, search and responsive style in isolated tree; build generated Help. Preserve app/firmware owners and live services. No physical settings or commands.

## Facts found
- apps/gacha/index.html:303,346 contain unescaped GCALIB quotes, preventing all script execution; live app has blank tabs and checking status. A47-20 already owns this source.
- Help faces screenshots show Open it while captions claim greeting/rules fields. Actual greeting tab is What the rig says; it has no move-file selector.
- Help gacha diagram puts Hall #1/#3 on wheel and Receive opposite Drop, contradicting human hardware correction. Drop mode and guaranteed centering claims are unsupported.
- Help search filters only .f and table rows, ignoring new .info-box content.
- Help .where display:block overrides shared hidden technical labels.

## Done
- Read-only live browser reproduction for prize page and Help faces.

## Next
1. Build and preview corrected Help; test search and navigation on wide/narrow screens.
2. Independent review and coordinated QC; do not take A47-20 driver lease.

## Blocked
- QC-only resource held by codex:10231901-f6cc for isolated gacha/Studio/TV gate.
