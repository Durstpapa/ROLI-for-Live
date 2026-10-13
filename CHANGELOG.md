# Changelog

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
