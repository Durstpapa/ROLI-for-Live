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
| 🎨 **Track colors** | Keys take the selected track's color; the root note glows brighter. |
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
Live loads Remote Scripts at startup, so restart Live after changing the installed copy.
Script messages and errors appear in Live's `Log.txt`.

## Credits

- BLOCKS protocol details (packet format, config IDs, scale tables) follow
  [WeAreROLI/roli_blocks_basics](https://github.com/WeAreROLI/roli_blocks_basics), ISC licensed (see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).
- ROLI, LUMI and Seaboard are trademarks of ROLI Ltd. Ableton, Live and Push are trademarks of
  Ableton AG. Used here only to describe compatibility.

## License

[MIT](LICENSE) © 2026 Ehsan Sayyad
