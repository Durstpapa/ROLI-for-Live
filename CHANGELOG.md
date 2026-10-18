# Changelog

## Unreleased (fork)

- Combine connection and scale/error status on one 10-point line, vertically centering
  the text and connection dot together in the full-width footer. Remove the separate
  connection text object; preserve complete annotations and connection-state semantics.
  Raise the dot one layout unit relative to the text-box center for optical alignment
  with the visible letters, based on the user's Live screenshot. User confirmed the
  revised alignment in Live (2026-10-18).
- Give the connection dot and connection label a dedicated row, adjusting the dot's
  vertical placement. Combine scale source, Chromatic/Scale mode OFF state and clip
  fallback reason in the full-width row below. Retain explicit source errors and full
  annotations; distinguish an unconfirmed connection from an explicit disconnection.
- Give status messages a full-width bottom strip across all three columns, expanding
  text width from 114 to 350 units and restoring consistent 10-point text. Combine
  connection and scale source on the first line, with detail on the second and full
  status text retained in the annotation. Move the lower
  brightness section up, shorten column dividers and span the status divider across
  the device without changing device size, control text sizes or bridge behavior.
- Add independent **Pitch bend** and **Pressure** native switches in a separate Expression
  column (376-unit device width). Save both choices with schema 6, default them ON to
  preserve prior behavior, and expose preferences/profile support through bridge v8
  while retaining older replies. Keep MPE enabled, performance MIDI unfiltered, and
  expression independent of lighting and palette. Leave Piano M/LUMI expression untouched.
- Capture native MPE, pitch-bend and pressure settings for restoration on shutdown and
  mode changes. Extend legacy snapshots with currently observed expression values
  without replacing lighting recovery data. Scale lighting OFF restores lighting only.
  Add simulated-host coverage for independent toggles, migrations, cancellation,
  reconnection, restoration, rejected saves, capability gating and duplicate devices;
  hardware qualification of the new OFF states remains pending.
- Report **Live Scale mode OFF / Chromatic** or **Clip Scale mode OFF / Chromatic**
  when the active source disables Scale mode. Retain explicit clip-fallback errors and
  native-lighting status. Add a v7 bridge flag for the effective source's Scale mode
  without changing older bridge replies or hardware lighting behavior.
- Reduce status text to 9 points while retaining 10-point controls. Add a non-clickable,
  theme-accent connection dot driven by reported keyboard readiness, with a neutral
  unconfirmed/disconnected state and explicit status/error text retained.
- Clarify the idle clip-following status as **Using Live scale** with **No playing clip**
  on the next line, replacing **Live scale (no clip)** without changing scale selection.
- Add native, theme-aware divider lines between the two brightness controls, between
  the control columns and above status, without changing layout or control behavior.
- Use consistent 10-point text throughout ROLI Controls, retaining the compact layout
  and room for the longer button labels.
- Move **Follow clip scale** directly below **Scale lighting**, ahead of Key colors,
  Root color and **Show playing notes**. Rename the former Clip scale and Playing notes
  buttons and clarify the clip-following
  tooltip: playing clips supply their own Scale mode independently of the global switch,
  with fallback to Live's global settings. Keep behavior, preferences and bridge wiring
  unchanged; update generated-layout and confirmed-label regressions.
- When the chosen Live/clip scale source has Scale mode OFF, send Chromatic along with
  Show Scale OFF so native Rainbow stops filtering notes. Restore the selected scale
  on re-enable without writing Live/clip metadata. Cover global toggles in all palettes
  and clip-specific Rainbow toggles. User confirmed in Live that Scale mode OFF shows
  the full rainbow and ON restores scale highlighting on Piano 49 (2026-10-18).
- Add native Rainbow as the third Key colors choice (White → Track → Rainbow), retaining
  Live/clip scale following, global brightness, playing-note feedback and native playing
  mode selection. Preserve but disable Root color and Background Brightness in Rainbow,
  which ignores custom RGB colors. Migrate settings schemas 1-4 to named palettes in
  schema 5, retain legacy bridge methods, and add the v6 three-color bridge.
- Add palette-cycle, migration, failure, scale/clip, reconnect and restoration regressions.
  User confirmed native Rainbow scale highlighting and custom RGB limitations in
  Dashboard on Piano 49 (2026-10-18). Initial integrated testing exposed the wrong native
  scheme ID (3); use the Dashboard-observed Rainbow ID 4 and pin it in a regression test.
  User confirmed corrected Rainbow follows scales and native lighting returns after
  quitting on Piano 49 / Live 12.4.15b7. LUMI Rainbow remains unqualified on hardware.
