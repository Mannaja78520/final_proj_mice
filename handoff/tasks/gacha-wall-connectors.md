# Gachapon bottom wall covers: power + data connector panels

Owner: codex:gacha-wall-connectors (v2 data fix completed)
Updated: 2026-10-29 15:05 (+07)
Branch: none (CAD files only; model/ is outside the code repo)
Last commit: none; task-local CAD work
Plan: completed

## Fix v2 data (DONE; user2026-10-29)
Bottom-up DATA: **RS485 IN h20, RS485 OUT h38, USB-C h60 mm** above the original bottom edge.
Published existing `gacha_buttom_wall_cover_data_v2.SLDPRT` and STL in place; no v3.
Refreshed/saved `gachapong_assembly_v2.SLDASM`, kept reference geometry hidden, regenerated both v2 preview PNGs.
RS485 pitch18 mm leaves2 mm inside-pocket web. POWER v2 unchanged. STEP skipped.

## Goal v2 (DONE)
One raised back lobe per cover. POWER lobe A/theta21; DATA lobe B/theta69; both clusters next to shared back seam.
Both fixed on empty -Z half opposite original visible +Z pair; four visible bottom covers close ring.
New v2 files preserve original and v1 native/STL/STEP artifacts. No encoder port added.

## Goal v1 (DONE; retained)
POWER:2 XT60E-M, DC female5.5x2.1, KCD1 round20. DATA:2 parallel RS485 JST XH3-pin plus UGREEN USB-C.
Reused sourced dimensions, scripts and lessons; vendor URLs and GUESS register in `wall_cover_connectors.md`.

## Hard rules
- Never save original `gacha_buttom_wall_cover.SLDPRT` or `gachapong_assembly.SLDASM`; preserve v1 and power v2.
- All connector cuts/holders on selected raised lobe; preserve recessed band and original upper bolt access.
- Own SolidWorks DispatchEx only; never touch user's PID13988 (started from Explorer). Close only owned instances.
- Stop and report exact path if any target remains locked. No remaining lock at publication.
- No friend folders (Face_Regonize,friend_api_handoff,All-Jao-Games,Photobooth*), training changes, GPU or STEP export.
- Keep sourced numbers separate from GUESS fit/layout choices; physical connector fit/print strength not tested.

## Doing now
DONE: canonical data native/STL replaced, assembly refreshed and reopened, references hidden,
geometry checks passed, both canonical previews regenerated/reviewed, final hashes/AST/cleanup checked.
All16 task-owned SolidWorks PIDs exited across v2/fix sessions; user PID13988 never accessed.
Task moved from code/ to mice_system/ during work; this is the current handoff.

## File status
Paths relative to model/gachapong/8_10_2026/ except task. Original/v1/power preservation confirmed by SHA256.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `gacha_buttom_wall_cover_power_v2.SLDPRT` | power unchanged | done | baseline SHA256 unchanged;native verified | outside repo |
| `gacha_buttom_wall_cover_data_v2.SLDPRT` | IN20/OUT38/USB60;one back lobe | done | reopened;14 zero-error features;1 solid | outside repo |
| `stl/gacha_buttom_wall_cover_power_v2.STL` | power unchanged | done | baseline SHA256 unchanged;closed mesh | outside repo |
| `stl/gacha_buttom_wall_cover_data_v2.STL` | corrected data mesh published in place | done | closed;1 component;9056 triangles;3 aperture checks | outside repo |
| `gachapong_assembly_v2.SLDASM` | refreshed existing v2 assembly | done | saved/reopened;normal/top-level rebuild pass;no overlaps | outside repo |
| `wall_cover_connectors.md` | published heights/spacing and rebuild limit | done | reviewed;current20/38/60 layout | outside repo |
| `wall_cover_v2_preview.png` | current canonical part preview | done | regenerated;visually reviewed | outside repo |
| `wall_cover_v2_assembly_preview.png` | current canonical assembly preview | done | regenerated;visually reviewed | outside repo |
| `tools/wall_cover_v2_common.py` | repeatable v2 task tool | done | AST passed;executed | outside repo |
| `tools/inspect_wall_v2.py` | repeatable v2 task tool | done | AST passed;executed | outside repo |
| `tools/inspect_wall_v2_visibility.py` | repeatable v2 task tool | done | AST passed;executed | outside repo |
| `tools/make_wall_covers_v2.py` | repeatable v2 task tool | done | AST passed;executed | outside repo |
| `tools/make_wall_assembly_v2.py` | repeatable v2 task tool | done | AST passed;executed | outside repo |
| `tools/verify_wall_covers_v2.py` | repeatable v2 task tool | done | AST passed;executed | outside repo |
| `tools/preview_wall_covers_v2.py` | repeatable v2 task tool | done | AST passed;executed | outside repo |
| `tools/wall_cover_v2_assembly.json` | canonical assembly refresh evidence | done | saved hash matches;normal/top-level rebuild pass | outside repo |
| `tools/wall_cover_v2_build_data.json` | canonical data publication evidence | done | native/STL hashes match | outside repo |
| `tools/wall_cover_v2_build_power.json` | part build/export evidence | done | verified;SHA256 manifest current | outside repo |
| `tools/wall_cover_v2_inspect.json` | read-only orientation/visibility evidence | done | verified;SHA256 manifest current | outside repo |
| `tools/wall_cover_v2_session.json` | owned session lifecycle | done | ExitApp recorded;own PID exited | outside repo |
| `tools/wall_cover_v2_verify.json` | native/mesh/assembly evidence | done | status passed | outside repo |
| `tools/wall_cover_v2_visibility.json` | read-only orientation/visibility evidence | done | verified;SHA256 manifest current | outside repo |
| `tools/wall_cover_v2_assembly_meshes.npz` | native/exported CPU mesh evidence | done | verified;SHA256 manifest current | outside repo |
| `tools/wall_cover_v2_orientation_meshes.npz` | native/exported CPU mesh evidence | done | verified;SHA256 manifest current | outside repo |
| `tools/wall_cover_v2_part_meshes.npz` | native/exported CPU mesh evidence | done | verified;SHA256 manifest current | outside repo |
| `tools/finish_wall_data_fix_v2.py` | repeatable v2 task tool | done | AST passed;executed | outside repo |
| `tools/wall_cover_v2_build_data_staged.json` | data fix staging/checkpoint evidence | done | verified;SHA256 manifest current | outside repo |
| `tools/wall_cover_v2_data_fix.json` | completed data fix evidence | done | status complete;protected hashes match | outside repo |
| `tools/wall_cover_v2_data_staged_verify.json` | native/mesh/assembly evidence | done | status passed | outside repo |
| `tools/wall_cover_v2_refresh_baseline.json` | rebuild scope/baseline evidence | done | original recursive issue isolated;top-level passes | outside repo |
| `tools/wall_cover_v2_refresh_inspect.json` | rebuild scope/baseline evidence | done | original recursive issue isolated;top-level passes | outside repo |
| `tools/data_fix_staging/gacha_buttom_wall_cover_data_v2.SLDPRT` | retained verified staging artifact | done | published/previewed;current canonical files verified | outside repo |
| `tools/data_fix_staging/gacha_buttom_wall_cover_data_v2.STL` | retained verified staging artifact | done | published/previewed;current canonical files verified | outside repo |
| `tools/data_fix_staging/wall_cover_v2_assembly_preview.png` | retained verified staging artifact | done | published/previewed;current canonical files verified | outside repo |
| `tools/data_fix_staging/wall_cover_v2_preview.png` | retained verified staging artifact | done | published/previewed;current canonical files verified | outside repo |
| `tools/wall_cover_v2_files.json` | current final artifact manifest | done | status passed;16 owned PIDs exited;8 AST checks | outside repo |
| `mice_system/handoff/tasks/gacha-wall-connectors.md` | completed task checkpoint | done | this checkpoint | uncommitted |

