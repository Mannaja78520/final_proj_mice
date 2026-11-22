# UX review by GPT (Codex), 2026-11-22

Asked by the user: "check the UX/UI, let GPT help". Reviewed as a non-technical person.

**Method.** 14 screens (hub tabs Home, Tools, Modules, Firmware, Network, Settings, Complaints; Help; Studio; Voice; Camera; TV; Prize machines; Photobooth) shot in Edge at 1280 px and 390 px, light and dark theme, English, against the QC hub with fake modules. Each screen is one 2x2 sheet. Codex (default model of the PC, gpt-6.1-sol) read the sheets and wrote the findings below. Second pass: the prompt (`docs/ux_review_prompt.txt`) asks for the whole layout and UX/UI (placement, order, flow, hierarchy, spacing, contrast in both themes, phone), not only wording. Findings are leads, not facts: check each against the code before changing it (project rule).

**Limits.** Pictures only: Chrome 75, real speed and signed-in flows were not assessed. The 390 px view is cut at 1500 px high. Studio, Voice and TV ran without a robot. The board page and Reconize (faces) were not shot.

**Gemini.** Gemini 3.8 Flash (High) via `agy` reviewed the same sheets with the same prompt (user allowed `--dangerously-skip-permissions` for the review picture folder only, 2026-11-22). Its findings are in the last section. Compare with GPT: where both agree, act first.

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

## Findings (Gemini)

### hub-home

**(a) First impression:** A master dashboard to launch show apps and see whether your robots are awake and connected.

**(b) Concrete problems & fixes:**
1. **[High] Login box hogs prime space above the fold:** On phones, the "Log in to control" card pushes tools and robot lists completely off-screen.  
   *Fix:* Move login to a compact "Sign In" key button in the top navbar; show tools and connected robots immediately at the top.
2. **[High] Red "STOP" button looks like an active emergency:** A prominent red banner right below the header makes teachers worry that the system crashed before the show even begins.  
   *Fix:* Style as a neutral outline button while idle; light it up bright red only when a robot is actively moving.
3. **[Medium] Navigation tabs cut off on phone:** "Network", "Settings", and "Complaints" tabs disappear off the right edge with no indicator that you can scroll.  
   *Fix:* Convert to a swipeable tab bar with faded edge cues or a bottom navigation bar.
4. **[Medium] Mixed languages on tool cards:** Photobooth card displays Thai subtitle text (`ถ่ายภาพพร้อมกรอบ...`) even when the interface language is set to English.  
   *Fix:* Sync all card descriptions with the selected language picker.
5. **[Low] "Your modules" status is passive text:** Plain sentence ("Looking for modules...") gives no visual clue whether scanning is active.  
   *Fix:* Add an animated radar pulse or clear counter badge (`0 robots connected · Scanning...`).

---

### hub-tools

**(a) First impression:** An app library to pick robot tools and show accessories.

**(b) Concrete problems & fixes:**
1. **[High] Identical duplicate of Home screen:** Displays the exact same 6 tool cards as the Home tab, confusing users about why both tabs exist.  
   *Fix:* Merge Home and Tools into one unified start page, or reserve Tools exclusively for system utilities and app installs.
2. **[High] "Apps on this PC" trapped in indefinite loading:** Plain text at the bottom reads "Loading..." with no spinner or result.  
   *Fix:* Show an explicit progress spinner and render installed app chips with "Launch" buttons.
3. **[Medium] Unnecessary login barrier to browse:** A prominent password box greets the user even though tools can be viewed without logging in.  
   *Fix:* Remove the login box from this page; prompt for credentials only when clicking an action that requires admin rights.
4. **[Medium] Small tap targets on mobile cards:** The text link "Open ↗" is small (~32 px height) and easy to miss on phones.  
   *Fix:* Make the entire tool card a tap target with a minimum height of 48 px.
5. **[Low] Thai text inconsistency on Photobooth:** Retains Thai description while interface language is English.  
   *Fix:* Provide English translations for all app tiles when English is active.

---

### hub-modules

**(a) First impression:** A live checklist of connected robot bodies and motor parts.

