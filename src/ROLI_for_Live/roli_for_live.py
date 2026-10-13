"""ROLI for Live: makes a ROLI keyboard follow Live's scale and selected track color.

Performance MIDI (notes, per-note pitch bend, pressure) is never touched by this script;
it reaches tracks through Live's normal MIDI input. The script only talks BLOCKS SysEx.
"""
from __future__ import absolute_import, print_function, unicode_literals

import json
import os

from _Framework.ControlSurface import ControlSurface

from . import blocks
from .playing_notes import PlayingNotes
from .scales import BUILTIN_SCALES, CHROMATIC, builtin_index

# BLOCKS config item ids (roli_BlockConfigId.h)
MODE = 20
SCALE = 22
KEY = 27
GLOBAL_KEY_COLOUR = 34
ROOT_KEY_COLOUR = 35
# Per-mode items: mode N uses 100 + 7 * N + offset (modes 0-3).
NUM_MODES = 4
_COLOR_TYPE, _MIDI_MODE, _PITCH_ENABLE, _PRESSURE_ENABLE, _SHOW_SCALE = range(5)


def mode_item(mode, offset):
    return 100 + 7 * mode + offset


COLOR_TYPE_USER = 1
SHARED_LIGHTING_ITEMS = (SCALE, KEY, GLOBAL_KEY_COLOUR, ROOT_KEY_COLOUR)

BUTTON_PREVIOUS = 3  # "<"
BUTTON_NEXT = 4      # ">"

# Live echoes the selected track's playing notes to the keyboard on this channel (MIDI ch 1).
# The keyboard lights a key white for each note it receives; it never sends notes on ch 1
# itself (MPE member channels are 2-16), so the echo can't be mistaken for playing.
PLAYING_NOTES_FEEDBACK_CHANNELS = (0,)
PLAYING_NOTES_FEEDBACK_VELOCITY = 127

# Supported keyboards by serial prefix (roli_BlocksProtocolDefinitions.h). Anything else stays idle.
#   api_mode:   hold BLOCKS API mode (the keyboard only reports its buttons in API mode)
#   buttons:    map < / > (button ids verified on hardware) to previous/next track
#   expression: turn on MPE pitch bend / pressure in the active mode if they're off
PROFILES = {
    'RP4': dict(name='ROLI Piano 49', api_mode=True, buttons=True, expression=True),
    # Experimental, not tested on hardware: lights only. Same protocol and config items as the
    # Piano per roli_blocks_basics; button ids and expression behaviour are unverified, so
    # those features stay off.
    'LKB': dict(name='LUMI Keys (experimental)', api_mode=False, buttons=False, expression=False),
}

PROBE_INTERVAL_TICKS = 20  # update_display runs ~10 Hz
# The keyboard only reports its </> buttons in API mode, which it leaves if no host ping
# arrives for 5 s (roli_BlocksProtocolDefinitions.h). Ping ~1 Hz; re-enter if ACKs stop.
PING_INTERVAL_TICKS = 10
API_MODE_TIMEOUT_TICKS = 50
MIN_WRITE_INTERVAL_TICKS = 2

SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'device_snapshot.json')


def _argb(rgb):
    v = 0xFF000000 | (rgb & 0xFFFFFF)
    return v - (1 << 32)


def _visible(rgb, floor=0x50):
    """Lift very dark colors so they still read on the LEDs."""
    r, g, b = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
    peak = max(r, g, b)
    if peak == 0:
        return (floor << 16) | (floor << 8) | floor
    if peak < floor:
        k = float(floor) / peak
        r, g, b = int(r * k), int(g * k), int(b * k)
    return (r << 16) | (g << 8) | b


def _brighter(rgb, amount=0.55):
    r, g, b = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
    r, g, b = [int(c + (255 - c) * amount) for c in (r, g, b)]
    return (r << 16) | (g << 8) | b


