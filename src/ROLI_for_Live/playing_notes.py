"""Lights the keys for notes that the selected track's playing clip is sounding right now.

Reads the clip's notes once (re-reading when they change) and, as the play position moves,
sends note-on/off to the keyboard on MIDI ch 1. The keyboard lights a key white for each note
it receives and never sends notes on ch 1 itself, so nothing loops back into Live.
"""

NOTE_ON = 0x90
NOTE_OFF = 0x80
VELOCITY = 127


def _note_tuples(clip):
    """Return [(pitch, start, end)] for the clip's unmuted notes."""
    out = []
    if hasattr(clip, 'get_notes_extended'):
        for n in clip.get_notes_extended(0, 128, -100000.0, 1000000.0):
            if not getattr(n, 'mute', False):
                out.append((int(n.pitch), float(n.start_time), float(n.start_time) + float(n.duration)))
    else:
        for pitch, start, dur, _vel, mute in clip.get_notes(-100000.0, 0, 1000000.0, 128):
            if not mute:
                out.append((int(pitch), float(start), float(start) + float(dur)))
    return out


def _arrangement_position(clip, song_time):
    """Clip-time position of an arrangement clip at the given song time, following its loop."""
    pos = float(clip.start_marker) + (song_time - float(clip.start_time))
    if getattr(clip, 'looping', False):
        loop_start, loop_end = float(clip.loop_start), float(clip.loop_end)
        if loop_end > loop_start and pos >= loop_end:
            pos = loop_start + (pos - loop_start) % (loop_end - loop_start)
    return pos


class PlayingNotes(object):

    def __init__(self, send_midi, log):
        self._send_midi = send_midi
        self._log = log
        self._track = None
        self._clip = None
        self._notes = []
        self._notes_cb = None
        self._lit = set()
        self._enabled = True

    def set_enabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            self.disconnect()

    def set_track(self, track):
        if track != self._track:
            self._track = track
            self._set_clip(None)
            self.clear()

    def disconnect(self):
        self._set_clip(None)
        self.clear()

    def clear(self):
        for pitch in sorted(self._lit):
            self._send_midi((NOTE_OFF, pitch, 0))
        self._lit = set()

    def update(self, song):
        if not self._enabled:
            return
        clip, pos = self._playing_clip(song)
        if clip != self._clip:  # Live returns a fresh wrapper per access; compare by value
            self._set_clip(clip)
        if clip is None:
            self.clear()
            return
        sounding = set(p for p, start, end in self._notes if start <= pos < end and 0 <= p < 128)
        for pitch in sorted(self._lit - sounding):
            self._send_midi((NOTE_OFF, pitch, 0))
        for pitch in sorted(sounding - self._lit):
            self._send_midi((NOTE_ON, pitch, VELOCITY))
        self._lit = sounding

    def _playing_clip(self, song):
        """Return (clip, position in clip beats) for the selected track, or (None, None)."""
        track = self._track
        if track is None or not getattr(song, 'is_playing', False):
            return None, None
        try:
            if not getattr(track, 'has_midi_input', False):
                return None, None
            index = track.playing_slot_index
            if index is not None and index >= 0:
                clip = track.clip_slots[index].clip
                if clip is not None:
                    return clip, float(clip.playing_position)
            t = float(song.current_song_time)
            for clip in getattr(track, 'arrangement_clips', ()):
                if clip.start_time <= t < clip.end_time and not getattr(clip, 'muted', False):
                    return clip, _arrangement_position(clip, t)
        except Exception as e:
            self._log('ROLI for Live: playing-notes lookup failed: %s' % e)
        return None, None

    def _set_clip(self, clip):
        old = self._clip
        if old is not None and self._notes_cb is not None:
            try:
                if old.notes_has_listener(self._notes_cb):
                    old.remove_notes_listener(self._notes_cb)
            except Exception:
                pass  # clip was deleted
        self._clip = clip
        self._notes_cb = None
        self._notes = []
        if clip is not None:
            self._reload_notes()
            self._log('ROLI for Live: lighting notes of playing clip %r (%d notes)'
                      % (getattr(clip, 'name', ''), len(self._notes)))
            if hasattr(clip, 'add_notes_listener'):
                self._notes_cb = lambda: self._reload_notes()
                clip.add_notes_listener(self._notes_cb)

    def _reload_notes(self):
        try:
            self._notes = _note_tuples(self._clip)
        except Exception as e:
            self._notes = []
            self._log('ROLI for Live: could not read clip notes: %s' % e)