**(b) Concrete problems & fixes:**
1. **[High] Overloaded with engineering jargon:** Strings like `reached RS485 #67 behind COM99 · this PC` terrify non-technical users.  
   *Fix:* Replace raw port paths with human labels: `Robot #67 (Cable)` or `Robot #1 (WiFi)` with a green connection dot.
2. **[High] Dual full-width action buttons inflate mobile height:** "Open module" and "Studio + monitor" create huge vertical blocks for every single robot.  
   *Fix:* Use one primary button ("Control Robot") and place secondary shortcuts inside an overflow menu `(...)`.
3. **[Medium] Raw terminal logs visible on desktop:** Cable detection logs (`COM99 — probing... CP210x`) clutter the bottom view.  
   *Fix:* Hide probing logs by default; show them only when "Show technical details" is checked.
4. **[Medium] Harsh yellow badge contrast:** Yellow `nong` tags have low contrast against white card backgrounds and glare in dark mode.  
   *Fix:* Switch to soft blue or slate badges with crisp dark/light text.
5. **[Low] "Rescan" button blends into background:** Low visual contrast makes it hard to spot when searching for a newly plugged robot.  
   *Fix:* Make "Rescan" a solid pill button with an explicit refresh icon.

---

### hub-firmware

**(a) First impression:** An empty or broken system update page.

**(b) Concrete problems & fixes:**
1. **[High] Redundant login wall on a blank page:** The entire screen is empty except for a card saying "Log in at the top of this page to use this", pointing to the login box already visible above.  
   *Fix:* Embed the login fields directly inside the card alongside an explanation: "Sign in to update robot software."
2. **[High] "Firmware" terminology is intimidating:** Teachers and designers do not know what firmware is.  
   *Fix:* Rename the tab and page title to "Robot Updates" or "Brain Software".
3. **[Medium] 85% wasted empty space:** No information is shown when logged out.  
   *Fix:* Display current installed versions and a friendly guide ("Your robots are on version 2.1; connect via USB to update") in read-only mode.
4. **[Low] Missing mobile / Android TV guidance:** Flashing boards cannot be done from an Android TV browser.  
   *Fix:* Add a clear note: "Software updates must be run from the main laptop plugged into the robot via USB."

---

### hub-network

**(a) First impression:** A connection setup screen to pair a phone controller or link other computers.

**(b) Concrete problems & fixes:**
1. **[High] Phone screen displays a QR code to "Open on a phone":** A user holding a smartphone cannot scan a QR code displayed on their own phone screen.  
   *Fix:* Detect mobile screens (<600 px) and replace the QR code with a one-tap "Copy Hub Link" button.
2. **[High] Intimidating raw IP addresses and hostnames:** Displays `http://192.168.100.36:20447/` and `WIN-RO2UQQ0R3FN.local`.  
   *Fix:* Hide technical port numbers behind a friendly link card: `Show WiFi Address` with a copy icon.
3. **[Medium] False red warning banner on load:** The login box shows `⚠️ log in first — that action changes something` before the user has touched anything.  
   *Fix:* Clear the error alert on initial page load; show it only after a rejected user tap.
4. **[Medium] Manual IP entry for other PCs:** Asks non-technical staff to type raw numbers like `10.123.98.148`.  
   *Fix:* Provide an automatic "Find Other Computers" scanner button, hiding manual IP boxes under an "Advanced" dropdown.
5. **[Low] Truncated navigation tabs on phone:** Tabs clip off abruptly (`es`, `Firmware`, `Network`).  
   *Fix:* Implement horizontal scrolling with touch friction for the tab bar.

---

### hub-settings

**(a) First impression:** A simple menu to change display colors and interface options.

**(b) Concrete problems & fixes:**
1. **[High] Developer source-code notes leaked into UI:** Description text reads: `Adding another theme is one block in shared/web/themes.css — it appears here by itself.`  
   *Fix:* Remove code file paths; replace with friendly text: "Choose a theme. Dark mode prevents screen light from spilling onto the stage."
2. **[High] Page is locked behind login for no reason:** A "Log in at the top of this page to use this" banner appears, even though theme switching is a harmless personal preference.  
   *Fix:* Allow theme switching freely without requiring an admin password.