## Facts found
- Native wall: R175 outside/R158.5 inside, raised16.5, recessed3, Y8.5..88.5; STL Z=nativeZ+175.
  Native axisY; conservative no-cut theta28..62 retained. Dimensions/sources in wall_cover_connectors.md.
- Original assembly had TWO visible +Z covers and hidden -3 on -Z; only that hidden placeholder suppressed in v2.
  Back=-Z follows user's empty-half convention; original upper dispensing opening is also on -Z.
- Original center(m)=(1.167093887713,.062327639590,1.267244680905);POWER identity,DATA -90degY.
  All original transforms retained;new covers fixed; selected edge-A/edge-B lobes meet at -Z seam.
- POWER unchanged h9/25/42/65; DATA now IN20/OUT38/USB60. RS48518-pitch gives4 mm outside-seat gap,
  2 mm inside-pocket web; OUT-to-USB outside-seat gap6.5 mm. All connector envelopes/skin sizes unchanged.
- Existing compact POWER uses31x14 XT inside pockets (v1 was31x18);minimum internal web0.7 mm remains.
- tools/wall_cover_v2_verify.json:11 aperture checks,324 band/234 unused-lobe rays pass;
  one solid per native,zero new feature errors,closed single STLs;15 boolean candidates,no overlap/errors.
- Normal/top-level v2 assembly rebuilds pass with zero assembly feature errors. Full recursive rebuild fails
  existing Namiki with Encoder-1 reference in untouched original too; no source subassembly modified.
  Evidence: tools/wall_cover_v2_refresh_baseline.json and wall_cover_v2_refresh_inspect.json.
- tools/wall_cover_v2_data_fix.json status complete; tools/wall_cover_v2_files.json records final hashes,
  preserved original/v1/power hashes,8 AST checks,16 owned PIDs exited; user13988 untouched.
- Original part SHA256:10cd79e74975c601bddaa2f6a16062f8f76053d5fae4ddf80f5c79a16ef7a68f.
  Original assembly SHA256:5d5a5d8e71fb50d7c1805da50a0a8ea0d7696b69694040cee50d1dac003e5bcd.

## Done
- Original v2 steps1-5: read task/reuse v1,orient lobes,build covers,save new assembly,verify and document.
- Data fix steps1-2: build/verify corrected same-name staging and closer RS485 pair;old canonical data was locked.
- Resume step3: after user released lock,all5 canonical write/replace checks passed;published native/STL in place.
  Refreshed/saved existing v2 assembly with hidden references using owned DispatchEx only.
- Resume step4: current canonical parts/assembly reopened and verified;both previews regenerated and reviewed.
- Resume step5: dimensions/statuses/final manifest updated;original/v1/power hashes unchanged;all own instances closed.

## Next
- Claude may re-export current v2 STEP outside sandbox; intentionally skipped here.
- Physical prototype: confirm purchased DC/UGREEN bodies,insertion/retention,fastener access,cable routing and print strength.

## Blocked / limits
- No active task blocker. All requested connectors fit on their selected single back lobes.
- Full recursive rebuild has the pre-existing Namiki reference issue documented above;normal/top-level refresh passes.
- Purchased DC/UGREEN envelopes remain GUESS;physical fit/printing/cables not tested. Details in dimension sheet.
