"""Playing-clip scale follows playback, never selection or inferred chord changes."""
import json
import unittest
from unittest.mock import patch

import test_script as fake
from test_script import ControlSurface, DEVICE, roli_for_live, tick
from test_settings import SurfaceTestCase
from ROLI_for_Live.scales import builtin_index


MAJOR = (0, 2, 4, 5, 7, 9, 11)
MINOR = (0, 2, 3, 5, 7, 8, 10)


def clip(root=2, intervals=MINOR, enabled=True):
    result = fake.FakeClip([])
    result.root_note = root
    result.scale_mode = enabled
    result.scale_intervals = intervals
    result.scale_name = 'Minor' if intervals == MINOR else 'Major'
    return result


def arrangement(root, start, end):
    result = clip(root)
    result.start_time, result.end_time = start, end
    result.start_marker = 0.0
    result.muted = False
    return result


class ClipScaleTests(SurfaceTestCase):
    def start(self, playing=None):
        self.playing = playing if playing is not None else clip()
        self.track.clip_slots = [fake.FakeSlot(self.playing)]
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_playing_notes(0)
        surface.set_roli_clip_scale(1)
        self.song.is_playing = True
        tick(surface, 2)
        return surface

    def assert_scale(self, root, intervals, enabled=True):
        self.assertEqual(DEVICE[roli_for_live.KEY], root)
        self.assertEqual(DEVICE[roli_for_live.SCALE], builtin_index(intervals))
        self.assertEqual(DEVICE[104], int(enabled))

    def test_default_keeps_live_scale_even_with_a_playing_clip(self):
        self.track.clip_slots = [fake.FakeSlot(clip())]
        self.song.is_playing = True
        surface, _ = self.create()
        tick(surface, 60)
        self.assertFalse(surface._settings['clip_scale'])
        self.assert_scale(0, MAJOR)
        self.assertEqual(surface.get_roli_controls_state_v4(),
                         'roli_controls_v4 1 1 1 1 0 1 1 live')

    def test_unselected_playing_clip_drives_all_scale_fields_with_notes_off(self):
        selected = clip(9, MAJOR)
        self.song.view.detail_clip = selected
        surface = self.start()
        self.assert_scale(2, MINOR)
        self.assertEqual(surface._scale_source_status, 'clip')
        self.assertEqual(self.song.root_note, 0)
        self.assertEqual(tuple(self.song.scale_intervals), MAJOR)
        self.assertIs(self.song.view.detail_clip, selected)
        self.assertIs(self.song.view.selected_track, self.track)
        self.assertEqual(DEVICE[34], roli_for_live._argb(0xFFFFFF))
        self.assertEqual(DEVICE[35], roli_for_live._argb(self.track.color))
        self.assertEqual(ControlSurface.feedback_channels, [])

    def test_selecting_another_clip_and_changing_global_scale_does_not_override_playback(self):
        surface = self.start()
        self.song.view.detail_clip = clip(9, MAJOR)
        self.song.root_note = 11
        self.song.scale_intervals = MAJOR
        self.song.scale_mode = False
        tick(surface, 2)
        self.assert_scale(2, MINOR)
        self.assertEqual(surface._scale_source_status, 'clip')

    def test_session_handoff_and_scale_edits_update_within_two_display_ticks(self):
        surface = self.start()
        next_clip = clip(7, MAJOR, False)
        self.track.clip_slots.append(fake.FakeSlot(next_clip))
        self.track.playing_slot_index = 1
        tick(surface, 2)
        self.assert_scale(7, MAJOR, False)
        next_clip.root_note = 4
        next_clip.scale_intervals = MINOR
        next_clip.scale_mode = True
        tick(surface, 2)
        self.assert_scale(4, MINOR)
        self.assertEqual(surface._scale_source_status, 'clip')

    def test_stop_falls_back_to_live_then_resume_uses_clip_again(self):
        surface = self.start()
        self.song.root_note = 5
        self.song.is_playing = False
        tick(surface, 2)
        self.assert_scale(5, MAJOR)
        self.assertEqual(surface._scale_source_status, 'idle')
        self.song.is_playing = True
        tick(surface, 2)
        self.assert_scale(2, MINOR)

    def test_empty_session_slot_and_stopped_clip_do_not_use_arrangement_underneath(self):
        surface = self.start()
        self.track.arrangement_clips = [arrangement(9, 0, 8)]
        self.playing.is_playing = False
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.track.clip_slots[0].clip = None
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.assertEqual(surface._scale_source_status, 'idle')

    def test_session_stop_override_suppresses_arrangement_for_scale_and_notes(self):
        surface = self.start()
        arr = arrangement(9, 0, 8)
        arr._note_list = [fake.FakeNote(72, 0, 1)]
        self.track.arrangement_clips = [arr]
        self.track.playing_slot_index = -2
        surface.set_roli_playing_notes(1)
        ControlSurface.notes_out[:] = []
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.assertEqual(ControlSurface.notes_out, [])
        self.assertEqual(surface._scale_source_status, 'idle')

    def test_back_to_arrangement_override_does_not_claim_silent_arrangement_scale(self):
        surface = self.start()
        self.track.playing_slot_index = -1
        self.track.arrangement_clips = [arrangement(9, 0, 8)]
        self.track.back_to_arranger = True
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.track.back_to_arranger = False
        tick(surface, 2)
        self.assert_scale(9, MINOR)

    def test_arrangement_boundaries_handoffs_muted_clips_and_gaps(self):
        surface = self.start()
        self.track.playing_slot_index = -1
        first, second = arrangement(4, 4, 8), arrangement(7, 8, 12)
        self.track.arrangement_clips = [first, second]
        for time, root, intervals in (
                (3.99, 0, MAJOR), (4, 4, MINOR), (7.99, 4, MINOR),
                (8, 7, MINOR), (12, 0, MAJOR), (5, 4, MINOR)):
            self.song.current_song_time = time
            tick(surface, 2)
            self.assert_scale(root, intervals)
        first.muted = True
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        first.muted = False
        first.is_playing = False
        tick(surface, 2)
        self.assert_scale(4, MINOR)

    def test_empty_arrangement_clips_follow_timeline_without_clip_playing_flag(self):
        surface = self.start()
        self.track.playing_slot_index = -1
        first, second = arrangement(2, 0, 16), arrangement(0, 16, 32)
        first.is_playing = second.is_playing = False
        second.scale_intervals, second.scale_name = MAJOR, 'Major'
        self.track.arrangement_clips = [first, second]
        for time, root, intervals, source in (
                (0, 2, MINOR, 'clip'), (15.9, 2, MINOR, 'clip'),
                (16, 0, MAJOR, 'clip'), (31.9, 0, MAJOR, 'clip'),
                (32, 0, MAJOR, 'idle')):
            self.song.current_song_time = time
            tick(surface, 2)
            self.assert_scale(root, intervals)
            self.assertEqual(surface._scale_source_status, source)
        self.song.is_playing = False
        self.song.current_song_time = 8
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.assertEqual(surface._scale_source_status, 'idle')

    def test_session_clip_takes_precedence_over_arrangement(self):
        surface = self.start()
        self.track.arrangement_clips = [arrangement(9, 0, 8)]
        tick(surface, 2)
        self.assert_scale(2, MINOR)

    def test_selected_track_change_uses_new_track_and_non_midi_falls_back(self):
        surface = self.start()
        self.other.has_midi_input = True
        self.other.playing_slot_index = 0
        self.other.clip_slots = [fake.FakeSlot(clip(8, MAJOR))]
        self.song.view.selected_track = self.other
        tick(surface, 2)
        self.assert_scale(8, MAJOR)
        self.other.has_midi_input = False
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.song.view.selected_track = self.song.master_track
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.song.view.selected_track = self.track
        tick(surface, 2)
        self.assert_scale(2, MINOR)

    def test_turning_clip_mode_off_immediately_restores_live_source(self):
        surface = self.start()
        surface.set_roli_clip_scale(0)
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.assertEqual(surface._scale_source_status, 'live')
        self.playing.root_note = 7
        tick(surface, 2)
        self.assert_scale(0, MAJOR)

    def test_scale_lighting_off_restores_native_snapshot_and_preserves_clip_choice(self):
        surface = self.start()
        surface.set_roli_scale_lighting(0)
        self.playing.root_note = 7
        tick(surface, 2)
        self.assert_original_lighting()
        self.assertTrue(surface._settings['clip_scale'])
        self.assertEqual(surface._scale_source_status, 'off')
        surface.set_roli_scale_lighting(1)
        tick(surface, 2)
        self.assert_scale(7, MINOR)

    def test_old_clip_api_falls_back_explicitly_without_repeated_notifications(self):
        surface = self.start(fake.FakeClip([]))
        self.assert_scale(0, MAJOR)
        self.assertEqual(surface._scale_source_status, 'unsupported')
        before = list(ControlSurface.logs)
        tick(surface, 50)
        self.assertEqual(ControlSurface.logs.count(next(
            log for log in before if log.startswith('SHOW:') and 'clip scale unavailable' in log)), 1)
        self.assertTrue(surface._settings['clip_scale'])
        self.track.clip_slots[0].clip = clip(7)
        tick(surface, 2)
        self.assert_scale(7, MINOR)
        self.assertEqual(surface._scale_source_status, 'clip')

    def test_deleted_clip_lookup_falls_back_with_visible_error_and_recovers(self):
        surface = self.start()
        with patch.object(roli_for_live, 'playing_clip', side_effect=RuntimeError('clip deleted')):
            tick(surface, 2)
            self.assert_scale(0, MAJOR)
            self.assertEqual(surface._scale_source_status, 'error')
            self.assertTrue(any('SHOW:' in log and 'clip deleted' in log for log in ControlSurface.logs))
        tick(surface, 2)
        self.assert_scale(2, MINOR)
        self.assertEqual(surface._scale_source_status, 'clip')

    def test_invalid_slot_index_is_a_reported_error_not_a_stale_scale(self):
        surface = self.start()
        self.track.playing_slot_index = 99
        tick(surface, 2)
        self.assert_scale(0, MAJOR)
        self.assertEqual(surface._scale_source_status, 'error')

    def test_invalid_clip_scale_is_not_mixed_with_global_metadata(self):
        surface = self.start()
        for root, intervals in ((12, MINOR), (2, ()), (2, (0, 14)), (True, MINOR)):
            self.playing.root_note, self.playing.scale_intervals = root, intervals
            tick(surface, 2)
            self.assert_scale(0, MAJOR)
            self.assertEqual(surface._scale_source_status, 'error')

    def test_unmapped_clip_scale_keeps_existing_keyboard_limitation(self):
        surface = self.start()
        self.playing.scale_intervals = (0, 1, 4)
        self.playing.scale_name = 'Custom'
        tick(surface, 2)
        self.assertEqual(DEVICE[27], 2)
        self.assertEqual(DEVICE[22], roli_for_live.CHROMATIC)
        self.assertEqual(surface._scale_source_status, 'clip')
        self.assertTrue(any('unsupported scale' in log for log in ControlSurface.logs))

    def test_clip_preference_survives_restart_without_max_and_legacy_bridges_stay_compatible(self):
        surface = self.start()
        self.assertEqual(surface.get_roli_controls_state_v3(), 'roli_controls_v3 1 1 0 1 1 1')
        self.assertEqual(surface.get_roli_controls_state_v4(), 'roli_controls_v4 1 1 0 1 1 1 1 clip')
        surface, _ = self.restart(surface)
        tick(surface, 60)
        self.assert_scale(2, MINOR)
        self.assertTrue(self.read_settings()['clip_scale'])

    def test_v2_settings_migrate_without_resetting_existing_preferences(self):
        legacy = dict(version=2, white_keys=False, scale_lighting=True,
                      playing_notes=False, root_color=False)
        with open(roli_for_live.SETTINGS_PATH, 'w') as file:
            json.dump(legacy, file)
        surface, _ = self.create()
        self.assertEqual(self.read_settings(), legacy)
        self.assertFalse(surface._settings['clip_scale'])
        surface.set_roli_clip_scale(1)
        expected = dict(legacy, version=3, clip_scale=True)
        self.assertEqual(self.read_settings(), expected)

    def test_failed_clip_preference_save_never_changes_runtime_source(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_white_keys(1)
        previous = self.read_settings()
        with patch.object(roli_for_live.os, 'replace', side_effect=PermissionError('save denied')):
            with self.assertRaises(PermissionError):
                surface.set_roli_clip_scale(1)
        self.assertFalse(surface._settings['clip_scale'])
        self.assertEqual(self.read_settings(), previous)

    def test_invalid_clip_preference_values_are_rejected_without_writes(self):
        surface, _ = self.create()
        for value in (None, True, False, 1.0, '1', -1, 2):
            with self.assertRaises(ValueError):
                surface.set_roli_clip_scale(value)
        self.assertFalse(surface._settings['clip_scale'])

    def test_reconnect_reapplies_current_clip_scale_without_replacing_snapshot(self):
        surface = self.start()
        surface.port_settings_changed()
        DEVICE.clear()
        DEVICE.update(self.original)
        self.playing.root_note = 8
        tick(surface, 60)
        self.assertTrue(surface._keyboard_ready())
        self.assert_scale(8, MINOR)
        surface.set_roli_scale_lighting(0)
        tick(surface, 2)
        self.assert_original_lighting()


if __name__ == '__main__':
    unittest.main()
