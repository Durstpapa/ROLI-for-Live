"""ROLI for Live: makes a ROLI keyboard follow Live's scale and selected track color.

Performance MIDI (notes, per-note pitch bend, pressure) is never touched by this script;
it reaches tracks through Live's normal MIDI input. The script only talks BLOCKS SysEx.
"""
from __future__ import absolute_import, print_function, unicode_literals

import json
import os
import tempfile
import time

from _Framework.ControlSurface import ControlSurface

from . import blocks
from .playing_notes import PlayingNotes, playing_clip
from .scales import BUILTIN_SCALES, CHROMATIC, builtin_index

# BLOCKS config item ids (roli_BlockConfigId.h)
MODE = 20
SCALE = 22
KEY = 27
GLOBAL_KEY_COLOUR = 34
ROOT_KEY_COLOUR = 35
BRIGHTNESS = 36
# Per-mode items: mode N uses 100 + 7 * N + offset (modes 0-3).
NUM_MODES = 4
_COLOR_TYPE, _MIDI_MODE, _PITCH_ENABLE, _PRESSURE_ENABLE, _SHOW_SCALE = range(5)


def mode_item(mode, offset):
    return 100 + 7 * mode + offset


COLOR_TYPE_USER = 1
COLOR_TYPE_RAINBOW = 4  # Rainbow scheme read back after the Dashboard hardware test.
KEY_COLORS = ('white', 'track', 'rainbow')
SHARED_LIGHTING_ITEMS = (SCALE, KEY, GLOBAL_KEY_COLOUR, ROOT_KEY_COLOUR, BRIGHTNESS)

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
#   expression: configure native MPE pitch bend / pressure in the active mode
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
DEVICE_RESPONSE_TIMEOUT_SECONDS = 5.0
MIN_WRITE_INTERVAL_TICKS = 2

SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'device_snapshot.json')
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
DEFAULT_SETTINGS = dict(key_colors='white', scale_lighting=True, playing_notes=True, root_color=True,
                        clip_scale=False, background_intensity=100, global_brightness=None,
                        pitch_bend=True, pressure=True)


def _is_percent(value):
    return type(value) is int and 0 <= value <= 100


def _argb(rgb):
    v = 0xFF000000 | (rgb & 0xFFFFFF)
    return v - (1 << 32)