- Stop lighting callbacks and note feedback before shutdown restoration; explicitly
  release Piano 49 BLOCKS API mode after restoring captured settings, without cycling
  native modes or changing saved preferences. Report unverified restoration requests
  honestly and retain the recovery snapshot on rejected restore sends. Add shutdown
  ordering, reentry, LUMI, and failure-path regressions. User confirmed native lighting
  returns automatically on Piano 49 / Live 12.4.15b7 when quitting with Scale lighting
  left ON (2026-10-17). LUMI shutdown and crash recovery are not hardware-qualified by
  this test.
- Change ROLI Controls to a Max Audio Effect with direct stereo passthrough so it can
  live on the Master/Main track inside an Audio Effect Rack. Keep the global controls
  and selected-track lighting behavior unchanged. Add audio routing and device-type
  regression checks; existing MIDI Effect instances must be replaced with the new build.
- Set native slider double-click reset values to Global Brightness 100% and Background
  Brightness 25%, keeping initialization disabled so loading the device does not
  overwrite saved preferences. Add generated-device regression assertions.
  User confirmed both double-click resets work in Live with LUMI Keys (2026-10-17).
- Record a successful user test on LUMI Keys / Piano M with macOS and Live 12.4.15b7
  (2026-10-17). Live recognized the existing `LKB` profile and accepted brightness
  adjustments; the user reported everything working and separately confirmed correct
  connection-status detection when powering the LUMI off and on. Firmware, lighting/state
  restoration after reconnect, script-shutdown restoration, recovery scenarios and a
  newer Piano M-branded unit were not separately qualified.
- Clarify the product as a ROLI Piano integration, not a general ROLI controller script.
  Distinguish tested Piano 49 support from the LUMI Keys / Piano M lighting profile;
  document separate Lightpad routing and exclude Lightpad/Seaboard
  integration without renaming installed components.
- Keep native slider parameter engines enabled (Hidden visibility, no initialization)
  so their numeric ranges work. Validate native 0/100 readback before enabling controls,
  rather than relying only on generated patch structure and mocked bridge tests.
- Add saved **Global brightness** and **Background intensity** sliders beside the
  unchanged button stack in a 240-unit native-theme device. Leave hardware brightness
  untouched until explicitly changed; keep global brightness active with Scale lighting
  off and restore captured native brightness when the script disconnects.
- Migrate preferences to schema 4 and preserve legacy bridge methods with a new v5 reply.
  Safely extend legacy recovery snapshots with observed brightness, retaining original
  captured colors. Coalesce slider writes and never apply startup/default widget values.
- Promote the successful native background RGB experiment to a saved percentage control.
  User confirmed useful contrast at 25% with native highlights at velocity 127 on Piano 49 /
  Live 12.4.15b7 (2026-10-16). After the native slider range correction, the user
  confirmed both brightness controls work on the same setup.
- Wire both playback-feedback paths to the same test velocity. A temporary velocity-64
  trial retained the successful 25% background. Live's startup log confirmed the trial
  was loaded, but the user saw no perceptible highlight-brightness change on Piano 49
  (2026-10-16). Restore feedback 127; do not expose this as a brightness control.
- Determine Arrangement scale source from running transport, timeline bounds and track
  override state rather than additionally requiring the clip's own `is_playing` flag.
  Add an explicit empty D-minor / C-major clip boundary regression.
- Add persistent, opt-in **Clip scale** following for the selected track's playing MIDI
  clip, independent of clip selection and Playing notes. Read clip root, mode and scale
  metadata on compatible hosts (introduced in Live 12.4.15b1); fall back explicitly to
  Live scale on stop, gaps, unavailable API or read errors without changing Live state.
- Share Session/Arrangement clip discovery between scale and note feedback, respecting
  Session stop/override states rather than lighting silent Arrangement clips underneath.
- Add the fifth native-theme control without increasing device width or reducing
  button targets. Migrate preference schemas 1/2 to 3 without resetting saved values;
  preserve existing bridge replies and add v4 with scale-source diagnostics.
- Cover clip-scale selection independence, handoffs, edits, fallback, reconnect,
  persistence and UI/bridge behavior with simulated-host and generated-device tests.
  User confirmed empty D-minor / C-major Arrangement transitions on Piano 49 with
  Live 12.4.15b7 after the playback-flag correction and restart (2026-10-16).
  Session clip-scale following is not yet separately hardware-qualified.
- Use a real elapsed-time deadline for keyboard readiness even if Live suspends display
  callbacks, and rediscover the active surface on every device poll to reject stale IDs.
- Show neutral **Disconnected** status when the ROLI surface is missing or the keyboard
  stops responding, without assuming a power, cable, or MIDI issue. Reconnect automatically.
