# UX review by GPT (Codex), 2026-11-22

Asked by the user: "check the UX/UI, let GPT help". Reviewed as a non-technical person.

**Method.** 14 screens (hub tabs Home, Tools, Modules, Firmware, Network, Settings, Complaints; Help; Studio; Voice; Camera; TV; Prize machines; Photobooth) shot in Edge at 1280 px and 390 px, light and dark theme, English, against the QC hub with fake modules. Each screen is one 2x2 sheet. Codex (default model of the PC, gpt-6.1-sol) read the sheets and wrote the findings below. Findings are leads, not facts: check each against the code before changing it (project rule).

**Limits.** Pictures only: Chrome 75, real speed and signed-in flows were not assessed. The 390 px view is cut at 1500 px high. Studio, Voice and TV ran without a robot. The board page and Reconize (faces) were not shot.

**Gemini.** Not run. `agy` (signed in, Gemini 3.8 Flash High listed) could not open the sheets in headless mode: reading a file needs a "command" permission that print mode cannot ask for. The only ways are `--dangerously-skip-permissions` or an allow rule in agy settings; I did not grant either on my own. When the user allows one, run: `agy -p "<same prompt>" --mode plan --model gemini-3.8-flash-high --add-dir <sheets>` with the prompt in `docs/ux_review_prompt.txt`.

## Findings (GPT)

**hub-home** — “This is where I find my robots and open their tools.”

- **High:** “Your modules” follows six tall tool cards, beyond the phone crop. Put connected robots and their status above the tool list.
- **Medium:** The large login form dominates even though browsing is free. Start with a compact “Sign in to control robots” button that expands the form.
- **Medium:** Phone Report and Shortcuts buttons look shorter than 44 px. Give them at least 44 px height.

**hub-tools** — “I can open tools and manage apps on this computer.”

- **High:** The selected Tools label is faint in both themes. Use a solid selected pill with clearly contrasting text, like Home.
- **Medium:** Apps shows only “Loading…”. Use “Looking for installed apps…” and provide a retry if loading fails.
- **Medium:** App management follows the entire tool grid. Add a “Manage installed apps” link above the grid so phone users can reach it quickly.

**hub-modules** — “This lists connected robots, but I need help choosing how to open one.”

- **Medium:** “Every module — one row each” describes the layout. Rename it “Connected robots and devices”.
- **High:** Connection lines expose “RS485”, “COM99” and routing details while technical details are unchecked. Show “Connected through this computer”; place the route under technical details.
- **Medium:** “Open module” and “Studio + monitor” do not explain their different purposes. Use “Control robot” and “Open Studio”, with short descriptions.
- **Medium:** On phones, the favourite star occupies a separate line above the name. Put a 44 px favourite button beside the name and group the two opening buttons beneath it.

**hub-firmware** — “I must sign in, but I cannot tell what this page does.”

- **High:** There is no visible task heading or explanation. Add “Update robot software” and “Install an update on a connected robot.”
- **Medium:** “Log in at the top…” makes users locate another control. Use “Sign in to update robot software” and focus the existing username field.
- **Medium:** The selected Firmware label is difficult to read. Give it the same high-contrast selected style as Home.

**hub-network** — “I can open this on my phone or connect another show computer.”

- **High:** “That action changes something” does not identify the blocked task. Name the attempted action, for example, “Sign in to add this computer.”
- **Medium:** Long addresses and computer identifiers compete with the QR instructions. Add “Copy phone link”; move machine identifiers under technical details.
- **Medium:** Phone tabs are clipped at both edges without clear navigation guidance. Use a labelled page chooser or wrapping tabs.
- **Medium:** “Looking for modules…” gives no visible outcome. When searching finishes, show the robots found or “No robots found” with “Search again”.

**hub-settings** — “I can change the appearance and how much information is shown.”

- **High:** The selected Settings label has weak contrast in both themes. Use a solid, readable selected pill.
- **Medium:** “Colour”, “Reconize” and “Midnight” make a simple choice harder to understand. Use “Appearance”, “Light” and “Dark”; retain theme names as secondary text.
- **Medium:** The card includes a code path and repeats the dark-theme explanation. Remove implementation instructions; keep “Dark reduces light in the show area.”
- **Medium:** A general sign-in notice precedes appearance controls, making permissions unclear. Label which settings need sign-in beside those settings.

**hub-complaints** — “This is a history of problems reported by people or detected automatically.”

- **Medium:** “Complaints” sounds personal, and “open” could mean status or action. Rename the page “Problem reports”; use “View report” for buttons.
- **High:** Phone rows emphasise dates while cutting the problem down to “Studio stopped ans…”. Show a readable two-line problem summary first, then date and status.
- **Medium:** Some summaries contain raw structured data. Show a plain-language summary and put the original details inside the report.
- **Medium:** The long list has no visible search or filters. Add “Unresolved”, “Resolved” and “Automatic alerts”, plus search.