3. **[Medium] Confusing theme label:** "Reconize" in the theme dropdown has no meaning to a teacher.  
   *Fix:* Rename to intuitive names like "Studio Light", "Stage Dark", and "High Contrast".
4. **[Low] Redundant "How much to show" card:** A dedicated section explains the "Show technical details" checkbox that sits 200 px above in the header.  
   *Fix:* Remove this section and place a small tooltip `(?)` directly next to the header checkbox.

---

### hub-complaints

**(a) First impression:** A customer complaint box, but actually an automated technical crash log.

**(b) Concrete problems & fixes:**
1. **[High] Misleading tab name "Complaints":** Sounds like visitor feedback rather than robot diagnostic logs.  
   *Fix:* Rename to "System Logs" or "Show Health Alerts".
2. **[High] Raw JSON and robotic log dumps:** Rows show raw code like `Sure! {"label": "Point...` and `Studio stopped answering for 15.4 s (sent automatically)`.  
   *Fix:* Translate into friendly status messages: "Nong Studio briefly paused (15s)" with an orange "Warning" badge.
3. **[Medium] Meaningless column of identical "open" buttons:** Provides no preview of what clicking will do.  
   *Fix:* Replace with "View Alert" buttons and color-code rows by severity (Red for Crash, Yellow for Delay, Green for Resolved).
4. **[Medium] Endless unpaginated vertical wall on mobile:** Forces long scrolling on phones.  
   *Fix:* Group logs by day ("Today", "Yesterday") and default to showing only the last 5 events with a "Load older" button.
5. **[Low] Overly chatty instruction copy:** Subtitle explains database persistence mechanics to the reader.  
   *Fix:* Simplify to: "Recent performance alerts. Tap any row to inspect details or mark resolved."

---

### help

**(a) First impression:** An illustrated visual guide and manual for running the robot show.

**(b) Concrete problems & fixes:**
1. **[High] Navigation pills bury help content on mobile:** On phones, 18 navigation buttons stack in a giant vertical cluster before the actual guide or search bar appears.  
   *Fix:* Collapse the topic menu into a drawer or top dropdown on mobile so the search bar and cartoon cards appear right at the top.
2. **[Medium] Search bar pushed down on phone:** Teachers needing quick help during a live show must scroll past dozens of links to find the search input.  
   *Fix:* Pin the "Find help..." search box directly under the header on mobile screens.
3. **[Medium] Dense text blocks under "Find your way around":** Multi-column small text (~12 px) is hard to skim on an Android TV or phone.  
   *Fix:* Convert paragraphs into bite-sized bullet points with bolded key terms.
4. **[Low] Pink active highlight looks like an error:** The bright pink "Start with a task" pill resembles an error alert.  
   *Fix:* Use the primary brand purple or blue for active topic selection.

---

### studio

**(a) First impression:** A 3D animation timeline to choreograph robot dance moves and poses.

**(b) Concrete problems & fixes:**
1. **[High] Dense wall of 10+ technical joint sliders:** Names like "L shoulder pitch", "R elbow roll", and "Shrug (rock..." overwhelm teachers.  
   *Fix:* Group sliders into collapsible sections ("Left Arm", "Right Arm", "Head & Body") and default to dragging handles directly on the 3D model.
2. **[High] 3D preview scrolls out of sight on mobile:** Sliders sit below the 3D canvas, so moving a slider means you cannot see what the robot is doing without scrolling back up.  
   *Fix:* Pin the 3D preview in a sticky top viewport (35% screen height) while sliders scroll beneath it.
3. **[Medium] Animation timeline completely missing on phone:** Keyframe timeline visible on desktop is cut off on phone view.  
   *Fix:* Add a compact floating playback bar at the bottom with Play, Next Keyframe, and Loop toggles.
4. **[Medium] Low slider thumb contrast in dark mode:** Dark blue slider handles blend into grey tracks on dim theater screens.  
   *Fix:* Use high-contrast bright teal or white circular handles with visible borders.
5. **[Low] Unstyled dance name input:** "my_move" in the header looks like debug text.  
   *Fix:* Place inside a labeled field: `Dance Name: [ My Move ]` next to a large "Save Dance" button.

---

### voice

**(a) First impression:** A voice control station to talk to the robot and customize AI answers.

