<p align="center">
  <img src="docs/logo.svg" alt="ROLI for Live" width="420">
</p>

<p align="center">
  <b>Your ROLI Piano, lit up by Ableton Live.</b><br>
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

**ROLI for Live — ROLI Piano integration** is a small MIDI Remote Script that runs inside
Ableton Live and turns a ROLI Piano keyboard into a Push-style partner for Live.
No extra app, no driver, no Max for Live, and
nothing to add to your Live Sets for the core integration. The optional **ROLI Controls**
device uses Max for Live to adjust and save the lighting preferences.

**Hardware scope:** tested on **ROLI Piano 49**, not a general integration for all ROLI
controllers. **Piano M (formerly LUMI Keys)** also has a lighting profile, now
user-confirmed on a LUMI Keys unit. **Lightpad and Seaboard are not supported by this
integration.** See the [compatibility matrix](#compatibility).

> Independent community project. Not affiliated with or endorsed by ROLI or Ableton.

## Features

| | |
|---|---|
| 🎼 **Scale guide** | The keys show Live's current root note and scale, or optionally the selected track's playing MIDI clip scale on compatible Live versions. |
| 🎨 **Track colors** | White keys with roots in the selected track's color by default; optional live controls switch to track-colored keys with brighter roots. |
| ✨ **Playing notes** | Keys light white as the selected track's clip plays (Session and Arrangement). |
| ⏮️⏭️ **Track buttons** | The keyboard's `<` / `>` buttons select the previous/next track. |
| 🎹 **Native MPE** | Per-note pitch bend and pressure go straight into Live; the script never touches your notes. If the keyboard's bend/pressure are switched off, it turns them on. |
| ↩️ **Native lighting handoff** | Requests restoration of captured lighting settings when Live closes, then releases API mode on Piano 49. Automatic native-lighting return is user-confirmed on Piano 49. |

### What this fork adds

The optional **ROLI Controls** device has five buttons, in this order: **Scale lighting,
Key colors, Root color, Playing notes, Clip scale**, plus **Global Brightness** and
**Background Brightness** sliders alongside them. Settings survive Live restarts, even
when the controls device is not loaded. The device shows connection/source status and
reconnects automatically when the keyboard becomes available.

- [Controls and installation](#optional-live-controls-experimental): every button, slider and default.
- [Following a playing clip](#following-a-playing-clip): use clip scales without changing selection.
- [Balancing brightness](#balancing-brightness): dim the background and adjust playback-highlight contrast.
- [Connection status](#connection-status), [saved preferences](#saved-preferences) and
  [troubleshooting](#troubleshooting): what to expect and how to recover.
- [Compatibility](#compatibility) and [known limits](#known-limits): supported hosts and deliberate boundaries.
- [Changelog](CHANGELOG.md): implementation history and hardware-test results.

**Install from this fork's source for these features.** The upstream release downloads
and download command below do not include this fork's controls. Follow the manual script
installation and the [controls build/install steps](#optional-live-controls-experimental).

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

The code-first **ROLI Controls** Max for Live Audio Effect provides five buttons and two sliders.
It passes stereo audio straight through without processing, and can sit on the Master/Main
track inside an Audio Effect Rack with your other default devices. Its controls operate
globally; scale and playing-note lighting still follow the selected MIDI track, not the
track holding the device.

The controls are:

| Control | Behavior |
|---|---|
| **Scale lighting: ON / OFF** | On follows the chosen scale source and selected track colors. Off restores captured native key colors and scale settings, not a factory reset. Saved global brightness, track navigation and MPE stay active. |
| **Key colors: White / Track** | White keys with track-colored roots, or track-colored keys with brighter roots. Used only when Scale lighting is on. |
| **Root color: ON / OFF** | Off removes the special root color: root keys match the other lit keys in White and Track modes. It does not make them dark or disable those notes. Used only when Scale lighting is on. |
| **Playing notes: ON / OFF** | Independently enables/disables temporary white highlights for sounding clip notes and Live's note feedback. It does not switch root-note coloring off. Turning it off clears feedback notes; normal performance MIDI is unaffected. |
| **Clip scale: ON / OFF** | On follows the playing MIDI clip on the selected track, without selecting it or changing Live's global scale. Off follows Live's global scale as before. Used only when Scale lighting is on. |
| **Global Brightness (%): 0-100** | Native global LED brightness, including playback highlights. Initially reads the keyboard's current value without changing it. Once adjusted, saves and reapplies your choice, including with Scale lighting off. Zero turns the LEDs off, not performance MIDI. |
| **Background Brightness (%): 0-100** | Scales background and root RGB channels relative to native playback highlights. Requires Scale lighting on; 25 gives the hardware-tested dim background. Zero removes background colors but does not disable notes. This is not calibrated perceptual brightness. |

Without saved preferences, the defaults are **White**, **Scale lighting ON**,
**Clip scale OFF**, **Playing notes ON**, **Root color ON**, and **Background 100%**,
with **no global brightness override**, including when no Max device is loaded. The keyboard's active
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
   `dist/m4l/ROLI Controls.amxd` onto the Master/Main track, an audio track, or a MIDI
   track after its instrument. It can be grouped with other audio effects in an Audio
   Effect Rack. Save the rack in your default Live Set to load it with new projects.
4. Wait for **Connected**, then use the buttons and sliders. No script reinstall or Live restart
   is needed for subsequent changes.

If upgrading from the MIDI Effect version, remove that instance and load the newly built
Audio Effect instead; existing Sets and saved racks retain their embedded older device.
Your saved lighting preferences remain unchanged.

### Following a playing clip

1. Select the MIDI track you want the keyboard to follow.
2. Turn **Scale lighting ON** and **Clip scale ON**.
3. Start playback through an Arrangement clip, or launch a Session clip on that track.
   Each clip must have its intended root, scale and Scale mode assigned in Live.
4. To compare selection-independent behavior, keep the track selected and select another
   clip on that same track without launching it. Lighting follows the playing clip,
   not the selected clip. Selecting another track changes which track is followed.

Empty Arrangement clips work too: they can provide scale guidance without containing
notes. Playing notes can be OFF and clip-scale following still works.

Clip-scale following requires clip-level scale properties, introduced in
[Live 12.4.15b1](https://www.ableton.com/en/release-notes/live-12-beta/).
It reads the playing clip's root, scale mode, intervals and scale name together. Session
clips take precedence over Arrangement clips on the selected track; Arrangement following
uses the running transport and clip timeline bounds, not the clip's own `is_playing` flag,
so empty clips can guide the scale too. It respects muted clips and Session stop/override states. Playback handoffs
and edits to a playing clip's scale are checked on the script's display updates (roughly
10 Hz), independently of Playing notes. This follows the clip's assigned scale, not chord
changes inferred from its MIDI notes. Existing keyboard built-in scale limitations remain.

The status shows **Playing clip scale** while following a clip and **Live scale (no clip)**
when stopped, in an Arrangement gap, or on a track with no applicable playing MIDI clip.
If the host does not expose the clip-scale properties, or a read fails, the script uses
Live's scale with an explicit **Clip scale unavailable** or **Clip scale read error** status
and a diagnostic in Live's log. It retries automatically without discarding the saved
Clip scale choice. No transport, clip selection, clip metadata or global scale is written.
The user confirmed empty adjacent D-minor and C-major Arrangement clips change the
Piano's lighting during playback on Live 12.4.15b7 (2026-10-16), after the Arrangement
playback-flag correction and a Live restart. Other paths have automated simulated-host
coverage; Session clip-scale following has not yet been separately hardware-qualified.

### Balancing brightness

Double-click **Global Brightness** to reset it to **100%**, or **Background Brightness**
to reset it to **25%**. These are explicit user actions and save the chosen reset value.
Loading the device does not apply these reset values or replace your saved preferences.
The fresh-install background default remains 100%.

1. Turn **Scale lighting ON** and **Playing notes ON**, then play a MIDI clip with notes.
2. Try **Background Brightness 25%** as a starting point. This dims background and root
   colors without requesting a lower playback-highlight velocity.
3. Lower **Global Brightness** until the white playback highlights feel comfortable.
   This dims all keyboard lighting, including the background and native touch lighting.
4. Adjust **Background Brightness** again to balance the other keys against the highlights.
   Root color and White/Track palettes keep working at the chosen background level.

These are not two independent per-key brightness controls: Global affects everything,
and Background changes the base/root RGB colors beneath native feedback. An independent
playback-highlight brightness control is not exposed; reducing feedback velocity did
not visibly dim highlights on the tested Piano. Neither slider changes the velocity of
notes played or recorded.

Setting Global to 0 makes the LEDs dark. Setting Background to 0 removes the script's
background/root colors while playback highlights may still appear. Neither disables the
keyboard's notes. Raise the sliders to bring the lighting back.

### Connection status

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
The device is 240 Max units wide, keeping the original button stack unchanged and adding
two horizontal `live.slider` controls beside it. It uses Live's dynamic device/control/text
colors and a wrapped status area; no duplicated device title or development credits appear
inside the panel. Slider changes are coalesced every 100 ms, confirmed through Python,
and rediscovered on each write. Polling uses `set` messages that do not emit slider output.
Sliders stay disabled until the keyboard is initialized; Background also requires Scale
lighting on. Loading a device does not apply its local startup/default slider values.
The native slider parameter engine stays enabled to preserve its 0-100 range, with
Hidden parameter visibility and initialization disabled to prevent Set/preset recall.
Startup checks both endpoints directly on the native widgets with non-outputting `set`
messages before enabling controls; a collapsed range displays an error and blocks writes.

### Saved preferences

Each successful change saves all seven preferences atomically to
`Remote Scripts/ROLI_for_Live/settings.json` in the User Library. This is separate from
`device_snapshot.json`, which captures the keyboard's pre-script lighting for restoration.
The settings file is read when the script starts and is not removed at shutdown.
The Mac installation's Dropbox User Library therefore syncs these preferences. Settings
are global, not per Live Set; they are not re-read live if another computer edits the file.
Avoid simultaneous edits on multiple computers (Dropbox conflict resolution is not handled).
Existing schemas 1-3 are read without resetting your choices. Root color starts on when
absent, Clip scale starts off, Background starts at 100%, and global brightness is left
alone until explicitly changed. If upgrading the temporary 25% background test, select
Background 25% to retain that appearance; the local test installation has been migrated
with that value. The next successful change writes schema version 4. Older control devices
can still use existing bridge methods; the slider device requires the updated v5 bridge.
Native brightness is captured before any override and restored at script shutdown.
Recovery snapshots from earlier versions retain their original colors while adding the
currently observed hardware brightness.

Missing settings use the defaults. Invalid/unreadable files use defaults **with an explicit
Live notification and device error status**, and are not silently overwritten on startup.
A failed save leaves the previous preference and previous settings file intact; the device
reports the failure instead of confirming an unsaved choice. Details appear in Live's
`Log.txt`. A later successful button change clears the error.

Removing/bypassing the Max device does not reset preferences. Turn **Scale lighting OFF**
to restore captured key colors and scale settings while retaining your global brightness,
or disable the control surface entirely to also restore captured native brightness.
Playing notes remains independent, including when Scale lighting is off. The keyboard's
own local response to physically played keys may still occur; the switch controls feedback
generated by this integration, not every built-in lighting behavior.
White highlights may be difficult to distinguish when Key colors is White; use Track
colors and a playing MIDI clip to see the difference clearly. Pressing the keys by hand
does not isolate this feedback: the Piano's native touch/pressure lighting continues
regardless of this switch. Root-note coloring has its own Root color control.
The Audio Effect passes stereo audio directly through; performance MIDI stays on the
keyboard's normal Live input routing. Per-Set recall and automation are not implemented.

**Background contrast hardware result:** The user confirmed 25% background RGB provides
useful contrast with native playback highlights at feedback velocity 127 on Piano 49 /
Live 12.4.15b7 (2026-10-16). This is now the Background slider, rather than an installed
source-code test constant. Native touch/pressure lighting is separate. No custom keyboard
program is involved. After enabling the native slider parameter engines and retaining
Hidden visibility, the user confirmed both brightness sliders work on Piano 49 /
Live 12.4.15b7 (2026-10-16). Slider restoration and migration paths also have automated
coverage; they have not all been separately hardware-qualified.

**Playback-highlight experiment:** A temporary test installation can also set
`PLAYING_NOTES_FEEDBACK_VELOCITY` to `64` instead of the normal `127`. The same value
then controls both Live's feedback velocity and the script's clip-note lighting messages.
Performance input and recorded note velocities are unaffected. This value is a MIDI
velocity, not a calibrated brightness percentage. On Piano 49 / Live 12.4.15b7, the
startup log confirmed velocity 64 was loaded in both paths, but the user reported no
perceptible highlight-brightness change (2026-10-16). Restore 127; this result does not
justify exposing an independent playback-brightness slider. A full Live restart is
needed to change test constants.

Source: [`m4l/ROLI-Controls.js`](m4l/ROLI-Controls.js), with a generated Max patch/device
from pinned third-party [js2max](https://github.com/ktamas77/js2max). The
[`build script`](m4l/build.mjs) adds compact theme-aware controls and text status, disables
Max parameter recall (preferences live in the Python script), and wires
direct stereo audio pass-through outside JavaScript. No visual patch
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
playback highlight can be subtle against full-intensity white base keys; lower Background
Brightness to improve the contrast.

### Troubleshooting

**Shutdown lighting:** A user reported that script colors could remain after quitting
Live until switching native hardware modes (2026-10-17). Shutdown now stops lighting
updates and note feedback before sending the captured lighting settings, then explicitly
ends BLOCKS API mode on Piano 49. LUMI/Piano M does not enter API mode and receives only
the restoration writes. No native mode switch is forced and saved lighting preferences
are unchanged. Logs describe requests, not verified hardware restoration; rejected
restore sends retain the recovery snapshot. The user confirmed native lighting returns
automatically on Piano 49 / Live 12.4.15b7 after quitting with Scale lighting left ON
(2026-10-17); turning it off manually before quitting is not required on that tested
setup. LUMI/Piano M shutdown restoration and crash/power-loss recovery are not covered
by that confirmation. This change cannot reconstruct native settings already altered;
restore those in Dashboard with Live closed.

| What you see | What to check |
|---|---|
| **Disconnected** | Check keyboard power, USB/MIDI connection and the ROLI control-surface input/output in Live. Wait for initialization. The device keeps polling; it does not assume which connection component failed. |
| **Live scale (no clip)** | For clip following, keep the intended MIDI track selected and transport running inside an unmuted Arrangement clip, or launch its Session clip. Stopped playback, timeline gaps and Session overrides can legitimately leave no applicable clip. |
| **Clip scale unavailable / read error** | The script is explicitly using Live's scale instead. Check host support (clip-scale properties were added in 12.4.15b1) and Live's log. |
| Keys are dark | Raise Global Brightness, then Background Brightness if Scale lighting is on. A saved 0% is valid and survives restarting Live. |
| Playing notes seems unchanged when pressing keys | Test a playing MIDI clip, not just physical key presses. Native touch/pressure lighting is separate. Lower Background Brightness if white playback highlights blend into the base keys. |
| Sliders are stuck at zero or a **Slider range error** appears | Load the current generated device. An earlier build disabled the native slider parameter engines, collapsing their range. The corrected device validates native 0/100 readback before allowing writes. If drag attempts saved zeros, raise Global and Background to the desired levels after updating. |
| **Settings file error / settings were not saved** | Check write access to the script's settings file and Live's log. Runtime preferences are not changed when saving fails. |
| Old labels/layout or an **Update ROLI script** message | Install matching script and device versions. Python changes require a full Live quit/restart. Device-only changes require reloading the device if Live has not refreshed it automatically. |

No restart is needed to change a control value. Removing or bypassing the controls device
does not reset the saved choices. Scale lighting OFF restores native key colors but
retains any saved global brightness override; disabling the control surface also restores
captured native brightness.

### Temporary custom-lighting experiment

Selectable green playback highlights are **not implemented in the installed device**.
The isolated [lighting experiment](experiments/lighting/) first tests restoration of
the Piano's saved default program, before trying custom colors. It does not modify the
installed Remote Script, Max device, or Dropbox preferences.

Build and test offline (CMake 3.22+, Ninja, C++17 compiler, internet access):

```sh
cmake -S experiments/lighting -B dist/lighting-probe -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build dist/lighting-probe --parallel 2
ctest --test-dir dist/lighting-probe --output-on-failure
```

Dependencies are pinned official ROLI BLOCKS SDK (ISC) and JUCE 7.0.12
([GPLv3/commercial licensing](https://github.com/juce-framework/JUCE/tree/7.0.12)).
The local executable is a development tool, not part of releases.
The real Littlefoot compiler/VM tests check native touch remains enabled, only the
intended green pixel is painted, and painting stops at the three-second watchdog.
They cannot establish actual Piano firmware behavior.

**Hardware testing requires explicit approval and Live closed.** The tool refuses
to run with Live open. Use an exact Piano 49 serial; the snapshot path must be new
and outside the repository. Close other ROLI-control apps to avoid competing owners.

```sh
dist/lighting-probe/roli_lighting_probe --test-restore RP4_SERIAL /absolute/path/to/snapshot.json
```

This reads and saves configuration before upload, loads a **temporary native-handler
program**, waits five seconds after upload acknowledgment, requests the saved default
program, and compares configuration readback. It never saves a program as default,
performs a factory reset, or sends performance notes. On errors or interruption it
attempts to restore the default; delivery cannot be guaranteed after a disconnect/crash.
A separate recovery command uploads nothing:

```sh
dist/lighting-probe/roli_lighting_probe --restore-default RP4_SERIAL
```

Readback alone cannot prove recovery. Confirm normal lighting, octave controls, notes,
bend/pressure and navigation after reopening Live before proceeding. The green-pulse
program is offline-only until this recovery path is hardware-verified. Recovery is
documented by the SDK but not yet established on this Piano; do not promise a guaranteed
rollback or treat a factory reset as routine recovery.

**Hardware attempt (2026-10-16): blocked before upload.** SDK discovery found the Piano
with the ROLI Hardware Driver temporarily paused, but factory configuration sync ended
without any item values. The safety gate refused upload; no temporary or green program
was sent. A saved-default restore command was sent as a precaution, but an empty sync
cannot verify its effect. The driver service was restarted. Reliable explicit
configuration reads are needed before continuing; do not bypass the snapshot gate.
After reopening Live, the user confirmed the existing setup still behaved normally.
This confirms the baseline, not rollback from a custom program (none was uploaded).

## Compatibility

| | Status |
|---|---|
| ROLI Piano 49, firmware 1.5.0 | ✅ Tested |
| ROLI Piano M (formerly LUMI Keys) | ✅ User-confirmed on a LUMI Keys unit with macOS / Live 12.4.15b7 (2026-10-17). Uses the existing lighting profile; buttons and expression configuration left alone. Select the script manually. |
| Ableton Live 12.4.6 Suite, Windows 11 | ✅ Original core integration tested; not evidence for the newer fork controls or clip-scale API. |
| Ableton Live 12.4.15b7, macOS, Piano 49 | ✅ Fork controls, persistence, disconnection detection, empty Arrangement clip-scale transitions and both brightness sliders user-confirmed. |
| Other Live 12 editions (Intro, Standard) | Core integration expected to work, untested. Optional controls require an edition with Max for Live support. |
| macOS with Live 12 | ✅ Tested (user-confirmed) |
| Lightpad, Seaboard, other ROLI models | Not supported (unrecognized device identities leave the script idle) |
| Without ROLI Connect / ROLI Hardware Driver running | Untested |

The LUMI Keys test used the existing `LKB` profile (still labeled experimental in
runtime diagnostics). The user reported that everything worked; Live's log confirms
recognition and accepted brightness adjustments. The user also confirmed correct
connection-status detection when powering the LUMI off and on. Lighting/state restoration
after reconnect, script-shutdown restoration and recovery scenarios were not separately
qualified on this unit.
Its firmware was not recorded, and a newer Piano M-branded unit was not separately tested.

### Using a Lightpad alongside the Piano

The script controls the Piano's key lighting and navigation; it does not configure
Lightpad pads, lighting, pitch bend or modulation mappings. Keep the control surface's
input/output assigned to the Piano, not the Lightpad. Configure the Lightpad separately
through Live's normal MIDI routing and the Lightpad's own configuration for your preferred
bend/modulation workflow. That combined setup is not yet hardware-qualified here.

The repository, installed script (`ROLI_for_Live`) and optional device (`ROLI Controls`)
retain their existing names for installation compatibility. Those names do not imply
support for every ROLI controller.

## Known limits

- Clip-scale following reads each clip's assigned scale, not chord changes within the
  clip. It follows only the selected track; it does not combine scales from multiple tracks.
- Clip-scale API support requires a compatible host (introduced in Live 12.4.15b1).
  Older hosts can still follow Live's scale; missing clip metadata produces an explicit
  fallback message when Clip scale is enabled.
- Preferences are global, not recalled or automated per Live Set. Device-only changes may
  refresh automatically, but Python script updates still require a full Live restart.
- Playback highlights use the Piano's native white feedback. Independent highlight color
  and brightness controls are not available through the current integration. The custom
  green-lighting experiment is deferred and was blocked before any upload.
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
Run the full Python regression suite and the Max device checks with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
npm run test:m4l
```

These cover saved preferences, error handling, clip scales, lighting restoration,
brightness, feedback, UI acknowledgements and generated-device structure. Tests use
temporary files, not installed preferences. Mock/structural success does not replace
hardware testing: the native-slider range issue was found only in Live, and native
endpoint readback now guards that path at runtime.
Live loads Remote Scripts at startup, so restart Live after changing the installed copy.
Script messages and errors appear in Live's `Log.txt`.

## Credits

- BLOCKS protocol details (packet format, config IDs, scale tables) follow
  [WeAreROLI/roli_blocks_basics](https://github.com/WeAreROLI/roli_blocks_basics), ISC licensed (see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).
- ROLI, LUMI and Seaboard are trademarks of ROLI Ltd. Ableton, Live and Push are trademarks of
  Ableton AG. Used here only to describe compatibility.

## License

[MIT](LICENSE) © 2026 Ehsan Sayyad
