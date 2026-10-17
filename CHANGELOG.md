# Changelog

## Unreleased (fork)

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