**(b) Concrete problems & fixes:**
1. **[High] Missing microphone and live conversation area:** Status says "ready — ask a question", but the page is 80% empty white space with nowhere to speak or type!  
   *Fix:* Add a prominent "Tap to Talk" microphone button and a live chat bubble feed in the main area.
2. **[High] Prominent login box displaces speech tools:** Login inputs dominate the upper screen before any voice feature is shown.  
   *Fix:* Hide login behind a settings gear; allow voice testing freely.
3. **[Medium] Unclear category pill names:** Labels like "Who does it" and "Faces" lack context.  
   *Fix:* Add explanatory labels: "Voice Persona", "Listening Sensitivity", and "Screen Expressions".
4. **[Low] Misleading status text styling:** "ready — ask a question" in green looks like an interactive link but is static text.  
   *Fix:* Change to a clear status pill (`● Ready`) next to an "Ask a Question" action button.

---

### camera

**(a) First impression:** A live video monitor showing what the robot's camera sees.

**(b) Concrete problems & fixes:**
1. **[High] Dead-end text error with no recovery steps:** When disconnected, only a single sentence appears: "No camera answered...".  
   *Fix:* Show an illustrated empty state: a camera drawing, a clear heading ("Camera Not Connected"), and 3 checklist steps ("1. Check USB/Power cable", "2. Connect to Show WiFi", "3. Tap Rescan").
2. **[High] Developer jargon in error message:** Sentence ends with "and its type has to be cam". Non-technical staff cannot fix code types.  
   *Fix:* Remove code terms; change to: "Make sure the camera is turned on and paired to the hub."
3. **[Medium] Giant login box on an empty screen:** Takes up half the card when there is nothing connected to control.  
   *Fix:* Hide login card when in empty/disconnected state.
4. **[Low] "Look again" button lacks loading state:** Clicking gives no visual feedback that a network search is happening.  
   *Fix:* Display a spinning icon and "Searching for cameras..." while scanning.

---

### tv

**(a) First impression:** A show director's remote control to trigger robot movements, sounds, and speech on stage.

**(b) Concrete problems & fixes:**
1. **[High] Conflicting robot selectors:** A "Choose an available Nong" dropdown sits in the header, while another "Choose Nong" dropdown sits inside the controller card.  
   *Fix:* Keep one global robot selector in the top bar; auto-select if only one robot is powered on.
2. **[High] Programmer filenames in sequence buttons:** Shows ugly file names like `all.yaml`, `Loooooooooooo...`, and `tangVongSungl...`.  
   *Fix:* Display clean human titles ("Full Welcome Dance", "Intro Bow") and show file duration tags (`0:45s`).
3. **[Medium] Dual STOP buttons create confusion:** Global header STOP button sits above the controller's "⏹ Stop" button.  
   *Fix:* Relabel the controller button to "Pause Routine" and keep the header button as "Emergency All-Stop".
4. **[Medium] Cramped 2-column buttons on phone:** Narrow sequence buttons truncate song names on mobile screens.  
   *Fix:* Use a clean single-column list on mobile with generous touch height (>48 px).
5. **[Low] Raw servo telemetry visible on desktop:** "Joint Monitor (Real-time)" lists raw motor codes (`L_SH_P`, `L_EL_P`).  
   *Fix:* Keep motor diagnostics collapsed inside the "Tech Monitor" tab.

---

### gacha

**(a) First impression:** A prize booth manager to reward audience members from gachapon machines.

**(b) Concrete problems & fixes:**
1. **[High] Disorganized workflow:** Presets, sub-tabs, manual prize forms, and event timers compete for attention simultaneously.  
   *Fix:* Organize into 3 clear steps: 1. Select Event → 2. Choose Prize → 3. Press Big "Dispense Prize" Button.
2. **[High] Deceptive green status for disconnected hardware:** "0 of 0 machines answering" is styled in bright green text, looking like a success state!  
   *Fix:* Use red or orange text when 0 machines are connected (`● No prize machines online`).
3. **[Medium] Cluttered duplicate dispense buttons:** "Give", "Give one anyway (admin)", and "Can they have one?" sit side by side without clear distinctions.  
   *Fix:* Keep one primary "Dispense Prize" button; show a confirmation popup if the visitor has already received a prize.
