# UX review by GPT (Codex), 2026-11-22

Asked by the user: "check the UX/UI, let GPT help". Reviewed as a non-technical person.

**Method.** 14 screens (hub tabs Home, Tools, Modules, Firmware, Network, Settings, Complaints; Help; Studio; Voice; Camera; TV; Prize machines; Photobooth) shot in Edge at 1280 px and 390 px, light and dark theme, English, against the QC hub with fake modules. Each screen is one 2x2 sheet. Codex (default model of the PC, gpt-6.1-sol) read the sheets and wrote the findings below. Second pass: the prompt (`docs/ux_review_prompt.txt`) asks for the whole layout and UX/UI (placement, order, flow, hierarchy, spacing, contrast in both themes, phone), not only wording. Findings are leads, not facts: check each against the code before changing it (project rule).

**Limits.** Pictures only: Chrome 75, real speed and signed-in flows were not assessed. The 390 px view is cut at 1500 px high. Studio, Voice and TV ran without a robot. The board page and Reconize (faces) were not shot.

**Gemini.** Not run. `agy` (signed in, Gemini 3.8 Flash High listed) could not open the sheets in headless mode: reading a file needs a "command" permission that print mode cannot ask for. The only ways are `--dangerously-skip-permissions` or an allow rule in agy settings; I did not grant either on my own. When the user allows one, run: `agy -p "<same prompt>" --mode plan --model gemini-3.8-flash-high --add-dir <sheets>` with the prompt in `docs/ux_review_prompt.txt`.

## Findings (GPT)

**hub-home** — “Open a show tool or find my robot.”

- **High:** The large sign-in form pushes useful content down on phones. Replace it with an expandable “Sign in to control” bar.
- **High:** Later phone tabs disappear offscreen without an obvious cue. Show priority tabs plus a labelled “More” menu.
- **Medium:** Language and technical details consume another header row. Keep language easy to find; move technical details into Settings.
- **Medium:** Six tall tool cards create substantial phone scrolling. Use compact rows with an icon, short description and 44px Open button.
- **Medium:** “Looking for modules…” offers no next step. Show searching, found or none found, with Retry and connection help.

**hub-tools** — “Find and open one of the apps.”

- **Medium:** This largely repeats Home. Give Home connected robots and recent tools; keep the complete app list here.
- **Medium:** The selected Tools label is faint in light mode and dark against grey in dark mode. Use a clearly contrasting selected state.
- **Medium:** Photobooth’s description is Thai while English is selected. Translate descriptions consistently.
- **Medium:** “Apps on this PC” shows only “Loading…”. Add a loading indicator, a failure message with Retry, and a completed empty state.

**hub-modules** — “Find a connected robot and open its controls.”

- **High:** Phone cards spend a whole row on the favourite star. Put star, name and connection status together above the actions.
- **High:** “Open module” and “Studio + monitor” compete without explaining the difference. Use “Control robot” as primary and “Open Studio and live view” as secondary.
- **Medium:** “RS485”, “COM99” and “reached” remain visible with technical details unchecked. Show “Connected through this computer”; reveal connection codes on request.
- **Medium:** Long discovery explanations crowd the page. Put them under “Connection help” and show a concise count beside Rescan.

**hub-firmware** — “A locked page; its purpose isn’t explained.”

- **High:** The sign-in form and another Sign in card repeat the same request. Combine them into one clear entry point.
- **Medium:** There is no plain-language page heading. Use “Update robot software” with a sentence explaining its purpose.
- **Medium:** The selected Firmware tab has weak contrast in both themes. Use readable text on a stronger selected background.

The actual update controls are not visible.

**hub-network** — “Connect a phone or another computer to this hub.”

- **High:** The QR card dominates the phone view and leaves desktop space unused. Collapse it under “Open on another device” on phones; place desktop cards alongside one another.
- **High:** The red sign-in warning does not identify the blocked action. Name that action and show the warning beside it.
- **Medium:** Long addresses wrap awkwardly in small text. Show a friendly computer name and Copy link button; put full addresses under Details.
- **Medium:** Manual address entry competes with discovery. Make “Find another computer” primary and put labelled manual entry under “Add by address”.

**hub-settings** — “Change the appearance and connection information shown.”

- **High:** Sign-in demands appear before the visible appearance controls, making them look locked. Put personal display choices first and identify restricted settings separately.
- **Medium:** “Reconize” and “Midnight” do not clearly describe appearance. Use “Light” and “Dark”, with small previews.
- **Medium:** The explanation includes a stylesheet file path. Remove development instructions from this user-facing page.
- **Medium:** The technical-details explanation is far from its checkbox. Place “Show connection details” beside the explanation here.

**hub-complaints** — “Read problems people have reported.”

- **High:** Dates dominate while phone summaries are clipped. Lead with the problem summary; put the smaller date underneath.
- **High:** The extremely long list has no visible filtering or grouping. Add Open/Closed filters, a count and grouped repeated reports.
- **Medium:** “Complaints” and raw command text are unhelpful labels. Rename this “Reports” and keep technical content inside report details.
- **Medium:** Small Open buttons create repetitive targets. Make each entire row tappable, at least 44px high, with a visible status label.