**help** — “This guide should help me choose and complete a task.”

- **High:** Phone navigation occupies a large area before the introduction and search. Collapse it into “Browse help topics” and put search first.
- **High:** The long “Find your way around” explanation precedes task choices. Move “What do you want to do?” directly below search.
- **Medium:** Desktop picture captions are tiny. Increase caption text and card size so instructions remain readable.
- **Medium:** “QC suite”, “Transports” and “Command language” need specialist knowledge. Use “Check the system”, “Connections” and “Robot commands”.

**studio** — “I can pose a robot and arrange movements into a show.”

- **High:** Phone slider labels are cut off, making similar joints hard to distinguish. Use full, wrapping labels with plain motion names, such as “Bend left elbow”.
- **High:** No Stop control is visible in the phone crop. Keep a clearly labelled “Stop robot” control visible when robot movement is available.
- **Medium:** Sliders and number fields are tightly packed. Give each row and number control a 44 px touch area.
- **Medium:** The large phone preview pushes pose controls far down. Add “Collapse preview” and a compact preview option.

**voice** — “I should be able to ask the robot a question or change how it answers.”

- **High:** Talk is selected, but its main area is blank. Show a question box and “Ask”, or an explicit explanation of what is required. The cause of the blank area is not visible.
- **Medium:** “Who does it” is vague. Rename it “Who answers?” and explain the available choice when opened.
- **Medium:** Phone navigation pills look shorter than 44 px. Increase their touch height while keeping the wrapping layout.

**camera** — “This should find cameras and show their pictures.”

- **High:** The empty message ends with the technical requirement “type has to be cam”. Replace it with “No cameras found. Turn on your camera, connect it to this network or computer, then search again.” Put device-type instructions under technical details.
- **Medium:** Login dominates the otherwise empty page. Put the camera result and recovery steps first.
- **Medium:** “Look again” is a small header control. Use a 44 px “Find cameras” button beside the empty message.

**tv** — “I can choose a robot, play a saved show and make it speak.”

- **High:** “Ready” appears while the robot selector still says “Choose Nong”. Show “Choose a robot to begin” until a robot is selected.
- **Medium:** The phone card says “14 files”, but only ten are visible with no obvious route to the rest. Add “Show all 14” or a clear scrolling cue.
- **Medium:** Phone mode tabs disappear beyond the right edge. Use a mode chooser with complete names.
- **Medium:** “Silenced All” is unclear as an action or status. Use “Mute all speech” for the button and “Speech muted” for the status.

**gacha** — “I can give prizes and set the rules for an event.”

- **High:** Prize and event controls appear before the sign-in notice. Put “Sign in to give prizes or change event rules” above those controls.
- **Medium:** “Kind”, “name, or empty” and “Can they have one?” require interpretation. Use “Prize type”, “Guest name (optional)” and “Check if this guest can win”.
- **High:** “New event (counts to zero)” sits among everyday controls. Separate it and rename it “Start a new event and reset counts”; explain the reset before confirmation. Confirmation behaviour is not visible.
- **Medium:** Presets do not show their rules. Display the prize limits beneath each preset before it is applied.

**photobooth** — “I can open the guest photo screen or manage the booth.”

- **Medium:** “Checking…” does not say what is being checked. Use “Checking photobooth…” followed by a clear ready or unavailable state and next action.
- **Medium:** “Open booth screen” and “Open admin” could be clearer. Use “Open guest screen” and “Manage photobooth”.
- **Medium:** “This PC” is confusing on a phone. Name the show computer and state where the guest screen opens; that destination is not visible here.

**Top 10 changes, ranked by likely benefit per effort**

1. Fix selected-tab contrast across both themes. **Low effort**
2. Use clear action names and consistent “Sign in” wording. **Low**
3. Make phone buttons and input touch areas at least 44 px. **Low–medium**
4. Replace vague errors and loading messages with named tasks and next steps. **Low–medium**
5. Give Voice’s blank Talk view a usable starting state. **Effort uncertain**
6. Hide connection jargon, code paths and raw report data under technical details. **Low–medium**
7. Make phone navigation complete and discoverable. **Medium**
8. Compact shared login forms and place permission explanations beside affected actions. **Medium**
9. Improve Studio’s visible Stop control and readable joint labels. **Medium**
10. Put Help search and task choices before navigation and long explanations. **Low–medium**

**Three things to keep**

- Prominent red Stop controls on the hub and TV controller.
- Consistent Hub return, language and technical-detail controls.
- Friendly illustrations, picture-based help, and light/dark choices.

Chrome 75 compatibility, actual loading speed and unseen signed-in workflows cannot be assessed from these pictures.
