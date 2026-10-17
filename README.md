<p align="center">
  <img src="docs/logo.svg" alt="ROLI for Live" width="420">
</p>

<p align="center">
  <b>Your ROLI keyboard, lit up by Ableton Live.</b><br>
  Scales, track colors and playing notes on the keys, with MPE expression untouched.
</p>

<p align="center">
  <img alt="Ableton Live 12" src="https://img.shields.io/badge/Ableton%20Live-12-ff9a3c">
  <img alt="ROLI Piano 49" src="https://img.shields.io/badge/ROLI%20Piano-49-ffd27a">
  <img alt="Windows tested" src="https://img.shields.io/badge/Windows-tested-3c9a5f">
  <img alt="macOS tested" src="https://img.shields.io/badge/macOS-tested-3c9a5f">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
</p>

---

**ROLI for Live** is a small MIDI Remote Script that runs inside Ableton Live and turns a ROLI
keyboard into a Push-style partner for Live. No extra app, no driver, no Max for Live, and
nothing to add to your Live Sets.

> Independent community project. Not affiliated with or endorsed by ROLI or Ableton.

## Features

| | |
|---|---|
| 🎼 **Scale guide** | The keys show Live's current root note and scale (when Scale mode is on). |
| 🎨 **Track colors** | White keys with roots in the selected track's color by default; optional live controls switch to track-colored keys with brighter roots. |
| ✨ **Playing notes** | Keys light white as the selected track's clip plays (Session and Arrangement). |
| ⏮️⏭️ **Track buttons** | The keyboard's `<` / `>` buttons select the previous/next track. |
| 🎹 **Native MPE** | Per-note pitch bend and pressure go straight into Live; the script never touches your notes. If the keyboard's bend/pressure are switched off, it turns them on. |
| ↩️ **Leaves no trace** | Your keyboard's own light settings come back when Live closes. |

## Install

Takes a minute: put one folder in place, then pick it once in Live.

### Easiest: download a release