**help** — “Learn how to set up and run the show.”

- **High:** On phones, the reference navigation comes before the search and introduction. Put search first and collapse navigation under “Browse help”.
- **High:** Task choices sit below lengthy guidance and eight pictures. Move “What do you want to do?” directly below search.
- **Medium:** Brown text in light mode and muted text in dark mode look faint, especially small captions. Increase contrast and use at least 16px reading text.
- **Medium:** Phone navigation links are small and closely packed. Use expandable groups with generously spaced, 44px-high links.

**studio** — “Make robot poses and arrange them into a show.”

- **High:** Phone slider names are clipped, making similar shoulder controls indistinguishable. Show full labels and group them under Left arm, Right arm and Body.
- **High:** The large preview and long pose form put the timeline beyond the supplied phone crop. Offer a compact preview and nearby “Add pose” and “Preview movement” actions.
- **High:** Desktop “Stop robot” is tiny; it is not visible in the phone crop. Keep a prominent red Stop beside robot playback controls.
- **Medium:** Save, preview, checking and robot commands crowd one desktop toolbar. Separate “Edit”, “Try on screen” and “Send to robot”.
- **Medium:** Timeline and toolbar buttons look shorter than 44px. Enlarge the main actions and move occasional commands into More.

**voice** — “Ask the rig a question.”

- **High:** Talk is selected, but its content area is blank in both sizes. Show a question field and Talk button, or an explicit loading/error state.
- **Medium:** “Ready—ask a question” contradicts the missing question controls. Tie readiness to a visible, usable next action.
- **Medium:** Eight equally prominent sections mix talking with configuration. Keep Talk first and group setup sections under Settings.
- **Medium:** Username and password rely on disappearing placeholder text. Add permanent labels and enlarge the fields and sign-in button.

**camera** — “Find cameras and watch their pictures.”

- **High:** The empty state ends with the unexplained device type “cam”. Show “No cameras found” with simple power and connection checks; move device-type details under technical information.
- **Medium:** “Look again” is separated from the empty message. Put Retry inside the empty-state card, with checking progress and the last result.
- **Medium:** The large sign-in panel precedes the useful camera status. Put status first and use a compact sign-in prompt for actions requiring permission.

**tv** — “Choose a robot, play a show and make it speak.”

- **High:** “Ready” appears before any robot is selected, while several controls look unavailable. Move robot selection first and say “Choose a robot to start”.
- **Medium:** Phone mode tabs cut off later choices. Wrap all three into readable, 44px-high buttons with clear selected states.
- **Medium:** The phone card says 14 files but shows ten tiles. Add “View all 14” or an obvious scrolling cue.
- **Medium:** “Silenced All” could describe a state or an action. Use “Speech muted” for status and “Mute all speech” for the action.

**gacha** — “Give prizes and set the event’s prize rules.”

- **High:** Green “0 of 0 machines answering” looks reassuring while prize controls look usable. Lead with “No prize machines found”, connection help and clearly unavailable actions.
- **High:** “Give one anyway (admin)” sits beside ordinary Give. Move overrides into a separate organiser menu and explain their consequences before use.
- **Medium:** Presets promise to fill a table that is not visible here. Put them beside the rules table and preview their changes.
- **Medium:** Event status says “open” beside “Start the event”. Show the current state clearly and present the relevant next action.
- **Medium:** “New event (counts to zero)” resembles routine buttons. Separate this reset action and explain which counts will be cleared.

**photobooth** — “Open the guest photo screen or set up the booth.”

- **Medium:** Small, muted “checking…” provides no completed result in the picture. Show a clear Checking, Ready or Not running status with Retry.
- **Medium:** The explanation mentions first-start behaviour, but the main action always reads Open. Match it to the state: “Start booth” or “Open guest screen”.
- **Low:** “Open admin” does not explain its destination. Rename it “Booth setup” and state that it opens a separate page.

TV remote navigation, loading completion, speed and Chrome 75 compatibility are not visible in these still images.

**TOP 10 changes, ranked by benefit for effort**

1. Fix selected-tab contrast in both themes.
2. Replace technical labels with everyday names; complete the selected language’s translations.
3. Make important buttons and navigation targets at least 44px.
4. Give every empty, loading and error state a clear next action.
5. Replace repeated sign-in forms with one compact, consistent entry point.
6. Make every hub section discoverable on phones.
7. Put Help search and task choices before reference material.
8. Give Voice a visible question-and-answer starting point.
9. Lead Prize machines with connection status; separate organiser overrides and resets.
10. Simplify Studio’s phone flow and keep Stop easy to reach.

**Three things to keep**

- Friendly illustrations that help people recognise tools and tasks.
- Consistent cards and “← Hub” links that provide familiar structure.
- Both light and dark themes, with red reserved prominently for Stop and urgent warnings.
