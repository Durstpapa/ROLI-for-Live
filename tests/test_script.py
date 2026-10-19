"""Runs ROLI_for_Live against a fake Live and a fake keyboard. Usage: py -3.11 tests/test_script.py"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'fake_live'))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

from _Framework.ControlSurface import ControlSurface, Observable  # noqa: E402
import ROLI_for_Live  # noqa: E402
from ROLI_for_Live import blocks, roli_for_live  # noqa: E402

roli_for_live.SNAPSHOT_PATH = os.path.join(HERE, 'device_snapshot.test.json')

# Serial dump reply captured from the real keyboard (MAC/serial tail anonymised).
def serial_reply(serial):
    return bytes([0xF0, 0x00, 0x21, 0x10, 0x78, 0x3A]) + b'RISE1.00' + bytes(32) + \
        b'48:B6:20:00:00:00' + serial + bytes([0x01, 0xF7])


SERIAL_REPLY = serial_reply(b'RP4800000000TEST')

COMMANDS = []
DEVICE = {20: 0, 22: 0, 27: 0, 34: -1002466, 35: -3623796, 36: 100,
          100: 0, 101: 1, 102: 0, 103: 1, 104: 1}


def device_reply(item, value):
    payload = blocks._pack([(0, 32), (0x18, 7), (4, 4), (item, 8), (value & 0xFFFFFFFF, 32),
                            (0, 32), (0, 32)])
    return blocks.BLOCKS_PREFIX + (0x6D,) + tuple(payload) + (blocks._checksum(payload), 0xF7)


def button_packet(button_id, down=True):
    payload = blocks._pack([(0, 32), (0x20 if down else 0x21, 7), (0, 5), (button_id, 12)])
    return blocks.BLOCKS_PREFIX + (0x6D,) + tuple(payload) + (blocks._checksum(payload), 0xF7)


class FakeNote(object):
    def __init__(self, pitch, start, duration, mute=False):
        self.pitch, self.start_time, self.duration, self.mute = pitch, start, duration, mute


class FakeClip(Observable):
    def __init__(self, notes):
        Observable.__init__(self, notes=None, playing_position=0.0, is_playing=True, name='Riff')
        self._note_list = notes

    def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        return list(self._note_list)


class FakeSlot(object):
    def __init__(self, clip):
        self.clip = clip


def make_song():
    t1 = Observable(color=0xFF3B30, name='Bass')
    t1.has_midi_input = True
    t1.clip = FakeClip([FakeNote(60, 0.0, 1.0), FakeNote(64, 0.5, 1.0), FakeNote(67, 2.0, 1.0, mute=True)])
    t1.playing_slot_index = 0
    t1.clip_slots = [FakeSlot(t1.clip)]
    t1.arrangement_clips = []
    t2 = Observable(color=0x0A0A20, name='Pad')
    t2.has_midi_input = False
    master = Observable(color=0x808080, name='Master')
    view = Observable(selected_track=t1)
    song = Observable(is_playing=False, current_song_time=0.0, root_note=0, scale_name='Major', scale_intervals=[0, 2, 4, 5, 7, 9, 11], scale_mode=True)
    song.view = view
    song.visible_tracks = [t1, t2]
    song.return_tracks = []
    song.master_track = master
    return song, t1, t2


def run_device(surface):
    """Answer every request the script sent since last call, like the keyboard would."""
    while ControlSurface.sent:
        msg = ControlSurface.sent.pop(0)
        if msg == blocks.SERIAL_DUMP_REQUEST:
            surface.handle_sysex(tuple(SERIAL_REPLY))
            continue
        r = blocks._BitReader(list(msg[6:-2]))
        t = r.read(7)
        if t == blocks.MSG_DEVICE_COMMAND:
            COMMANDS.append(r.read(9))
            payload = blocks._pack([(0, 32), (0x02, 7), (0, 10)])  # packetACK
            surface.handle_sysex(blocks.BLOCKS_PREFIX + (0x6D,) + tuple(payload) + (blocks._checksum(payload), 0xF7))
            continue
        cmd = r.read(4)
        if (t, cmd) == (0x10, 1):
            r.read(32)
            item = r.read(8)
            if item in DEVICE:
                surface.handle_sysex(device_reply(item, DEVICE[item]))
        elif (t, cmd) == (0x10, 0):
            item = r.read(8)
            DEVICE[item] = blocks._s32(r.read(32))


def tick(surface, n=1):
    for _ in range(n):
        surface.update_display()
        run_device(surface)


def main():
    song, t1, t2 = make_song()
    ControlSurface.song_instance = song
    if os.path.exists(roli_for_live.SNAPSHOT_PATH):
        os.remove(roli_for_live.SNAPSHOT_PATH)
    original = dict(DEVICE)

    caps = ROLI_for_Live.get_capabilities()
    assert caps['controller_id']['vendor_id'] == 0x2AF4

    s = ROLI_for_Live.create_instance(object())
    assert s.get_roli_lighting_state() == 'roli_lighting_v1 1 0'
    for invalid in (-1, 2, 1.0, '1', None):
        try:
            s.set_roli_white_keys(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid white keys value accepted: %r' % (invalid,))
    assert s.get_roli_lighting_state() == 'roli_lighting_v1 1 0'
    tick(s, 60)
    assert ControlSurface.feedback_channels == [0]
    assert COMMANDS.count(blocks.CMD_BEGIN_API_MODE) == 1 and COMMANDS.count(blocks.CMD_PING) >= 3, COMMANDS
    assert ControlSurface.controlled_track is t1
    assert DEVICE[100] == 1 and DEVICE[104] == 1, DEVICE
    assert DEVICE[102] == 1, 'pitch bend should have been enabled'
    assert DEVICE[27] == 0 and DEVICE[22] == 0
    assert DEVICE[34] == roli_for_live._argb(0xFFFFFF), hex(DEVICE[34] & 0xFFFFFFFF)
    assert DEVICE[35] == roli_for_live._argb(0xFF3B30)
    assert s.get_roli_lighting_state() == 'roli_lighting_v1 1 1'
    assert s.set_roli_white_keys(1) == 'roli_lighting_v1 1 1'
    tick(s, 10)
    assert DEVICE[34] == roli_for_live._argb(0xFFFFFF)
    assert DEVICE[35] == roli_for_live._argb(0xFF3B30)
    t1.color = 0x123456
    tick(s, 10)
    assert DEVICE[34] == roli_for_live._argb(0xFFFFFF)
    assert DEVICE[35] == roli_for_live._argb(roli_for_live._visible(0x123456))
    t1.color = 0xFF3B30
    assert s.set_roli_white_keys(0) == 'roli_lighting_v1 0 1'
    tick(s, 10)
    assert DEVICE[34] == roli_for_live._argb(0xFF3B30)
    assert DEVICE[35] == roli_for_live._argb(roli_for_live._brighter(0xFF3B30))
    s.set_roli_white_keys(1)
    s.set_roli_white_keys(0)
    tick(s, 10)
    assert DEVICE[34] == roli_for_live._argb(0xFF3B30), 'rapid toggles must cancel stale queued colors'
    assert DEVICE[35] == roli_for_live._argb(roli_for_live._brighter(0xFF3B30))

    song.root_note = 2
    song.scale_intervals = [0, 2, 3, 5, 7, 8, 10]
    tick(s, 5)
    assert DEVICE[27] == 2 and DEVICE[22] == 1, DEVICE

    song.view.selected_track = t2
    tick(s, 5)
    assert ControlSurface.controlled_track is None  # audio track: nothing to echo
    assert DEVICE[34] == roli_for_live._argb(roli_for_live._visible(0x0A0A20))

    t2.color = 0x00FF00
    tick(s, 5)
    assert DEVICE[34] == roli_for_live._argb(0x00FF00)
    s.set_roli_white_keys(1)
    tick(s, 10)
    song.view.selected_track = t1
    tick(s, 10)
    assert DEVICE[34] == roli_for_live._argb(0xFFFFFF)
    assert DEVICE[35] == roli_for_live._argb(0xFF3B30)
    s.set_roli_white_keys(0)
    song.view.selected_track = t2
    tick(s, 10)

    song.scale_intervals = [0, 1, 4, 5, 7, 8, 10]  # Phrygian Dominant: no built-in match
    tick(s, 5)
    assert DEVICE[22] == 18
    assert any('not one of the keyboard' in l for l in ControlSurface.logs)

    song.scale_mode = False
    tick(s, 5)
    assert DEVICE[104] == 0

    s.handle_sysex(button_packet(3))
    assert song.view.selected_track is t1
    s.handle_sysex(button_packet(4))
    s.handle_sysex(button_packet(4))
    assert song.view.selected_track.name == 'Master', song.view.selected_track.name

    assert any('button 3 pressed' in l for l in ControlSurface.logs)

    # playing-note lights for the selected track's clip
    song.view.selected_track = t1
    ControlSurface.notes_out[:] = []
    song.is_playing = True
    t1.clip.playing_position = 0.25
    song.current_song_time = 0.25
    assert ControlSurface.notes_out == [(0x90, 60, 127)], ControlSurface.notes_out
    t1.clip.playing_position = 0.75
    song.current_song_time = 0.75
    assert ControlSurface.notes_out[-1] == (0x90, 64, 127)
    t1.clip.playing_position = 1.2
    song.current_song_time = 1.2
    assert ControlSurface.notes_out[-1] == (0x80, 60, 0)
    t1.clip.playing_position = 2.5  # only a muted note here
    song.current_song_time = 2.5
    assert (0x80, 64, 0) in ControlSurface.notes_out and (0x90, 67, 127) not in ControlSurface.notes_out
    t1.clip.playing_position = 0.6
    song.current_song_time = 0.6
    song.is_playing = False
    assert ControlSurface.notes_out[-2:] == [(0x80, 60, 0), (0x80, 64, 0)], ControlSurface.notes_out[-4:]

    # arrangement clip at bar 2 (beat 4), looping beats 0..2, starting at marker 0
    arr = FakeClip([FakeNote(72, 0.0, 0.5), FakeNote(74, 1.0, 0.5)])
    arr.start_time, arr.end_time, arr.start_marker = 4.0, 12.0, 0.0
    arr.looping, arr.loop_start, arr.loop_end = True, 0.0, 2.0
    t1.playing_slot_index = -1
    t1.arrangement_clips = [arr]
    ControlSurface.notes_out[:] = []
    song.is_playing = True
    song.current_song_time = 4.25   # clip pos 0.25 -> note 72
    assert ControlSurface.notes_out == [(0x90, 72, 127)], ControlSurface.notes_out
    song.current_song_time = 7.25   # 3.25 -> loops to 1.25 -> note 74
    assert ControlSurface.notes_out[-2:] == [(0x80, 72, 0), (0x90, 74, 127)], ControlSurface.notes_out
    song.current_song_time = 12.5   # past the clip
    assert ControlSurface.notes_out[-1] == (0x80, 74, 0)
    song.is_playing = False
    s.set_roli_white_keys(1)
    s.disconnect()
    assert ControlSurface.controlled_track is None
    run_device(s)
    for item in list(roli_for_live.SHARED_LIGHTING_ITEMS) + [100, 104]:
        assert DEVICE[item] == original[item], (item, DEVICE[item], original[item])
    assert not os.path.exists(roli_for_live.SNAPSHOT_PATH)
    print('\n'.join(ControlSurface.logs[:12]))
    test_lumi()
    print('ALL TESTS PASSED')


def config_packet(item, value):
    """An unsolicited setConfig from the keyboard, e.g. when the user changes mode."""
    payload = blocks._pack([(0, 32), (0x18, 7), (0, 4), (item, 8), (value & 0xFFFFFFFF, 32)])
    return blocks.BLOCKS_PREFIX + (0x6D,) + tuple(payload) + (blocks._checksum(payload), 0xF7)


def test_lumi():
    """Experimental LUMI lighting/expression with API mode, without track navigation."""
    global SERIAL_REPLY
    SERIAL_REPLY = serial_reply(b'LKB000000000TEST')
    DEVICE.clear()
    DEVICE.update({20: 1, 22: 3, 27: 5, 34: -1002466, 35: -3623796, 36: 100})
    for mode in range(4):
        for offset in range(5):
            DEVICE[100 + 7 * mode + offset] = 0
    original = dict(DEVICE)
    del COMMANDS[:]
    ControlSurface.sent[:] = []
    ControlSurface.logs[:] = []
    song, t1, t2 = make_song()
    ControlSurface.song_instance = song

    s = ROLI_for_Live.create_instance(object())
    tick(s, 60)
    assert any('LUMI Keys (experimental)' in l for l in ControlSurface.logs)
    assert blocks.CMD_BEGIN_API_MODE in COMMANDS and blocks.CMD_PING in COMMANDS, COMMANDS
    assert DEVICE[107] == 1 and DEVICE[111] == 1, 'mode 1 colour type / show scale'
    assert DEVICE[100] == 0 and DEVICE[104] == 0, 'mode 0 untouched'
    assert all(DEVICE[i] == 1 for i in (108, 109, 110)), 'native MPE / bend / pressure default on'
    assert s.get_roli_lighting_state() == 'roli_lighting_v1 1 1', 'new script instances default to white keys'
    assert DEVICE[27] == 0 and DEVICE[22] == 0 and DEVICE[34] == roli_for_live._argb(0xFFFFFF)
    assert DEVICE[35] == roli_for_live._argb(0xFF3B30)

    s.handle_sysex(button_packet(4))
    assert song.view.selected_track is t1, 'buttons are not mapped on LUMI'
    s.set_roli_pitch_bend(0)
    s.set_roli_pressure(0)
    tick(s, 2)
    assert [DEVICE[i] for i in (108, 109, 110)] == [1, 0, 0], 'expression toggles keep MPE on'

    # user switches the LUMI to mode 2: mode 1 gets its settings back, mode 2 is driven instead
    DEVICE[20] = 2
    s.handle_sysex(config_packet(20, 2))
    run_device(s)
    assert DEVICE[107] == 0 and DEVICE[111] == 0, 'mode 1 restored'
    assert all(DEVICE[i] == 0 for i in (108, 109, 110)), 'mode 1 native expression restored'
    tick(s, 60)
    assert DEVICE[114] == 1 and DEVICE[118] == 1, 'mode 2 now driven'
    assert [DEVICE[i] for i in (115, 116, 117)] == [1, 0, 0], 'saved expression follows mode 2'

    s.disconnect()
    run_device(s)
    for item, value in original.items():
        if item != 20:
            assert DEVICE[item] == value, (item, DEVICE[item], value)
    assert not os.path.exists(roli_for_live.SNAPSHOT_PATH)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as directory:
        roli_for_live.SNAPSHOT_PATH = os.path.join(directory, 'snapshot.json')
        roli_for_live.SETTINGS_PATH = os.path.join(directory, 'settings.json')
        main()