Quit Live, download **ROLI-for-Live-vX.Y.Z.zip** from the
[Releases page](https://github.com/ehsuun/ROLI-for-Live/releases) and unzip it. Then:

**Windows:** double-click **Install on Windows.cmd**.

**Mac:** paste this line into **Terminal** and press Return. It downloads the latest release
and installs it, with no security prompts (you don't need the zip):

```sh
curl -fsSL https://raw.githubusercontent.com/ehsuun/ROLI-for-Live/main/install.sh | sh
```

Or drag the folder in yourself:
1. In Finder choose **Go → Go to Folder…**, enter `~/Music/Ableton/User Library/Remote Scripts`
   and press Return. If it doesn't exist, open `~/Music/Ableton/User Library` and create a
   folder named `Remote Scripts`.
2. Drag the **ROLI_for_Live** folder from the unzipped download into it.

> **Why not double-click on Mac?** The included **Install on Mac.command** isn't signed by
> Apple, so macOS warns that it "could not verify it is free of malware" and offers to move it
> to the Trash. It's safe, but you don't need it: dragging the folder does the same thing. If
> you prefer the installer, click **Done** (not Move to Trash), open **System Settings →
> Privacy & Security**, click **Open Anyway** next to it and confirm. Or open Terminal and run
> `sh ~/Downloads/ROLI-for-Live-v0.1.1/install.sh` (adjust the path if you unzipped it elsewhere).

Then do the one-time setup in Live below.

### Manual install

#### Windows

1. Quit Live. Download this repository (**Code → Download ZIP**) and unzip it.
2. Copy the `src\ROLI_for_Live` folder into `Documents\Ableton\User Library\Remote Scripts\`
   (create `Remote Scripts` if it's missing).
   *Or* right-click `install.ps1` → **Run with PowerShell**; it finds your User Library for you.
3. Connect the keyboard and start Live.

#### macOS

1. Quit Live. Download and unzip this repository.
2. Copy `src/ROLI_for_Live` into `~/Music/Ableton/User Library/Remote Scripts/`.
   *Or* run `sh install.sh` from the unzipped folder in Terminal.
3. Connect the keyboard and start Live.

### One-time setup in Live

In **Settings → Tempo & MIDI**:
1. In an empty **Control Surface** row choose **ROLI for Live**, with Input and Output **ROLI Piano**.
2. Under **Input Ports**, turn on **Track** and **MPE** for **ROLI Piano**.

Live remembers this. For playing, pick an MPE instrument (Drift, Meld, Wavetable…) and set its
pitch bend range to **48** to match the keyboard.

> Moved your User Library? Use the location shown in **Settings → Library** instead.
> To update, replace the folder and restart Live. To uninstall, quit Live and delete the folder.

## Optional live controls (experimental)

The code-first **ROLI Controls** Max for Live device provides four buttons:

| Control | Behavior |
|---|---|
| **Scale lighting: ON / OFF** | On follows Live's scale, root and track colors. Off restores all lighting settings captured before the script took control, not a factory reset. Track navigation and MPE stay active. |
| **Key colors: White / Track** | White keys with track-colored roots, or track-colored keys with brighter roots. Used only when Scale lighting is on. |
| **Root color: ON / OFF** | Off removes the special root color: root keys match the other lit keys in White and Track modes. It does not make them dark or disable those notes. Used only when Scale lighting is on. |
| **Playing notes: ON / OFF** | Independently enables/disables temporary white highlights for sounding clip notes and Live's note feedback. It does not switch root-note coloring off. Turning it off clears feedback notes; normal performance MIDI is unaffected. |

Without saved preferences, the defaults are **White**, **Scale lighting ON**, and
**Playing notes ON**, and **Root color ON**, including when no Max device is loaded. The keyboard's active
scale/display mode still determines which keys display the selected colors.

Requires Max for Live and **Max 9** (the device uses `v8` JavaScript). This is an
experimental fork feature, not included in the upstream release downloads.

1. Quit Live and install this checkout's updated Python script once using the manual
   installation steps above. Do not use the upstream download command for this feature.
2. With Node.js 18 or newer installed, run:
   ```sh
   npm ci --ignore-scripts
   npm run build:m4l
   npm run test:m4l
   ```
3. Start Live with the ROLI control surface enabled. Drag
   `dist/m4l/ROLI Controls.amxd` onto a MIDI track, before any instrument.
4. Wait for **Connected**, then use the four buttons. No script reinstall or Live restart
   is needed for subsequent changes.

The UI reads the script's accepted settings every 500 ms. **Connected** means keyboard
initialization is complete and a real keyboard reply was received within roughly five
seconds; it does not verify physical LED delivery. A read-only mode query every two
seconds checks liveness even on profiles without API-mode acknowledgments. After a
response timeout the status returns to **Disconnected**, discovery restarts,
and saved lighting is reapplied on reconnection. API retry timestamps do not count as
keyboard replies. Pre-script lighting recovery data and saved choices are preserved.
The timeout uses monotonic elapsed time, including when Live stops calling the script's
display-update callback. Each UI poll rediscovers the currently listed surface rather
than trusting an old API object's ID after MIDI ports disappear or scripts are replaced.
After restarting Live and reloading the device, the user confirmed power-off changes
the status to **Disconnected** on the Piano (2026-10-16).
**Disconnected** also appears before initialization finishes or when Live has not
exposed the ROLI script. The status does not assume a cause: check Piano power, the
USB connection, and Live's MIDI settings as needed. Polling continues automatically,
so restoring the connection does not require reloading the device.
Missing/older scripts and ambiguous multiple ROLI
surfaces disable all controls and display an explanation; details also appear in Max's console.
Only one ROLI control surface is supported by this proof of concept.
Each button click reads the script's current setting and requests its opposite; the
button labels display only confirmed script state. Key colors and Root color are disabled
while Scale lighting is off; their choices are retained for the next time it is enabled.
The compact device is 140 Max units wide (one-third of the initial proof-of-concept
layout). It uses Live's dynamic device/control/text colors, native `live.text` buttons,
and a wrapped status area; no duplicated device title or development credits appear
inside the panel.

### Saved preferences

Each successful change saves all four preferences atomically to
`Remote Scripts/ROLI_for_Live/settings.json` in the User Library. This is separate from
`device_snapshot.json`, which captures the keyboard's pre-script lighting for restoration.
The settings file is read when the script starts and is not removed at shutdown.
The Mac installation's Dropbox User Library therefore syncs these preferences. Settings
are global, not per Live Set; they are not re-read live if another computer edits the file.
Avoid simultaneous edits on multiple computers (Dropbox conflict resolution is not handled).
Existing three-preference settings files are read without resetting your choices.
Root color starts on for these files; the next successful change writes the new schema.

Missing settings use the defaults. Invalid/unreadable files use defaults **with an explicit
Live notification and device error status**, and are not silently overwritten on startup.
A failed save leaves the previous preference and previous settings file intact; the device
reports the failure instead of confirming an unsaved choice. Details appear in Live's
`Log.txt`. A later successful button change clears the error.

Removing/bypassing the Max device does not reset preferences. Turn **Scale lighting OFF**
to restore captured keyboard lighting, or disable the control surface entirely.
Playing notes remains independent, including when Scale lighting is off. The keyboard's
own local response to physically played keys may still occur; the switch controls feedback
generated by this integration, not every built-in lighting behavior.
White highlights may be difficult to distinguish when Key colors is White; use Track
colors and a playing MIDI clip to see the difference clearly. Pressing the keys by hand
does not isolate this feedback: the Piano's native touch/pressure lighting continues
regardless of this switch. Root-note coloring has its own Root color control.
The device's MIDI input is wired directly to MIDI output; performance MIDI does not pass
through JavaScript. Per-Set recall and automation are not implemented.

Source: [`m4l/ROLI-Controls.js`](m4l/ROLI-Controls.js), with a generated Max patch/device
from pinned third-party [js2max](https://github.com/ktamas77/js2max). The
[`build script`](m4l/build.mjs) adds compact theme-aware controls and text status, disables
Max parameter recall (preferences live in the Python script), and replaces
the compiler's JavaScript MIDI routing with direct MIDI pass-through. No visual patch
editing is required. Automated mocks/structural checks do **not** establish that the
device loads or that custom control-surface calls work in a real Live session; verify
those in a blank Set before relying on it.

**Proof-of-concept verification (2026-10-16):** the generated device loaded in Live
12.4.15b7 on macOS, and Live's log confirmed calls from Max to the Python script and
outgoing color commands. The user confirmed both schemes work on a ROLI Piano 49 and
root colors follow the selected track. A subsequent repeated-click issue showed the
initial Max toggle could keep sending on; the revised momentary button inverts script
state directly. After reloading the revised device, the user confirmed repeated clicks
switch both on and off correctly.
Performance MIDI wiring is covered by structural
tests; playing feel, reload recovery, and broader compatibility still need real-session
testing.

Persistence, both note-feedback paths, and lighting restoration have automated regression
coverage in `tests/test_settings.py`. The updated three-control device loaded in Live,
its setting changes appeared in Live's log, and the user confirmed preferences survived
quitting and reopening Live (2026-10-16). The user subsequently confirmed the fourth
Root color control and visible clip-playback highlighting on the Piano. The white
playback highlight can be subtle against white base keys.

## Compatibility

| | Status |
|---|---|
| ROLI Piano 49, firmware 1.5.0 | ✅ Tested |
| Ableton Live 12.4.6 Suite, Windows 11 | ✅ Tested |
| Other Live 12 editions (Intro, Standard) | Expected to work, untested |
| macOS with Live 12 | ✅ Tested (user-confirmed) |
| LUMI Keys | 🧪 Experimental, untested: lights only (scale, track color, playing notes); buttons and expression left alone. Select the script manually. |
| Seaboard, other ROLI models | Not supported (the script stays idle) |
| Without ROLI Connect / ROLI Hardware Driver running | Untested |

## Known limits

- Keyboard colors may briefly return to the captured pre-script lighting between Live
  sessions. The script deliberately restores it on shutdown, then waits for keyboard
  initialization before applying the saved preferences on startup.
- Live scales without an exact match among the keyboard's 19 built-in scales (e.g. Phrygian
  Dominant, Hirajoshi, Harmonic Major) light only the root note, and Live shows a message.
- Notes from MIDI effects (Arpeggiator, Chord, …) don't light up; Live doesn't give those notes
  to control-surface scripts. Notes in clips do.
- Live doesn't select the control surface automatically yet; it's the one-time step above.

## How it works

The script talks to the keyboard over its normal USB MIDI port using ROLI's documented BLOCKS
SysEx protocol. It sets the keyboard's built-in key/scale/color display from Live's state, keeps
the keyboard in BLOCKS API mode while Live is open so the `<` / `>` buttons are reported, and
sends note-ons for the notes sounding in the playing clip. Hardware findings and protocol notes
are in [docs/hardware-inventory.md](docs/hardware-inventory.md); the original plan is in
[ROLI_LIVE_IMPLEMENTATION_PLAN.md](ROLI_LIVE_IMPLEMENTATION_PLAN.md).

## Development

Build a release zip with `py -3.11 tools/build_release.py` (output in `dist/`).

```bash
py -3.11 tests/test_script.py
```

runs the script against a fake Live (which enforces Live's listener rules) and a fake keyboard.
Run `python3 tests/test_settings.py` for saved-preference, error-handling, lighting-restoration,
and note-feedback regression tests. These tests use temporary files, not installed preferences.
Live loads Remote Scripts at startup, so restart Live after changing the installed copy.
Script messages and errors appear in Live's `Log.txt`.

## Credits

- BLOCKS protocol details (packet format, config IDs, scale tables) follow
  [WeAreROLI/roli_blocks_basics](https://github.com/WeAreROLI/roli_blocks_basics), ISC licensed (see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).
- ROLI, LUMI and Seaboard are trademarks of ROLI Ltd. Ableton, Live and Push are trademarks of
  Ableton AG. Used here only to describe compatibility.

## License

[MIT](LICENSE) © 2026 Ehsan Sayyad