class ROLIForLive(ControlSurface):

    def __init__(self, c_instance):
        super(ROLIForLive, self).__init__(c_instance)
        with self.component_guard():
            self._serial = None
            self._profile = None
            self._mode = None
            self._device_config = {}
            self._sent = {}
            self._pending = {}
            self._snapshot = None
            self._expression_checked = False
            self._ticks = 0
            self._last_probe = -PROBE_INTERVAL_TICKS
            self._last_write = 0
            self._last_ping = 0
            self._last_ack = None
            self._track = None
            self._unsupported_scale_reported = None
            self._playing = PlayingNotes(self._send_midi, self.log_message)
            self._add_song_listeners()
            self.set_feedback_channels(list(PLAYING_NOTES_FEEDBACK_CHANNELS))
            # Velocity Live uses for the echoed notes; Live's own BLOCKS script sets this too.
            if hasattr(self._c_instance, 'set_feedback_velocity'):
                self._c_instance.set_feedback_velocity(PLAYING_NOTES_FEEDBACK_VELOCITY)
            self._on_track_selected()
            from . import __version__
            self.log_message('ROLI for Live %s: started' % __version__)

    # ---------------------------------------------------------------- lifecycle

    def disconnect(self):
        self._restore_snapshot()
        self.release_controlled_track()
        self._playing.disconnect()
        self._remove_song_listeners()
        self._set_track(None)
        super(ROLIForLive, self).disconnect()

    def port_settings_changed(self):
        super(ROLIForLive, self).port_settings_changed()
        self._reset_device_state()

    def refresh_state(self):
        super(ROLIForLive, self).refresh_state()
        self._reset_device_state()

    def _reset_device_state(self):
        self._serial = None
        self._profile = None
        self._mode = None
        self._device_config = {}
        self._sent = {}
        self._expression_checked = False
        self._last_probe = -PROBE_INTERVAL_TICKS
        self._last_ack = None

    def update_display(self):
        super(ROLIForLive, self).update_display()
        self._ticks += 1
        self._playing.update(self.song())
        if self._serial is None:
            if self._ticks - self._last_probe >= PROBE_INTERVAL_TICKS:
                self._last_probe = self._ticks
                self._send_midi(blocks.SERIAL_DUMP_REQUEST)
            return
        if self._profile['api_mode']:
            self._keep_api_mode()
        if self._snapshot is None or not self._expression_checked:
            missing = [i for i in self._required_items() if i not in self._device_config]
            if missing:
                if self._ticks - self._last_probe >= PROBE_INTERVAL_TICKS:
                    self._last_probe = self._ticks
                    for item in missing:
                        self._send_midi(blocks.config_request(item))
                return
            if self._mode is None:
                mode = self._device_config[MODE]
                if not 0 <= mode < NUM_MODES:
                    if self._ticks - self._last_probe >= PROBE_INTERVAL_TICKS:
                        self._last_probe = self._ticks
                        self.log_message('ROLI for Live: keyboard reports mode %r; leaving it alone' % mode)
                    return
                self._mode = mode
                return  # read the active mode's items next
            if self._snapshot is None:
                self._take_snapshot()
            if not self._expression_checked:
                self._ensure_expression()
            self._update_lighting()
        self._flush()

    # ---------------------------------------------------------------- device I/O

    def handle_sysex(self, midi_bytes):
        if self._serial is None:
            serial = blocks.parse_serial(midi_bytes)
            if serial is not None:
                profile = PROFILES.get(serial[:3])
                if profile is not None:
                    self._serial = serial
                    self._profile = profile
                    self.log_message('ROLI for Live: found %s (%s...)' % (profile['name'], serial[:3]))
                    self._last_probe = -PROBE_INTERVAL_TICKS
                else:
                    self.log_message('ROLI for Live: unsupported ROLI device %s..., staying idle' % serial[:3])
                return
        for event in blocks.parse_device_packet(midi_bytes):
            if event[0] == 'ack':
                self._last_ack = self._ticks
            elif event[0] == 'config':
                item, value = event[1], event[2]
                if item == MODE and self._mode is not None and value != self._mode:
                    self._on_mode_changed(value)
                self._device_config[item] = value
            elif event[0] == 'button' and event[2] and self._profile and self._profile['buttons']:
                self.log_message('ROLI for Live: button %d pressed' % event[1])
                if event[1] == BUTTON_PREVIOUS:
                    self._select_relative_track(-1)
                elif event[1] == BUTTON_NEXT:
                    self._select_relative_track(1)

    def _required_items(self):
        items = [MODE] + list(SHARED_LIGHTING_ITEMS)
        if self._mode is not None:
            items += self._lighting_mode_items()
            if self._profile['expression']:
                items += self._expression_mode_items()
        return items

    def _lighting_mode_items(self):
        return [mode_item(self._mode, _COLOR_TYPE), mode_item(self._mode, _SHOW_SCALE)]

    def _expression_mode_items(self):
        return [mode_item(self._mode, o) for o in (_MIDI_MODE, _PITCH_ENABLE, _PRESSURE_ENABLE)]

    def _on_mode_changed(self, mode):
        """The user switched the keyboard's mode: give the old mode its settings back, start over."""
        self.log_message('ROLI for Live: keyboard mode changed %r -> %r' % (self._mode, mode))
        self._restore_snapshot()
        for item in self._lighting_mode_items() + self._expression_mode_items():
            self._device_config.pop(item, None)
        self._snapshot = None
        self._sent = {}
        self._pending = {}
        self._mode = None
        self._expression_checked = False
        self._last_probe = -PROBE_INTERVAL_TICKS

    def _keep_api_mode(self):
        if self._last_ack is None or self._ticks - self._last_ack > API_MODE_TIMEOUT_TICKS:
            self._send_midi(blocks.device_command(blocks.CMD_BEGIN_API_MODE))
            self._last_ack = self._ticks  # give it time to answer before retrying
            self.log_message('ROLI for Live: entering API mode')
        if self._ticks - self._last_ping >= PING_INTERVAL_TICKS:
            self._last_ping = self._ticks
            self._send_midi(blocks.device_command(blocks.CMD_PING))

    def _write(self, item, value):
        if self._sent.get(item) != value:
            self._pending[item] = value

    def _flush(self):
        if not self._pending or self._ticks - self._last_write < MIN_WRITE_INTERVAL_TICKS:
            return
        self._last_write = self._ticks
        pending, self._pending = self._pending, {}
        for item, value in pending.items():
            msg = blocks.config_set(item, value)
            ok = self._send_midi(msg)
            self._sent[item] = value
            self.log_message('ROLI for Live: set item %d = %d (sent=%r) %s'
                             % (item, value, ok, ' '.join('%02X' % b for b in msg)))

    # ---------------------------------------------------------------- snapshot / restore

    def _take_snapshot(self):
        snap = None
        try:
            if os.path.exists(SNAPSHOT_PATH):
                with open(SNAPSHOT_PATH) as f:
                    stored = json.load(f)
                if stored.get('serial') == self._serial and stored.get('mode', 0) == self._mode:
                    snap = dict((int(k), v) for k, v in stored['items'].items())
        except Exception as e:
            self.log_message('ROLI for Live: could not read snapshot: %s' % e)
        if snap is None:
            snap = dict((i, self._device_config[i])
                        for i in list(SHARED_LIGHTING_ITEMS) + self._lighting_mode_items())
            try:
                with open(SNAPSHOT_PATH, 'w') as f:
                    json.dump({'serial': self._serial, 'mode': self._mode, 'items': snap}, f)
            except Exception as e:
                self.log_message('ROLI for Live: could not write snapshot: %s' % e)
        self._snapshot = snap
        self.log_message('ROLI for Live: lighting snapshot %r' % (snap,))

    def _restore_snapshot(self):
        if not self._snapshot or self._serial is None:
            return
        for item, value in self._snapshot.items():
            self._send_midi(blocks.config_set(item, value))
        try:
            os.remove(SNAPSHOT_PATH)
        except OSError:
            pass
        self.log_message('ROLI for Live: restored keyboard lighting')

    # ---------------------------------------------------------------- expression

    def _ensure_expression(self):
        self._expression_checked = True
        if not self._profile['expression']:
            return
        changed = []
        for item in self._expression_mode_items():
            if self._device_config.get(item) != 1:
                self._write(item, 1)
                changed.append(item)
        if changed:
            self.log_message('ROLI for Live: enabled MPE / pitch bend / pressure (items %r)' % (changed,))
            self.show_message('ROLI for Live: turned on MPE pitch bend and pressure on the keyboard')

    # ---------------------------------------------------------------- lighting

    def _update_lighting(self):
        if self._serial is None or self._snapshot is None or self._mode is None:
            return
        song = self.song()
        root = int(getattr(song, 'root_note', 0)) % 12
        scale_on = bool(getattr(song, 'scale_mode', True))
        intervals = list(getattr(song, 'scale_intervals', [0, 2, 4, 5, 7, 9, 11]))
        index = builtin_index(intervals)
        if index is None:
            index = CHROMATIC
            name = getattr(song, 'scale_name', '?')
            if self._unsupported_scale_reported != name:
                self._unsupported_scale_reported = name
                self.show_message('ROLI for Live: "%s" is not one of the keyboard\'s built-in scales; '
                                  'showing the root note only' % name)
                self.log_message('ROLI for Live: unsupported scale %r intervals %r' % (name, intervals))
        else:
            self._unsupported_scale_reported = None
        color = self._track_color()
        self._write(mode_item(self._mode, _COLOR_TYPE), COLOR_TYPE_USER)
        self._write(mode_item(self._mode, _SHOW_SCALE), 1 if scale_on else 0)
        self._write(KEY, root)
        self._write(SCALE, index)
        self._write(GLOBAL_KEY_COLOUR, _argb(color))
        self._write(ROOT_KEY_COLOUR, _argb(_brighter(color)))

    def _track_color(self):
        track = self._track
        try:
            if track is not None:
                return _visible(int(track.color))
        except Exception:
            pass
        return 0x5080FF

    # ---------------------------------------------------------------- Live listeners

    def _make_callback(self):
        # Live rejects registering the same callable on one object twice, so each
        # observed property gets its own function.
        return lambda: self._update_lighting()

    def _add_song_listeners(self):
        song = self.song()
        self._listeners = [(song.view, 'selected_track', self._on_track_selected)]
        for prop in ('root_note', 'scale_name', 'scale_intervals', 'scale_mode'):
            if hasattr(song, 'add_%s_listener' % prop):
                self._listeners.append((song, prop, self._make_callback()))
        for prop in ('current_song_time', 'is_playing'):
            if hasattr(song, 'add_%s_listener' % prop):
                self._listeners.append((song, prop, lambda: self._playing.update(self.song())))
        for obj, prop, cb in self._listeners:
            getattr(obj, 'add_%s_listener' % prop)(cb)

    def _remove_song_listeners(self):
        for obj, prop, cb in getattr(self, '_listeners', []):
            try:
                if getattr(obj, '%s_has_listener' % prop)(cb):
                    getattr(obj, 'remove_%s_listener' % prop)(cb)
            except Exception:
                pass
        self._listeners = []

    def _on_track_selected(self):
        track = self.song().view.selected_track
        self._set_track(track)
        self._playing.set_track(track)
        if track is not None and getattr(track, 'has_midi_input', False):
            self.set_controlled_track(track)
        else:
            self.release_controlled_track()
        self._update_lighting()

    def _set_track(self, track):
        old, cb = self._track, getattr(self, '_track_color_cb', None)
        if old is not None and cb is not None:
            try:
                if old.color_has_listener(cb):
                    old.remove_color_listener(cb)
            except Exception:
                pass  # track was deleted
        self._track = track
        self._track_color_cb = None
        if track is not None and hasattr(track, 'add_color_listener'):
            self._track_color_cb = self._make_callback()
            track.add_color_listener(self._track_color_cb)

    def _select_relative_track(self, delta):
        song = self.song()
        tracks = list(song.visible_tracks) + list(song.return_tracks) + [song.master_track]
        current = song.view.selected_track
        try:
            i = tracks.index(current)
        except ValueError:
            i = 0
        j = max(0, min(len(tracks) - 1, i + delta))
        if j != i:
            song.view.selected_track = tracks[j]