4. **[Medium] Unstyled floating helper text:** Text "the person in front of the camera" floats awkwardly between input boxes.  
   *Fix:* Turn into a styled checkbox toggle: `[✓] Dispense to visitor at camera`.
5. **[Low] Cramped mobile form layout:** Dropdown "Kind [v]" and input "for [name]" wrap awkwardly on phone screens.  
   *Fix:* Stack input fields vertically with full-width tap targets.

---

### photobooth

**(a) First impression:** A guest photo souvenir station where visitors take framed pictures with the robot.

**(b) Concrete problems & fixes:**
1. **[High] 90% blank screen with zero visual appeal:** Shows only three plain text buttons on a vast empty card.  
   *Fix:* Display an attractive live preview card showing current photo frames, camera status, and sample souvenir prints.
2. **[High] Technical backend explanation instead of user guidance:** Text reads: "Photobooth runs beside Mice on this PC. The first start also opens a browser tab that becomes the booth screen."  
   *Fix:* Replace with simple teacher instructions: "Click Launch to open the photo screen on your TV or guest display."
3. **[Medium] Perpetual "checking..." status:** Top status indicator stays stuck on "checking..." indefinitely without confirming readiness.  
   *Fix:* Resolve quickly to a clear status pill (`● Ready` or `⚠️ Photo App Not Open`).
4. **[Low] Unclear button hierarchy:** "Open booth screen ↗" and "Open admin ↗" look like technical dev links.  
   *Fix:* Make "Launch Guest Photo Screen" a prominent, full-width action button; style "Settings" as a small secondary link.

---

### TOP 10 Changes Across All Screens (Ranked by Benefit per Effort)

1. **Remove the giant login card from the top of every screen:** Move login to a small key icon in the navbar. Frees up 40% of the screen across all pages so users see their show tools immediately. *(Very High Benefit / Low Effort)*
2. **Fix false-positive green status on Gacha:** Change "0 of 0 machines answering" from green to warning amber/red so teachers immediately notice disconnected machines. *(High Benefit / Minimal Effort)*
3. **Hide the phone QR code on mobile screens in hub-network:** Swap the un-scannable QR code on mobile for a one-tap "Copy Link" button. *(High Benefit / Low Effort)*
4. **Scrub developer code notes from UI text:** Remove references to `shared/web/themes.css`, code types (`type has to be cam`), and raw port paths (`RS485 #67 behind COM99`). *(High Benefit / Low Effort)*
5. **Add a live mic button and test box to Voice:** Turn the empty 80% blank space into an instant voice tester with a microphone button. *(Very High Benefit / Medium Effort)*
6. **Clean up robot dance names on TV Remote:** Replace `all.yaml` and truncated strings with clean human titles and song durations. *(High Benefit / Low Effort)*
7. **Add an illustrated empty/recovery card to Camera:** Replace the one-line error with clear step-by-step connection checks. *(High Benefit / Low Effort)*
8. **Collapse mobile Help categories into an accordion/drawer:** Bring the search box and cartoon tutorial cards to the top of the mobile screen. *(High Benefit / Medium Effort)*
9. **Pin 3D robot preview on mobile Studio:** Keep the 3D model sticky at the top while joint sliders scroll below, preventing endless up-and-down scrolling. *(High Benefit / Medium Effort)*
10. **Tone down the persistent red STOP button on the Hub header:** Use a neutral outline while idle so teachers do not mistake it for a system crash. *(Medium Benefit / Low Effort)*

---

### 3 Things That Are Already Good and Must Not Be Lost

1. **"The hard parts, in pictures" in Help:** The 8 illustrated cartoon step cards (plugging USB cables, WiFi pairing, timeline poses, scanning QR codes) are friendly, visual, and reassuring for non-technical teachers.
2. **Direct Quick Speech buttons on TV Remote:** The preset phrase buttons ("🙏 Hello", "👋 Welcome", "✨ Thank you", "🎉 Have a happy day") are intuitive, fast, and ideal for quick live stage interactions.
3. **Flawless Dark Mode color parity across tools:** The dark theme across Studio, TV Remote, and Hub maintains dark theater compliance, preventing harsh white light spills into show venues.
