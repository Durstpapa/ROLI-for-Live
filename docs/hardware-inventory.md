# Hardware & host inventory (G0, read-only part of G2)

Captured 2026-10-10 on the development PC. Read-only: no flash writes, no API-mode
begin/end, no config/program messages, no Live preference changes. Serial number and
MAC are partially redacted below; the full capture lives only on the local machine.

## Host

| Item | Value |
|---|---|
| OS | Windows 11 Pro 10.0.26200, x64 |
| MIDI stack | Windows MIDI Services (MIDI 2.0 service `midisrv`) active; ROLI port is a KS-aggregated endpoint `SWD\MIDISRV\MIDIU_KSA_6573409034431001027` |
| Other MIDI | an audio interface's MIDI ports, Microsoft GS Wavetable Synth |

## Keyboard

| Item | Value | Source |
|---|---|---|
| Windows name | `ROLI Piano` | PnP |
| USB VID / PID | `0x2AF4` / `0x0F00`, `REV_0000` | PnP hardware IDs |
| USB location | Port_#0004.Hub_#0002 | PnP |
| Kernel driver | `roliMIDI` service, "ROLI MIDI Driver" 1.0.14.2 (ROLI Ltd.), **not** class-compliant usbaudio | PnP / uninstall registry |
| MIDI ports (WinMM via python-rtmidi) | in `ROLI Piano 1`, out `ROLI Piano 2` (the numeric suffix is the rtmidi index, not part of the name; don't match on it) | mido 1.3 / python-rtmidi on Python 3.11 |
| BLOCKS serial | `RP4…` (16 chars; rest redacted) → `isRoliPiano49()` in roli_blocks_basics | 0x78 dump + topology |
| Model | **ROLI Piano 49** (by serial prefix; Windows only says "ROLI Piano") | |
| Firmware | **1.5.0** (BLOCKS deviceVersion string `"1.5.0"`; Universal Identity version bytes `01 05 00 00`) | topology reply / identity reply |
| Other strings in 0x78 dump | `RISE1.00` (offset 5) and `1.00` near the end; meaning unknown (probably bootloader/hardware rev); MAC-like `48:B6:20:xx:xx:xx` | 0x78 dump |
| Device name | empty (deviceName msg with a single NUL) | topology reply |
| Battery fields | level 23 / 31, charging=1 (reported despite USB power) | topology reply |

## Vendor software (installed / running at capture time)

| Software | Version | Running? |
|---|---|---|
| ROLI Connect | 1.6.4 | **Yes**, 4 processes, `C:\Program Files\ROLI\ROLI Connect\` |
| ROLI Hardware Driver (process) | n/a | **Yes**, PID 7748 |
| ROLI MIDI Driver (kernel) | 1.0.14.2 | bound to the device |
| ROLI Dashboard | 4.7.2 (x64 and x86 entries) | No |

While Connect and the Hardware Driver were running, a second client opened both ROLI ports
and got replies with no errors. So in this configuration multi-client coexistence works
(G2 transport-contention question: at least not exclusive; ownership/API-mode contention
is still untested).

## Ableton Live

| Item | Value |
|---|---|
| Primary install | Live **12.4.6 Suite** (`C:\ProgramData\Ableton\Live 12 Suite\`), Build 2026-09-10_0de5c8fa9a, Release, 64-bit, `Licensing: [Variant=Suite]` |
| Embedded Python | **3.11** (bundled Remote Script `.pyc` magic 3495 = CPython 3.11) |
| Bundled Remote Scripts | `C:\ProgramData\Ableton\Live 12 Suite\Resources\MIDI Remote Scripts` (149 dirs) |
| Preferences | `%APPDATA%\Ableton\Live 12.4.6\Preferences\` (also contains `User Remote Scripts\` with `UserConfiguration.txt`) |
| User Library | `%USERPROFILE%\Documents\Ableton\User Library` (from `Library.cfg`) |
| User Library Remote Scripts | `...\User Library\Remote Scripts\` exists; contained one unrelated third-party script |
| Current control surfaces (Log.txt) | slot 1 `Push2`, one unrelated third-party script, others None |
| Live MIDI devices in last log | only the audio interface listed; **ROLI Piano had not been seen by Live 12.4.6** in the logged sessions |
| Push driver | Ableton USB Audio Driver 5.72.0 |

### Bundled `BLOCKS` script (relevant to G1)

Live ships `MIDI Remote Scripts\BLOCKS` (compiled only). Its `__init__.get_capabilities()`
declares `controller_id(vendor_id=10996 /*0x2AF4*/, product_ids=[2304 /*0x0900*/],
model_name='Lightpad BLOCK')` and ports with `NOTES_CC` / `SCRIPT` props. `blocks.pyc` uses
SysEx header `F0 00 21 10`. Takeaways:
- Live's own USB VID/PID capability matching exists and is how first-party scripts
  auto-detect. That's the mechanism G1 item 3 asks about. It still needs a fresh-profile test
  for a *User Library* script.
- The bundled script targets Lightpad only (PID 0x0900); it does not claim PID 0x0F00.

## BLOCKS SysEx probe (raw)

Protocol per `WeAreROLI/roli_blocks_basics` @ `212ba4e` (ISC). Only these were sent, on
`ROLI Piano 2`, each followed by a 2 s listen. The whole sequence ran **twice** by accident
(identical replies both times).

| Request | Bytes sent | Reply |
|---|---|---|
| MIDI Universal Identity | `F0 7E 7F 06 01 F7` | `F0 7E 7F 06 02 00 21 10 02 00 06 00 01 05 00 00 F7` → mfr `00 21 10` (ROLI), family `02 00`, member `06 00`, version `01 05 00 00` |
| BLOCKS serial dump (`BlockSerialReader`) | `F0 00 21 10 78 3F F7` | 254-byte `F0 00 21 10 78 3A …` dump, ASCII `RISE1.00`, MAC `48:B6:20:…`, serial `RP4…` (redacted), `1.00` |
| BLOCKS requestTopology, index 0 (msgType 0x01, cmd 0x01, checksum 0x5D) | `F0 00 21 10 77 00 01 01 00 5D F7` | `F0 00 21 10 77 6D 00 00 00 00 10 10 20 00 00 29 28 … 21 2B 00 00 6F F7` (checksum OK) |

Decoded topology reply (dev→host, index byte `0x6D` → **topology index 45**):
`deviceTopology` protoVer 1, 1 device, 0 connections; device serial `RP4…`, index 45;
then `deviceVersion` idx 45 `"1.5.0"`; then `deviceName` idx 45 empty.

**Unsolicited traffic:** the device sends `F0 00 21 10 77 6D 00 00 00 00 20 00 00 6D F7`
at exactly 1.000 s intervals = `packetACK` (msgType 0x02) with counter 0 from index 45.
That's almost certainly the device ACKing ROLI Connect's pings, i.e. **the keyboard is
already in BLOCKS API mode, held by ROLI Connect**. The timestamp field was 0 in every packet.

## Incoming performance MIDI

Passive 120 s capture on `ROLI Piano 1` (nothing sent) while the owner played freely,
with ROLI Connect still running. No pedal was connected and the octave/transpose buttons
were not exercised. 598 messages after dropping the 1 Hz heartbeat:

| Observation | Value |
|---|---|
| Message types | `note_on`, `note_off`, SysEx only. **No pitch bend, channel pressure, poly aftertouch or CC (incl. CC74) at all.** |
| Channels | Notes rotate across **MIDI ch 2–16** (15 member channels). Ch 1 never used → MPE-style lower-zone channel-per-note layout, but with no per-note expression data. |
| Notes | 109 notes, range 41–81, max 6-note polyphony. Velocity 1–126 (many at 1 = softest). |
| Note off | Real `note_off` (never note_on vel 0) with **release velocity** (mostly 1, some 11–22). |
| BLOCKS touch stream (SysEx, index 45) | For every key: `touchStartWithVelocity` (0x13) at the same instant as note_on, `touchMove` (0x11) every **~128 ms** while held, `touchEndWithVelocity` (0x15) at note_off. 539 touch messages total. |
| Touch fields | x = key position on a 0–4095 axis: x ≈ (note − 36 + 0.5) × 4096/49 (e.g. note 41 → 459, 48 → 1044), i.e. 49 keys with the current lowest key = MIDI 36. y always 2048, z (pressure) 0 while held / 127 in end messages. The velocity-z byte in touchStart equals the MIDI note-on velocity. |
| Topology | An unsolicited topology packet arrives every **~30.1 s** (presumably ROLI Connect polling). |

### "<" / ">" button test (ROLI Connect quit, ROLI Hardware Driver still running)

Owner pressed: leftmost white key ×3, ">" ×1, key ×3, "<" ×2, key ×3, ">" ×1, key ×3.

| Event | Observed |
|---|---|
| Leftmost white key, all four times | **always note 36**, touch x = 41. The note numbers never moved. |
| ">" | BLOCKS `controlButtonDown/Up` (0x20/0x21), **button ID 4**; 1st press: no MIDI, 2nd press: `program_change 126` on MIDI ch 1 |
| "<" | BLOCKS `controlButtonDown/Up`, **button ID 3**; `program_change 126`, then `125`, on MIDI ch 1 |

So in this state, "<" / ">" act as **program down/up on ch 1** (starting from program 127,
which is why the first ">" sent nothing: it was clamped), not octave shift. They're also
reported as BLOCKS control buttons 3/4. How to change octave on this unit (another mode, a
shift combo, or only with no API host attached) is still open.

With Connect quit, the 1 Hz packetACK and the ~30 s topology packet **continue**. The
`ROLI Hardware Driver` process (PID 7748), not ROLI Connect, is what holds the device in API mode.

### "+" / "−" button test, and held-key pressure/bend attempt

| Event | Observed |
|---|---|
| "+" | BLOCKS button **ID 2** + config `setConfig` item 4 (`octave`) → 0. Leftmost key went 36 → **48**. |
| "−" ×2 | BLOCKS button **ID 1** ×2, octave → −1, −2. Leftmost key → **24**. |
| "+" | back to octave −1, key → **36**. |
| Touch x during all of this | always **41**: physical position is independent of octave. |
| One key held ~6 s, pressed harder, wiggled | note 52 on/off only. **No poly aftertouch, channel pressure, pitch bend or CC74.** Touch y stayed 2048, z stayed 0 throughout. |

So "+"/"−" are the octave buttons (default octave = −1 → leftmost key = MIDI 36), and each
press is also announced as a config change (item 4) over BLOCKS. "<"/">" (buttons 3/4) are
program down/up.

### Config read (read-only `requestConfig`, cmd 0x01, per item, device index 0)

`requestUserSync` (cmd 0x03) got no reply; per-item `requestConfig` answered all 50 items
with `updateConfig` (value/min/max). Expression-relevant values:

| Item | Value [range] |
|---|---|
| midiUseMPE (2) | **1** [0..2] |
| midiStartChannel / EndChannel / ChannelRange (0/1/9) | 1 / 16 / 15 |
| MPEZone (40) | 0 [0..1] |
| pitchBendRange (3) | **48** [0..96] |
| keyPitchBendAmount (41) | 1 [1..12] |
| octave / transpose (4/5) | −1 / 0 |
| slideCC / slideMode / slideSensitivity (6/7/12) | 74 / 2 / 127 |
| glideSensitivity (11) | 100 |
| pressureSensitivity (13) | **64** |
| liftSensitivity (14) | 64 |
| pressMin/Max (52/53) | 0 / 127 |
| velocitySensitivity / velocityMin/Max (10/50/51) | 110 / 1 / 127 |
| x/y/zTrackingMode (30/31/32) | 1 / 1 / 1 |
| pianoMode (17), mode (20), fixedVelocity (15) | 0 / 0 / 0 |
| midiPortForwarding (56), midiPortThrottling (57) | 1 / 0 |
| pedalCC (47) | 64 |
| brightness (36), scale (22), key (27) | 100 / 0 / 0 |

**Open question:** config says MPE on (48-semitone bend range), pressure and glide enabled,
yet the keyboard emits no bend or pressure and the BLOCKS touch stream reports z=0 / constant
y. Candidates: the API-mode host (ROLI Hardware Driver) suppresses expression output; the
press/bend gesture needs more force than was used; or this firmware/model doesn't implement
it.

### No ROLI software running (Connect quit, `ROLI Hardware Driver` service stopped by owner)

The `ROLI Hardware Driver` is a Windows **service** (LocalSystem, Auto start, `srvstart.exe`
wrapper in `C:\Program Files\ROLI\ROLI Hardware Driver\`). A normal user can't stop it
(Access denied); the owner stopped it via services.msc. Once stopped:
- The 1 Hz packetACK, the 30 s topology packets and all BLOCKS touch SysEx **stopped**
  (0 messages in a 4 s idle check), so the device left API mode and the MIDI port stayed usable.
- Owner held 4 keys, pressed hard and wiggled: **5 notes, note on/off only, still no
  pitch bend, pressure, poly aftertouch or CC.** Channels 2, 3, 9, 13 (MPE rotation
  continues). Release velocities 1–127.

**Conclusion:** neither ROLI Connect nor the Hardware Driver suppresses expression. With
settings that report MPE on, pressure 64 and bend range 48, this unit/firmware 1.5.0 still
emits velocity + release velocity only, for the gestures tried. Still unexplained. Next
candidates: a specific physical technique, a feature gated by ROLI Connect (or a firmware
update), or the published per-key bend/aftertouch claims don't match this unit. Check in
ROLI Connect's own UI whether it shows pressure/bend activity.

### Resolution: expression appears after ROLI Studio Player is used

The owner restarted the service and Connect, then opened **ROLI Studio Player** (WinMM client,
`C:\Program Files\ROLI\ROLI Studio Player\`) and heard pressure and bend working. Captured
on the same `ROLI Piano 1` port, in parallel:

| Phase | Notes | Pitch bend | Channel pressure |
|---|---|---|---|
| Studio Player open, deliberate press/bend | 4 (ch 6–9) | 443 msgs, range −171..+151 | 428 msgs, 0..127 |
| Studio Player open, free playing (~7 min) | ~1,640 | thousands | thousands |
| **After Studio Player closed** | 3 | 385 | 208 |
| **After USB unplug/replug, Studio Player not opened** | 4 (ch 9, 10, 13) | 441, −171..+170 | 224, 0..127 |

Expression format: **MIDI 1.0 MPE, lower zone, member channels 2–16**:
- per-note **pitch bend** on the note's channel; ±171 of ±8192 = **±1 semitone** at the
  reported 48-semitone range (`keyPitchBendAmount` = 1);
- per-note **channel pressure** (aftertouch, `0xD_`), 0..127;
- no CC74/slide, no poly aftertouch.

Config diff, before Studio Player vs. after: **`midiStartChannel` 1 → 2** (and `octave` −1 → 0
from a "+" press). Everything else was identical, including `midiUseMPE` = 1. After the replug,
`midiStartChannel` was still 2 and `octave` still 0, so the state persists across power
cycles. It's either stored on the device, or ROLI Connect (running during the replug)
re-applies it on connect; not yet separated.

**Working theory (unproven):** with `midiStartChannel` = 1 the firmware rotates notes over
ch 2–16 but suppresses per-note expression. Setting the lower-zone layout, either through
`midiStartChannel` = 2 via BLOCKS config or through a standard MPE Configuration Message
(RPN 6 on ch 1) that Studio Player may send, enables bend/pressure. Studio Player's
outgoing messages were not captured.

**Impact on the plan:** expression on this unit depends on device state that some host
software sets. A fresh/unconfigured keyboard may send no bend/pressure to Live. That falls
under the spec's §5.4 "MPE setup" consent step: the integration must detect
`midiStartChannel`/zone state (read-only `requestConfig` item 0 works) and offer a one-time,
consented fix with a saved before-state. Earlier sections of this doc that say "no
continuous per-note expression" describe the pre-Studio-Player state only.

Implications: this firmware/configuration gives **no continuous per-note expression**,
only strike and release velocity, so "MPE" here is channel-per-note routing only. The BLOCKS
touch stream already gives a key→position mapping that doesn't depend on MIDI channel/octave,
and it's emitted only because the device is in API mode (held by ROLI Connect). Still
**NOT RUN**: octave/transpose buttons (does the note offset change while touch x stays
fixed?), sustain pedal, and whether the MIDI channel layout changes when Connect isn't running.

## Lighting (G3), in progress

Stock lighting settings (snapshot, read-only): `key` 0 (C), `scale` 0, `mode0_showScale` 1,
`mode0_colorType` 0 ("Pro"), `brightness` 100, `globalKeyColour` −1002466 (0xFFF0B41E),
`rootKeyColour` −3623796 (0xFFC8B38C). Per-mode expression switches (items 100–125):
mode 0 = MPE, pitchEnable 1, pressureEnable 1 (probably what Studio Player turned on;
their earlier values weren't read).

Baseline as seen by the owner: **every C red**, other white keys lit white, black keys
dimly lit; a pressed key lights brighter (white for black keys). The red/white colours don't
match the stored global/root colour values, so the "Pro" scheme presumably overrides them.

Test 1: `setConfig key = 2` (D) at 00:28 UTC, read back = 2. The owner didn't observe the
keys while it was set. It was restored to C (all snapshot items written back and verified)
at 00:43 after an unrelated PC-keyboard issue (Windows reported Left Ctrl stuck down; it
cleared after a synthetic Ctrl key-up). **Result: not yet observed.**

Test 2 (00:50 UTC): `mode0_colorType` = 1 (User), `globalKeyColour` = 0xFF0000FF (blue),
`rootKeyColour` = 0xFF00FF00 (green), `scale` = 0 (Major), `key` = 2 (D), `showScale` = 1;
all read back OK. Owner's report: **D green; C♯, E, F♯, G, A, B blue; C, F, G♯, A♯ dark**.
That's D major exactly with the root in the root colour, plus D♯ reported blue (possibly
light bleed from the adjacent D; recheck). **The stock config path works:** root, scale
filtering and arbitrary RGB scale/root colours via `colorType` = User, with no Littlefoot
program needed. Restored to the snapshot afterwards (verified).

## Spec claims vs. observation

| Spec (ROLI_LIVE_IMPLEMENTATION_PLAN.md) | Observation |
|---|---|
| Primary target "Piano 49" | Consistent: serial prefix `RP4` = `isRoliPiano49`. Windows/USB only say "ROLI Piano", so model identity must come from SysEx, not the port name. |
| "Discover current topology address; never hard-code the byte" | Confirmed important: the device reports index **45**, not 0. A request addressed to index 0 was still answered. |
| Python 3 Remote Scripts | Confirmed: Live 12.4.6 embeds Python 3.11. |
| Capability discovery "commonly exposed by `get_capabilities`" | Confirmed for bundled scripts (BLOCKS uses VID/PID). User Library auto-activation is still unproven. |
| Test with vendor apps not running (G2) | Currently ROLI Connect + Hardware Driver run at login and appear to hold API mode. Coexistence for reads works; the effect on lighting/API ownership is still untested. |
| Target Standard/Suite, "beta not required" | This PC has Suite 12.4.6. No Standard install to test. |
| Native expression: "MPE, pressure, pitch bend" preserved (R07, A10) | Supported, but **state-dependent**: per-note pitch bend (±1 semitone at range 48) and channel pressure on ch 2–16, no CC74. Absent until a host (ROLI Studio Player) changed `midiStartChannel` 1 → 2; persists across replug afterwards. §5.4 MPE onboarding is a real requirement, not hypothetical. |
| USB driver | The spec doesn't mention it: a vendor kernel driver (`roliMIDI` 1.0.14.2) is bound, not the Windows class driver. Behaviour on a machine without ROLI's driver is untested. |

## Reproduce

```bash
py -3.11 -m pip install --user mido python-rtmidi   # rtmidi failed to build on 3.13
```
The probe and decoder scripts used are not committed (kept in the session scratchpad); the
request bytes above are complete.