def _dim(rgb, amount):
    r, g, b = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
    return (int(r * amount) << 16) | (int(g * amount) << 8) | int(b * amount)


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
            self._disconnecting = False
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
            self._last_response = None
            self._track = None
            self._unsupported_scale_reported = None
            self._scale_source_status = 'live'
            self._scale_source_enabled = False
            self._clip_scale_error = None
            self._settings_error = False
            self._settings = self._load_settings()
            self._playing = PlayingNotes(self._send_midi, self.log_message,
                                         velocity=PLAYING_NOTES_FEEDBACK_VELOCITY)
            self._add_song_listeners()
            self._configure_note_feedback()
            self._on_track_selected()
            from . import __version__
            self.log_message('ROLI for Live %s: started' % __version__)
            if PLAYING_NOTES_FEEDBACK_VELOCITY != 127:
                self.log_message('ROLI for Live: temporary playback-highlight test at '
                                 'feedback velocity %d' % PLAYING_NOTES_FEEDBACK_VELOCITY)

    # ---------------------------------------------------------------- lifecycle

    def get_roli_lighting_state(self):
        """Versioned reply for the optional Max for Live controls."""
        ready = self._keyboard_ready()
        return 'roli_lighting_v1 %d %d' % (int(self._settings['key_colors'] == 'white'), int(ready))

    def get_roli_controls_state(self):
        ready = self._keyboard_ready()
        return 'roli_controls_v2 %d %d %d %d %d' % (
            int(self._settings['key_colors'] == 'white'), int(self._settings['scale_lighting']),
            int(self._settings['playing_notes']), int(ready), int(not self._settings_error))

    def get_roli_controls_state_v3(self):
        ready = self._keyboard_ready()
        return 'roli_controls_v3 %d %d %d %d %d %d' % (
            int(self._settings['key_colors'] == 'white'), int(self._settings['scale_lighting']),
            int(self._settings['playing_notes']), int(self._settings['root_color']),
            int(ready), int(not self._settings_error))

    def get_roli_controls_state_v4(self):
        return 'roli_controls_v4 %d %d %d %d %d %d %d %s' % (
            int(self._settings['key_colors'] == 'white'), int(self._settings['scale_lighting']),
            int(self._settings['playing_notes']), int(self._settings['root_color']),
            int(self._settings['clip_scale']), int(self._keyboard_ready()),
            int(not self._settings_error), self._scale_source_status)

    def get_roli_controls_state_v5(self):
        brightness = self._settings['global_brightness']
        if brightness is None:
            brightness = self._device_config.get(BRIGHTNESS, -1)
        return self.get_roli_controls_state_v4().replace('roli_controls_v4', 'roli_controls_v5', 1) + (
            ' %d %d' % (brightness, self._settings['background_intensity']))

    def get_roli_controls_state_v6(self):
        return self.get_roli_controls_state_v5().replace('roli_controls_v5', 'roli_controls_v6', 1) + (
            ' ' + self._settings['key_colors'])

    def get_roli_controls_state_v7(self):
        return self.get_roli_controls_state_v6().replace('roli_controls_v6', 'roli_controls_v7', 1) + (
            ' %d' % int(self._scale_source_enabled))

    def get_roli_controls_state_v8(self):
        return self.get_roli_controls_state_v7().replace('roli_controls_v7', 'roli_controls_v8', 1) + (
            ' %d %d %d' % (int(self._settings['pitch_bend']), int(self._settings['pressure']),
                           int(bool(self._profile and self._profile['expression']))))

    def _keyboard_ready(self):
        return (self._serial is not None and self._snapshot is not None and self._mode is not None
                and self._last_response is not None
                and time.monotonic() - self._last_response <= DEVICE_RESPONSE_TIMEOUT_SECONDS)

    def set_roli_white_keys(self, value):
        self._set_setting('white_keys', value)
        return self.get_roli_lighting_state()

    def set_roli_key_colors(self, value):
        if type(value) is not int or not 0 <= value < len(KEY_COLORS):
            self.log_message('ROLI for Live: rejected key_colors value %r' % (value,))
            raise ValueError('key_colors must be 0 (White), 1 (Track), or 2 (Rainbow)')
        updated = dict(self._settings)
        updated['key_colors'] = KEY_COLORS[value]
        self._save_settings(updated)
        self._settings = updated
        self._update_lighting()
        self.log_message('ROLI for Live: saved key_colors %s' % KEY_COLORS[value])
        return self.get_roli_controls_state_v6()

    def set_roli_scale_lighting(self, value):
        self._set_setting('scale_lighting', value)
        return self.get_roli_controls_state()

    def set_roli_playing_notes(self, value):
        self._set_setting('playing_notes', value)
        return self.get_roli_controls_state()

    def set_roli_root_color(self, value):
        self._set_setting('root_color', value)
        return self.get_roli_controls_state_v3()

    def set_roli_clip_scale(self, value):
        self._set_setting('clip_scale', value)
        return self.get_roli_controls_state_v4()

    def set_roli_pitch_bend(self, value):
        self._set_expression('pitch_bend', value)
        return self.get_roli_controls_state_v8()

    def set_roli_pressure(self, value):
        self._set_expression('pressure', value)
        return self.get_roli_controls_state_v8()

    def _set_expression(self, name, value):
        if not self._keyboard_ready() or not self._profile['expression']:
            self.log_message('ROLI for Live: rejected %s; expression controls unavailable' % name)
            raise RuntimeError('Expression controls require a connected, supported keyboard')
        self._set_setting(name, value)

    def set_roli_global_brightness(self, value):
        self._set_level('global_brightness', value)
        return self.get_roli_controls_state_v5()

    def set_roli_background_intensity(self, value):
        self._set_level('background_intensity', value)
        return self.get_roli_controls_state_v5()

    def _set_level(self, name, value):
        if not _is_percent(value):
            self.log_message('ROLI for Live: rejected %s value %r' % (name, value))
            raise ValueError('%s must be an integer from 0 to 100' % name)
        updated = dict(self._settings)
        updated[name] = value
        self._save_settings(updated)
        self._settings = updated
        self._update_lighting()
        self.log_message('ROLI for Live: saved %s %d%%' % (name, value))

    def _set_setting(self, name, value):
        if type(value) is not int or value not in (0, 1):
            self.log_message('ROLI for Live: rejected %s value %r' % (name, value))
            raise ValueError('%s must be 0 or 1' % name)
        updated = dict(self._settings)
        if name == 'white_keys':
            updated['key_colors'] = 'white' if value else 'track'
        else:
            updated[name] = bool(value)
        self._save_settings(updated)
        self._settings = updated
        if name == 'playing_notes':
            self._configure_note_feedback(clear=not bool(value))
        if name in ('pitch_bend', 'pressure'):
            self._ensure_expression()
        self._update_lighting()
        self.log_message('ROLI for Live: saved %s %s' % (name, 'on' if value else 'off'))

    def _settings_failure(self, action, error):
        self._settings_error = True
        message = 'ROLI for Live: could not %s settings: %s' % (action, error)
        self.log_message(message)
        self.show_message(message)

    def _load_settings(self):
        try:
            with open(SETTINGS_PATH) as file:
                stored = json.load(file)
            if (not isinstance(stored, dict) or type(stored.get('version')) is not int
                    or stored['version'] not in (1, 2, 3, 4, 5, 6)):
                raise ValueError('Invalid settings schema or version')
            fields = set(DEFAULT_SETTINGS)
            levels = {'background_intensity', 'global_brightness'}
            if stored['version'] < 6:
                fields -= {'pitch_bend', 'pressure'}
            if stored['version'] < 5:
                fields.remove('key_colors')
                fields.add('white_keys')
            if stored['version'] < 4:
                fields -= levels
            if stored['version'] < 3:
                fields.remove('clip_scale')
            if stored['version'] == 1:
                fields.remove('root_color')
            if (set(stored) != fields | {'version'}
                    or any(type(stored[name]) is not bool for name in fields - levels - {'key_colors'})):
                raise ValueError('Invalid settings schema or version')
            if stored['version'] >= 5 and stored['key_colors'] not in KEY_COLORS:
                raise ValueError('Invalid key color setting')
            if stored['version'] >= 4 and (
                    not _is_percent(stored['background_intensity'])
                    or (stored['global_brightness'] is not None
                        and not _is_percent(stored['global_brightness']))):
                raise ValueError('Invalid brightness settings')
            settings = dict(DEFAULT_SETTINGS)
            settings.update((name, stored[name]) for name in fields)
            if stored['version'] < 5:
                settings['key_colors'] = 'white' if settings.pop('white_keys') else 'track'
            return settings
        except FileNotFoundError:
            return dict(DEFAULT_SETTINGS)
        except (OSError, ValueError) as error:
            self._settings_failure('read', error)
            return dict(DEFAULT_SETTINGS)

    def _save_settings(self, settings):
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix='.roli-settings-', suffix='.tmp',
                                             dir=os.path.dirname(SETTINGS_PATH))
            with os.fdopen(fd, 'w') as file:
                json.dump(dict(settings, version=6), file, sort_keys=True)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, SETTINGS_PATH)
            temporary = None
            self._settings_error = False
        except OSError as error:
            self._settings_failure('save', error)
            raise
        finally:
            if temporary is not None:
                try:
                    os.remove(temporary)
                except OSError as error:
                    self.log_message('ROLI for Live: could not remove temporary settings: %s' % error)

    def _configure_note_feedback(self, clear=False):
        enabled = self._settings['playing_notes']
        self._playing.set_enabled(enabled)
        self.set_feedback_channels(list(PLAYING_NOTES_FEEDBACK_CHANNELS) if enabled else [])
        if hasattr(self._c_instance, 'set_feedback_velocity'):
            self._c_instance.set_feedback_velocity(PLAYING_NOTES_FEEDBACK_VELOCITY if enabled else 0)
        if clear and self._serial is not None:
            # Clear notes echoed by Live itself, not just the clip notes tracked by PlayingNotes.
            for pitch in range(128):
                self._send_midi((0x80, pitch, 0))

    def disconnect(self):
        if self._disconnecting:
            return
        self._disconnecting = True
        self._pending = {}
        self._remove_song_listeners()
        self._set_track(None)
        self.release_controlled_track()
        self.set_feedback_channels([])
        if hasattr(self._c_instance, 'set_feedback_velocity'):
            self._c_instance.set_feedback_velocity(0)
        self._playing.disconnect()
        self._restore_snapshot()
        if self._serial is not None and self._profile['api_mode']:
            if self._send_midi(blocks.device_command(blocks.CMD_END_API_MODE)):
                self.log_message('ROLI for Live: requested native keyboard control (end API mode)')
            else:
                self.log_message('ROLI for Live: could not send end API mode')
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
        self._pending = {}
        self._snapshot = None
        self._expression_checked = False
        self._last_probe = -PROBE_INTERVAL_TICKS
        self._last_ack = None
        self._last_response = None

    def update_display(self):
        if self._disconnecting:
            return
        super(ROLIForLive, self).update_display()
        self._ticks += 1
        if (self._serial is not None and self._last_response is not None
                and time.monotonic() - self._last_response > DEVICE_RESPONSE_TIMEOUT_SECONDS):
            self.log_message('ROLI for Live: keyboard stopped responding; waiting for reconnection')
            self._reset_device_state()
        self._playing.update(self.song())
        if self._settings['clip_scale']:
            self._update_lighting()
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
        if self._ticks - self._last_probe >= PROBE_INTERVAL_TICKS:
            self._last_probe = self._ticks
            self._send_midi(blocks.config_request(MODE))
        self._flush()

    # ---------------------------------------------------------------- device I/O

    def handle_sysex(self, midi_bytes):
        if self._disconnecting:
            return
        if self._serial is None:
            serial = blocks.parse_serial(midi_bytes)
            if serial is not None:
                profile = PROFILES.get(serial[:3])
                if profile is not None:
                    self._serial = serial
                    self._profile = profile
                    self._last_response = time.monotonic()
                    self.log_message('ROLI for Live: found %s (%s...)' % (profile['name'], serial[:3]))
                    self._last_probe = -PROBE_INTERVAL_TICKS
                else:
                    self.log_message('ROLI for Live: unsupported ROLI device %s..., staying idle' % serial[:3])
                return
        if self._serial is None:
            return
        for event in blocks.parse_device_packet(midi_bytes):
            self._last_response = time.monotonic()
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
        else:
            self._pending.pop(item, None)

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
        changed = False
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
            changed = True
        elif BRIGHTNESS not in snap:
            snap[BRIGHTNESS] = self._device_config[BRIGHTNESS]
            changed = True
        if self._profile['expression']:
            for item in self._expression_mode_items():
                if item not in snap:
                    snap[item] = self._device_config[item]
                    changed = True
        if changed:
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
        sent = True
        for item, value in self._snapshot.items():
            if not self._send_midi(blocks.config_set(item, value)):
                sent = False
                self.log_message('ROLI for Live: could not send lighting restore item %d' % item)
        if not sent:
            self.show_message('ROLI for Live: lighting restore send failed; recovery snapshot retained')
            return
        try:
            os.remove(SNAPSHOT_PATH)
        except FileNotFoundError:
            pass
        except OSError as error:
            self.log_message('ROLI for Live: could not remove lighting snapshot: %s' % error)
        self.log_message('ROLI for Live: sent lighting restore request (hardware result unverified)')

    # ---------------------------------------------------------------- expression

    def _ensure_expression(self):
        self._expression_checked = True
        if not self._profile['expression']:
            return
        changed = []
        values = (1, int(self._settings['pitch_bend']), int(self._settings['pressure']))
        for item, value in zip(self._expression_mode_items(), values):
            self._write(item, value)
            if self._device_config.get(item) != value:
                changed.append((item, value))
        if changed:
            self.log_message('ROLI for Live: queued native MPE / pitch bend / pressure settings %r' % (changed,))
            self.show_message('ROLI for Live: requested keyboard pitch bend and pressure settings')

    # ---------------------------------------------------------------- lighting

    def _scale_state(self):
        song = self.song()
        state = (int(getattr(song, 'root_note', 0)) % 12,
                 bool(getattr(song, 'scale_mode', True)),
                 tuple(getattr(song, 'scale_intervals', [0, 2, 4, 5, 7, 9, 11])),
                 getattr(song, 'scale_name', '?'))
        self._scale_source_status = 'live'
        error = None
        if self._settings['clip_scale']:
            try:
                clip = playing_clip(song, self._track)
                if clip is None:
                    self._scale_source_status = 'idle'
                else:
                    root, enabled = clip.root_note, clip.scale_mode
                    intervals, name = tuple(clip.scale_intervals), clip.scale_name
                    if (type(root) is not int or not 0 <= root < 12 or not intervals
                            or any(type(i) is not int or not 0 <= i < 12 for i in intervals)):
                        raise ValueError('invalid clip root or scale intervals')
                    state = (root, bool(enabled), intervals, name)
                    self._scale_source_status = 'clip'
            except AttributeError as exc:
                self._scale_source_status = 'unsupported'
                error = ('clip scale unavailable; requires clip-scale API support '
                         '(Live 12.4.15b1 or newer): %s; using Live scale' % exc)
            except (RuntimeError, IndexError, TypeError, ValueError) as exc:
                self._scale_source_status = 'error'
                error = 'could not read playing clip scale: %s; using Live scale' % exc
        if error is not None and error != self._clip_scale_error:
            self.log_message('ROLI for Live: %s' % error)
            self.show_message('ROLI for Live: %s' % error)
        self._clip_scale_error = error
        self._scale_source_enabled = state[1]
        return state

    def _update_lighting(self):
        if self._disconnecting or self._serial is None or self._snapshot is None or self._mode is None:
            return
        if self._settings['global_brightness'] is not None:
            self._write(BRIGHTNESS, self._settings['global_brightness'])
        if not self._settings['scale_lighting']:
            self._scale_source_status = 'off'
            self._scale_source_enabled = False
            for item, value in self._snapshot.items():
                if item in list(SHARED_LIGHTING_ITEMS) + self._lighting_mode_items() and item != BRIGHTNESS:
                    self._write(item, value)
            return
        root, scale_on, intervals, name = self._scale_state()
        # Rainbow still uses the native scale mask with Show Scale off.
        index = builtin_index(intervals) if scale_on else CHROMATIC
        if index is None:
            index = CHROMATIC
            if self._unsupported_scale_reported != name:
                self._unsupported_scale_reported = name
                self.show_message('ROLI for Live: "%s" is not one of the keyboard\'s built-in scales; '
                                  'showing the root note only' % name)
                self.log_message('ROLI for Live: unsupported scale %r intervals %r' % (name, intervals))
        else:
            self._unsupported_scale_reported = None
        color = self._track_color()
        rainbow = self._settings['key_colors'] == 'rainbow'
        self._write(mode_item(self._mode, _COLOR_TYPE),
                    COLOR_TYPE_RAINBOW if rainbow else COLOR_TYPE_USER)
        self._write(mode_item(self._mode, _SHOW_SCALE), 1 if scale_on else 0)
        self._write(KEY, root)
        self._write(SCALE, index)
        if rainbow:
            for item in (GLOBAL_KEY_COLOUR, ROOT_KEY_COLOUR):
                self._write(item, self._snapshot[item])
            return
        white_keys = self._settings['key_colors'] == 'white'
        key_color = 0xFFFFFF if white_keys else color
        root_color = color if white_keys else _brighter(color)
        root_color = root_color if self._settings['root_color'] else key_color
        intensity = self._settings['background_intensity'] / 100.0
        self._write(GLOBAL_KEY_COLOUR, _argb(_dim(key_color, intensity)))
        self._write(ROOT_KEY_COLOUR, _argb(_dim(root_color, intensity)))

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

    def _on_playback_changed(self):
        self._playing.update(self.song())
        if self._settings['clip_scale']:
            self._update_lighting()

    def _add_song_listeners(self):
        song = self.song()
        self._listeners = [(song.view, 'selected_track', self._on_track_selected)]
        for prop in ('root_note', 'scale_name', 'scale_intervals', 'scale_mode'):
            if hasattr(song, 'add_%s_listener' % prop):
                self._listeners.append((song, prop, self._make_callback()))
        for prop in ('current_song_time', 'is_playing'):
            if hasattr(song, 'add_%s_listener' % prop):
                self._listeners.append((song, prop, lambda: self._on_playback_changed()))
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
        if self._disconnecting:
            return
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