- Order controls as Scale lighting, Key colors, Root color, Playing notes. Expire
  keyboard readiness after roughly five seconds without real replies, probe liveness,
  and reinitialize lighting after reconnection without resetting saved choices.
- Add isolated, opt-in temporary-lighting recovery probe with pinned ROLI/JUCE build
  dependencies and real Littlefoot VM tests. Green pulse remains offline-only pending
  Piano restoration verification; no installed integration changes.
- Add independent saved **Root color** control. Off makes roots match other lit keys
  in both color modes, without darkening or disabling them. Existing three-setting
  preference files migrate without resetting their values.
- Save global color, scale-lighting, and playing-note preferences beside the script in
  `settings.json`, with atomic writes and explicit read/save errors.
- Add independent Scale lighting and Playing notes controls; Scale lighting off restores
  captured pre-script lighting without changing navigation or MPE. Playing notes off
  disables both feedback paths and clears outstanding feedback notes.
- Rename the color button to **Key colors: White / Track** and retain compact native styling.
- Compact Max device layout at one-third of the original width, with native Live theme
  colors, stock-sized text, and no duplicated title/development credits.
- Default to white keys with track-colored roots on script startup, including when no
  Max device is loaded. The live button can still switch to the original track colors.
- Fix repeated color-switch clicks re-sending on: the Max button now inverts confirmed
  Python state instead of relying on the widget's local toggle value.
- Experimental code-first Max for Live **ROLI Controls** device: switch live between
  track colors and white keys with track-colored roots, without restarting Live.
- Versioned Python control-surface bridge, acknowledged UI state, explicit connection
  errors, and direct MIDI pass-through outside JavaScript.
- Automated simulated keyboard, JavaScript bridge, and generated-device structural tests.
- Requires Max 9. Device loading and live switching between both schemes, including
  following selected-track root colors, verified on macOS with Live 12.4.15b7 and
  a ROLI Piano 49 (2026-10-16).

## v0.1.1

Fixes the Mac installer.

- **Mac:** after unzipping by double-click, the installer could stop with
  "cp: …/ROLI_for_Live/*.py: No such file or directory". The zip now creates its folders with
  normal permissions, and the installer fixes an unreadable folder before copying.
- **Mac:** new one-line install, no download or security prompt needed. Paste into Terminal:
  `curl -fsSL https://raw.githubusercontent.com/ehsuun/ROLI-for-Live/main/install.sh | sh`

## v0.1.0 (first preview)

First public preview of ROLI for Live, a Live 12 MIDI Remote Script for ROLI keyboards.

Tested on a ROLI Piano 49 (firmware 1.5.0) with Ableton Live 12.4.6 Suite on Windows 11.

### Features
- **Scale guide:** the keys show Live's current root note and scale when Scale mode is on.
- **Track colors:** keys take the selected track's color; the root note is brighter.
- **Playing notes:** keys light white for the notes in the selected track's playing clip
  (Session and Arrangement, loops included).
- **Track buttons:** the keyboard's `<` / `>` buttons select the previous/next track.
- **Native MPE:** notes, per-note pitch bend and pressure go straight into Live. If the
  keyboard's pitch bend/pressure are switched off, the script turns them on.
- **Leaves no trace:** the keyboard's own light settings come back when Live closes.
- **LUMI Keys (experimental, untested):** lights only (scale, track color, playing notes).

### Install
Download `ROLI-for-Live-v0.1.0.zip` and unzip it. Quit Live.

- **Windows:** double-click **Install on Windows.cmd**.
- **Mac:** in Finder choose Go → Go to Folder…, enter
  `~/Music/Ableton/User Library/Remote Scripts` (create `Remote Scripts` if it's missing), and
  drag the **ROLI_for_Live** folder into it.

Then, once, in Live's Settings → Tempo & MIDI, choose **ROLI for Live** as a Control Surface
(Input/Output: ROLI Piano) and turn on Track and MPE for the ROLI Piano input.

About the Mac installer: **Install on Mac.command** isn't signed by Apple, so macOS warns it
"could not verify it is free of malware" and offers to move it to the Trash. It's safe but not
needed; dragging the folder does the same. To use it anyway: click Done, then System Settings →
Privacy & Security → Open Anyway. Or open Terminal and run
`sh ~/Downloads/ROLI-for-Live-v0.1.0/install.sh`.

### Known limits
- Live scales the keyboard doesn't have built in (e.g. Phrygian Dominant, Hirajoshi) show
  the root note only.
- Arpeggiator/Chord output doesn't light up; Live doesn't give those notes to scripts.
- macOS, LUMI Keys, and setups without ROLI Connect running are untested.
- Live doesn't select the control surface automatically; it's a one-time step.
