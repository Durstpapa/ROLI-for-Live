"""Persistence, lighting restoration, and independent note-feedback controls."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import test_script as fake
from test_script import ControlSurface, DEVICE, ROLI_for_Live, blocks, roli_for_live, tick


class FakeInstance(object):
    def set_feedback_velocity(self, value):
        self.velocity = value


class SurfaceTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_paths = roli_for_live.SNAPSHOT_PATH, roli_for_live.SETTINGS_PATH
        roli_for_live.SNAPSHOT_PATH = os.path.join(self.directory.name, 'snapshot.json')
        roli_for_live.SETTINGS_PATH = os.path.join(self.directory.name, 'settings.json')
        fake.SERIAL_REPLY = fake.serial_reply(b'RP4800000000TEST')
        DEVICE.clear()
        DEVICE.update({20: 0, 22: 3, 27: 5, 34: -1002466, 35: -3623796, 36: 100,
                       100: 0, 101: 0, 102: 0, 103: 0, 104: 0})
        self.original = dict(DEVICE)
        ControlSurface.sent[:] = []
        ControlSurface.notes_out[:] = []
        ControlSurface.logs[:] = []
        fake.COMMANDS[:] = []
        self.song, self.track, self.other = fake.make_song()
        ControlSurface.song_instance = self.song
        self.surfaces = []
        self.now = 100.0
        clock = patch.object(roli_for_live.time, 'monotonic', side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def tearDown(self):
        for surface in self.surfaces:
            surface.disconnect()
            fake.run_device(surface)
        roli_for_live.SNAPSHOT_PATH, roli_for_live.SETTINGS_PATH = self.old_paths
        self.directory.cleanup()

    def create(self):
        instance = FakeInstance()
        surface = ROLI_for_Live.create_instance(instance)
        self.surfaces.append(surface)
        return surface, instance

    def restart(self, surface):
        surface.disconnect()
        fake.run_device(surface)
        self.surfaces.remove(surface)
        return self.create()

    def read_settings(self):
        with open(roli_for_live.SETTINGS_PATH) as file:
            return json.load(file)

    def assert_original_lighting(self):
        for item in list(roli_for_live.SHARED_LIGHTING_ITEMS) + [100, 104]:
            self.assertEqual(DEVICE[item], self.original[item], item)


class SettingsTests(SurfaceTestCase):
    def test_v7_reports_global_scale_mode_without_changing_legacy_replies_or_settings(self):
        surface, _ = self.create()
        tick(surface, 60)
        for palette in range(3):
            surface.set_roli_key_colors(palette)
            for follow_clip in (0, 1):
                surface.set_roli_clip_scale(follow_clip)
                for enabled in (True, False, True):
                    self.song.scale_mode = enabled
                    tick(surface, 2)
                    commands = list(fake.COMMANDS)
                    reply = surface.get_roli_controls_state_v7()
                    self.assertEqual(reply,
                                     surface.get_roli_controls_state_v6().replace(
                                         'roli_controls_v6', 'roli_controls_v7', 1) +
                                     ' %d' % int(enabled))
                    self.assertEqual(reply.split()[8], 'idle' if follow_clip else 'live')
                    self.assertEqual(fake.COMMANDS, commands, 'bridge reads must not send MIDI')
        surface.set_roli_scale_lighting(0)
        tick(surface, 2)
        self.assertEqual(surface.get_roli_controls_state_v7().split()[8], 'off')
        self.assertTrue(surface.get_roli_controls_state_v7().endswith(' 0'))

    def test_shutdown_restores_lighting_then_releases_api_without_changing_mode_or_preferences(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_white_keys(0)
        surface.set_roli_background_intensity(25)
        surface.set_roli_global_brightness(40)
        tick(surface, 10)
        surface.set_roli_white_keys(1)
        saved = self.read_settings()
        self.assertTrue(surface._pending)
        ControlSurface.sent[:] = []
        with patch.object(surface, 'release_controlled_track',
                          side_effect=lambda: surface._on_track_selected()):
            surface.disconnect()
        messages = list(ControlSurface.sent)
        self.assertEqual(messages, [
            blocks.config_set(item, value) for item, value in surface._snapshot.items()
        ] + [blocks.device_command(blocks.CMD_END_API_MODE)])
        self.assertEqual(surface._pending, {})
        self.assertEqual(ControlSurface.feedback_channels, [])
        self.assertEqual(instance.velocity, 0)
        self.assertEqual(self.read_settings(), saved)
        fake.run_device(surface)
        self.assert_original_lighting()
        self.assertEqual(DEVICE[20], self.original[20], 'never cycle native playing modes')
        surface.update_display()
        surface._update_lighting()
        surface.handle_sysex(fake.config_packet(20, 1))
        surface.disconnect()
        self.assertEqual(ControlSurface.sent, [], 'no writes or API re-entry after shutdown')
        self.assertFalse(any('restored keyboard lighting' in log for log in ControlSurface.logs))

    def test_shutdown_restores_lumi_then_releases_api_mode(self):
        fake.SERIAL_REPLY = fake.serial_reply(b'LKB000000000TEST')
        surface, instance = self.create()
        tick(surface, 60)
        ControlSurface.sent[:] = []
        surface.disconnect()
        self.assertEqual(ControlSurface.sent, [
            blocks.config_set(item, value) for item, value in surface._snapshot.items()
        ] + [blocks.device_command(blocks.CMD_END_API_MODE)])

    def test_failed_shutdown_restore_send_retains_recovery_snapshot(self):
        surface, instance = self.create()
        tick(surface, 60)
        original_send = surface._send_midi

        def send(message, optimized=True):
            if message == blocks.config_set(roli_for_live.GLOBAL_KEY_COLOUR, self.original[34]):
                return False
            return original_send(message, optimized)

        with patch.object(surface, '_send_midi', side_effect=send):
            surface.disconnect()
        self.assertTrue(os.path.exists(roli_for_live.SNAPSHOT_PATH))
        self.assertTrue(any('restore send failed' in log for log in ControlSurface.logs))
        self.assertIn(blocks.device_command(blocks.CMD_END_API_MODE), ControlSurface.sent)

    def test_failed_api_release_is_logged(self):
        surface, instance = self.create()
        tick(surface, 60)
        original_send = surface._send_midi

        def send(message, optimized=True):
            if message == blocks.device_command(blocks.CMD_END_API_MODE):
                return False
            return original_send(message, optimized)

        with patch.object(surface, '_send_midi', side_effect=send):
            surface.disconnect()
        self.assertTrue(any('could not send end API mode' in log for log in ControlSurface.logs))

    def test_missing_file_uses_explicit_defaults_without_rewriting(self):
        surface, instance = self.create()
        self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 1 1 1 0 1')
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))
        tick(surface, 60)
        self.assertEqual(DEVICE[34], roli_for_live._argb(0xFFFFFF))
        self.assertEqual(instance.velocity, 127)

    def test_all_preferences_survive_restart_without_max_loaded(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_white_keys(0)
        surface.set_roli_scale_lighting(0)
        surface.set_roli_playing_notes(0)
        surface.set_roli_root_color(0)
        tick(surface, 10)
        self.assertEqual(self.read_settings(), dict(
            version=6, key_colors='track', scale_lighting=False, playing_notes=False, root_color=False,
            clip_scale=False, background_intensity=100, global_brightness=None, pitch_bend=True, pressure=True))
        surface, instance = self.restart(surface)
        tick(surface, 60)
        self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 0 0 0 1 1')
        self.assertEqual(surface.get_roli_controls_state_v3(), 'roli_controls_v3 0 0 0 0 1 1')
        self.assert_original_lighting()
        self.assertEqual(ControlSurface.feedback_channels, [])
        self.assertEqual(instance.velocity, 0)
        for setter in (surface.set_roli_white_keys, surface.set_roli_scale_lighting,
                       surface.set_roli_playing_notes, surface.set_roli_root_color,
                       surface.set_roli_clip_scale):
            setter(1)
        surface, instance = self.restart(surface)
        tick(surface, 60)
        self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 1 1 1 1 1')
        self.assertEqual(surface.get_roli_controls_state_v3(), 'roli_controls_v3 1 1 1 1 1 1')
        self.assertEqual(DEVICE[34], roli_for_live._argb(0xFFFFFF))

    def test_power_off_expires_readiness_without_discarding_saved_preferences(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_white_keys(0)
        surface.set_roli_root_color(0)
        tick(surface, 10)
        saved = self.read_settings()
        with open(roli_for_live.SNAPSHOT_PATH) as file:
            snapshot = json.load(file)
        last_response = surface._last_response
        for step in range(1, 51):
            self.now = last_response + step / 10.0
            surface.update_display()
            ControlSurface.sent[:] = []  # unplugged: no serial/config/ACK replies
        self.assertTrue(surface._keyboard_ready(), 'expire only after the response deadline')
        surface._last_ack = surface._ticks  # a retry timestamp is not a device reply
        self.now += 0.001
        surface.update_display()
        ControlSurface.sent[:] = []
        self.assertEqual(surface.get_roli_lighting_state(), 'roli_lighting_v1 0 0')
        self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 0 1 1 0 1')
        self.assertEqual(surface.get_roli_controls_state_v3(), 'roli_controls_v3 0 1 1 0 0 1')
        self.assertEqual(self.read_settings(), saved)
        self.assertEqual(surface._pending, {})
        self.assertEqual(surface._sent, {})
        for _ in range(120):
            surface.update_display()
            ControlSurface.sent[:] = []
        self.assertFalse(surface._keyboard_ready())
        self.assertEqual(sum('stopped responding' in log for log in ControlSurface.logs), 1)
        DEVICE.clear()
        DEVICE.update(self.original)
        tick(surface, 60)
        self.assertTrue(surface._keyboard_ready())
        self.assertEqual(DEVICE[34], roli_for_live._argb(self.track.color))
        self.assertEqual(DEVICE[35], DEVICE[34])
        self.assertEqual(self.read_settings(), saved)
        with open(roli_for_live.SNAPSHOT_PATH) as file:
            self.assertEqual(json.load(file), snapshot, 'retain pre-script lighting across reconnect')
        surface.set_roli_scale_lighting(0)
        tick(surface, 10)
        self.assert_original_lighting()

    def test_config_heartbeat_keeps_non_api_keyboard_connected(self):
        fake.SERIAL_REPLY = fake.serial_reply(b'LKB800000000TEST')
        surface, instance = self.create()
        non_api = dict(roli_for_live.PROFILES['LKB'], api_mode=False)
        with patch.dict(roli_for_live.PROFILES, {'LKB': non_api}):
            for _ in range(240):
                self.now += 0.1
                tick(surface)
        self.assertTrue(surface._keyboard_ready())
        self.assertFalse(surface._profile['api_mode'])
        self.assertEqual(fake.COMMANDS, [])
        self.assertLessEqual(self.now - surface._last_response, 2.01)

    def test_readiness_expires_in_real_time_even_if_live_stops_display_callbacks(self):
        surface, instance = self.create()
        tick(surface, 60)
        frozen_ticks = surface._ticks
        last_response = surface._last_response
        self.now = last_response + roli_for_live.DEVICE_RESPONSE_TIMEOUT_SECONDS
        self.assertTrue(surface._keyboard_ready())
        self.now += 0.001
        self.assertEqual(surface.get_roli_lighting_state(), 'roli_lighting_v1 1 0')
        self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 1 1 1 0 1')
        self.assertEqual(surface.get_roli_controls_state_v3(), 'roli_controls_v3 1 1 1 1 0 1')
        self.assertEqual(surface._ticks, frozen_ticks)
        self.assertIsNotNone(surface._serial, 'getters must expire status without needing an update')
        surface.update_display()
        self.assertIsNone(surface._serial)
        tick(surface, 60)
        self.assertTrue(surface._keyboard_ready())

    def test_port_reset_discards_stale_handshake_and_pending_writes(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_white_keys(0)
        self.assertTrue(surface._pending)
        surface.port_settings_changed()
        self.assertFalse(surface._keyboard_ready())
        self.assertIsNone(surface._snapshot)
        self.assertEqual(surface._pending, {})
        tick(surface, 60)
        self.assertTrue(surface._keyboard_ready())
        self.assertEqual(DEVICE[34], roli_for_live._argb(self.track.color))

    def test_invalid_files_report_failure_preserve_file_and_allow_recovery(self):
        cases = ['{broken', '[]', '{"version": 2}', json.dumps(dict(
            version=True, white_keys=True, scale_lighting=True, playing_notes=True)),
            json.dumps(dict(version=1, white_keys=1, scale_lighting=True, playing_notes=True)),
            json.dumps(dict(version=2, white_keys=True, scale_lighting=True, playing_notes=True,
                            root_color=1))]
        for contents in cases:
            with self.subTest(contents=contents):
                with open(roli_for_live.SETTINGS_PATH, 'w') as file:
                    file.write(contents)
                surface, instance = self.create()
                self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 1 1 1 0 0')
                self.assertTrue(any('could not read settings' in log for log in ControlSurface.logs))
                with open(roli_for_live.SETTINGS_PATH) as file:
                    self.assertEqual(file.read(), contents)
                surface.set_roli_white_keys(0)
                self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 0 1 1 0 1')
                self.assertEqual(self.read_settings()['key_colors'], 'track')
                surface.disconnect()
                self.surfaces.remove(surface)

    def test_read_permission_failure_is_visible(self):
        with patch('builtins.open', side_effect=PermissionError('read denied')):
            surface, instance = self.create()
        self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 1 1 1 0 0')
        self.assertTrue(any('SHOW:' in log and 'read denied' in log for log in ControlSurface.logs))

    def test_failed_atomic_save_keeps_previous_file_and_runtime_state(self):
        surface, instance = self.create()
        surface.set_roli_white_keys(1)
        before = self.read_settings()
        with patch.object(roli_for_live.os, 'replace', side_effect=PermissionError('save denied')):
            with self.assertRaises(PermissionError):
                surface.set_roli_white_keys(0)
        self.assertEqual(self.read_settings(), before)
        self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 1 1 1 0 0')
        self.assertFalse(any(name.startswith('.roli-settings-') for name in os.listdir(self.directory.name)))
        self.assertTrue(any('SHOW:' in log and 'save denied' in log for log in ControlSurface.logs))
        surface.set_roli_white_keys(0)
        self.assertEqual(surface.get_roli_controls_state(), 'roli_controls_v2 0 1 1 0 1')

    def test_save_creation_failure_cannot_apply_unpersisted_values(self):
        surface, instance = self.create()
        with patch.object(roli_for_live.tempfile, 'mkstemp', side_effect=PermissionError('directory denied')):
            with self.assertRaises(PermissionError):
                surface.set_roli_scale_lighting(0)
        self.assertTrue(surface._settings['scale_lighting'])
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))

    def test_invalid_values_never_create_a_settings_file(self):
        surface, instance = self.create()
        for setter in (surface.set_roli_white_keys, surface.set_roli_scale_lighting,
                       surface.set_roli_playing_notes, surface.set_roli_root_color):
            for value in (None, True, 1.0, '1', -1, 2):
                with self.assertRaises(ValueError):
                    setter(value)
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))

    def test_scale_off_restores_snapshot_and_ignores_live_changes(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_scale_lighting(0)
        tick(surface, 10)
        self.assert_original_lighting()
        self.assertTrue(os.path.exists(roli_for_live.SNAPSHOT_PATH), 'keep crash recovery snapshot')
        self.song.root_note = 7
        self.track.color = 0x00FF00
        self.song.scale_mode = False
        tick(surface, 10)
        self.assert_original_lighting()
        self.assertEqual(DEVICE[102], 1, 'lighting switch must not undo expression')
        self.assertEqual(ControlSurface.feedback_channels, [0], 'note feedback remains independent')
        surface.handle_sysex(fake.button_packet(4))
        self.assertIs(self.song.view.selected_track, self.other, 'navigation remains active')
        surface.set_roli_scale_lighting(1)
        tick(surface, 10)
        self.assertEqual(DEVICE[27], 7)
        self.assertEqual(DEVICE[104], 0, 'Live scale mode still applies after re-enabling')
        self.assertEqual(DEVICE[34], roli_for_live._argb(0xFFFFFF))
        self.assertEqual(DEVICE[35], roli_for_live._argb(roli_for_live._visible(self.other.color)))

    def test_rapid_scale_toggles_cancel_queued_lighting(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_scale_lighting(0)
        surface.set_roli_scale_lighting(1)
        tick(surface, 10)
        self.assertEqual(DEVICE[34], roli_for_live._argb(0xFFFFFF))
        surface.set_roli_scale_lighting(0)
        tick(surface, 10)
        surface.set_roli_scale_lighting(1)
        surface.set_roli_scale_lighting(0)
        tick(surface, 10)
        self.assert_original_lighting()

    def test_scale_off_before_initialization_never_replaces_original_lighting(self):
        surface, instance = self.create()
        surface.set_roli_scale_lighting(0)
        tick(surface, 60)
        self.assert_original_lighting()
        self.assertEqual(DEVICE[102], 1)

    def test_playing_notes_off_clears_both_feedback_paths_without_changing_input_routing(self):
        surface, instance = self.create()
        tick(surface, 60)
        ControlSurface.notes_out[:] = []
        self.song.is_playing = True
        self.track.clip.playing_position = 0.25
        self.song.current_song_time = 0.25
        self.assertIn((0x90, 60, 127), ControlSurface.notes_out)
        surface.set_roli_playing_notes(0)
        self.assertEqual(ControlSurface.notes_out[-128:], [(0x80, pitch, 0) for pitch in range(128)])
        self.assertEqual(ControlSurface.feedback_channels, [])
        self.assertEqual(instance.velocity, 0)
        self.assertIs(ControlSurface.controlled_track, self.track)
        self.assertEqual(self.track.clip._listeners.get('notes'), [])
        ControlSurface.notes_out[:] = []
        self.track.clip.playing_position = 0.75
        self.song.current_song_time = 0.75
        tick(surface, 5)
        self.assertEqual(ControlSurface.notes_out, [])
        surface.set_roli_playing_notes(1)
        tick(surface, 1)
        self.assertEqual(ControlSurface.feedback_channels, [0])
        self.assertEqual(instance.velocity, 127)
        self.assertEqual(ControlSurface.notes_out, [(0x90, 60, 127), (0x90, 64, 127)])

    def test_scale_off_keeps_playing_notes_and_color_choice_is_saved_for_reenable(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_scale_lighting(0)
        surface.set_roli_white_keys(0)
        tick(surface, 10)
        self.assert_original_lighting()
        ControlSurface.notes_out[:] = []
        self.song.is_playing = True
        self.song.current_song_time = 0.25
        self.track.clip.playing_position = 0.25
        tick(surface, 1)
        self.assertIn((0x90, 60, 127), ControlSurface.notes_out)
        surface.set_roli_scale_lighting(1)
        tick(surface, 10)
        self.assertEqual(DEVICE[34], roli_for_live._argb(self.track.color))

    def test_scale_off_survives_keyboard_mode_change_without_undoing_expression(self):
        fake.SERIAL_REPLY = fake.serial_reply(b'LKB000000000TEST')
        DEVICE[20] = 1
        for mode in range(4):
            for offset in range(5):
                DEVICE[100 + 7 * mode + offset] = 0
        surface, instance = self.create()
        surface.set_roli_scale_lighting(0)
        tick(surface, 60)
        self.assertEqual(DEVICE[107], 0)
        self.assertEqual(DEVICE[111], 0)
        DEVICE[20] = 2
        surface.handle_sysex(fake.config_packet(20, 2))
        fake.run_device(surface)
        tick(surface, 60)
        self.assertEqual(DEVICE[114], 0)
        self.assertEqual(DEVICE[118], 0)
        self.assertEqual(DEVICE[34], self.original[34])
        self.assertEqual(DEVICE[35], self.original[35])
        self.assertTrue(all(DEVICE[100 + 7 * mode + offset] == int(mode == 2)
                            for mode in range(4) for offset in (1, 2, 3)))
        surface.set_roli_scale_lighting(1)
        tick(surface, 10)
        self.assertEqual(DEVICE[114], 1)
        self.assertEqual(DEVICE[118], 1)
        self.assertEqual([DEVICE[115], DEVICE[116], DEVICE[117]], [1, 1, 1])

    def test_legacy_settings_migrate_without_resetting_other_choices(self):
        legacy = dict(version=1, white_keys=False, scale_lighting=False, playing_notes=False)
        with open(roli_for_live.SETTINGS_PATH, 'w') as file:
            json.dump(legacy, file)
        surface, instance = self.create()
        self.assertEqual(surface.get_roli_controls_state_v3(), 'roli_controls_v3 0 0 0 1 0 1')
        self.assertEqual(self.read_settings(), legacy, 'loading must not rewrite the old file')
        surface.set_roli_root_color(0)
        self.assertEqual(self.read_settings(), dict(
            version=6, key_colors='track', scale_lighting=False, playing_notes=False, root_color=False,
            clip_scale=False, background_intensity=100, global_brightness=None, pitch_bend=True, pressure=True))
        surface, instance = self.restart(surface)
        self.assertEqual(surface.get_roli_controls_state_v3(), 'roli_controls_v3 0 0 0 0 0 1')

    def test_root_color_off_matches_other_keys_in_both_palettes(self):
        surface, instance = self.create()
        tick(surface, 60)
        for white in (1, 0):
            surface.set_roli_white_keys(white)
            surface.set_roli_root_color(0)
            tick(surface, 10)
            expected = roli_for_live._argb(0xFFFFFF if white else self.track.color)
            self.assertEqual(DEVICE[34], expected)
            self.assertEqual(DEVICE[35], expected, 'roots must not go dark or retain a special color')
            self.song.root_note = 7
            self.track.color = 0x123456
            tick(surface, 10)
            color = roli_for_live._visible(self.track.color)
            expected = roli_for_live._argb(0xFFFFFF if white else color)
            self.assertEqual(DEVICE[34], expected)
            self.assertEqual(DEVICE[35], expected)
            surface.set_roli_root_color(1)
            tick(surface, 10)
            self.assertEqual(DEVICE[35], roli_for_live._argb(color if white else roli_for_live._brighter(color)))
            self.assertEqual(DEVICE[34], expected)
            self.track.color = 0xFF3B30

    def test_root_color_off_is_restored_at_startup_without_max(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_root_color(0)
        surface, instance = self.restart(surface)
        tick(surface, 60)
        self.assertEqual(surface.get_roli_controls_state_v3(), 'roli_controls_v3 1 1 1 0 1 1')
        self.assertEqual(DEVICE[34], roli_for_live._argb(0xFFFFFF))
        self.assertEqual(DEVICE[35], DEVICE[34])

    def test_root_setting_does_not_override_native_lighting_when_scale_lighting_is_off(self):
        surface, instance = self.create()
        tick(surface, 60)
        surface.set_roli_root_color(0)
        surface.set_roli_scale_lighting(0)
        tick(surface, 10)
        self.assert_original_lighting()
        surface.set_roli_scale_lighting(1)
        tick(surface, 10)
        self.assertEqual(DEVICE[34], DEVICE[35])

    def test_root_color_failed_save_and_rapid_clicks_preserve_correct_state(self):
        surface, instance = self.create()
        tick(surface, 60)
        original_root = DEVICE[35]
        with patch.object(roli_for_live.os, 'replace', side_effect=PermissionError('root save denied')):
            with self.assertRaises(PermissionError):
                surface.set_roli_root_color(0)
        self.assertTrue(surface._settings['root_color'])
        self.assertEqual(DEVICE[35], original_root)
        surface.set_roli_root_color(0)
        surface.set_roli_root_color(1)
        tick(surface, 10)
        self.assertEqual(DEVICE[35], original_root)


class RainbowTests(SurfaceTestCase):
    def test_global_scale_mode_off_uses_chromatic_in_all_palettes_and_restores_selected_scale(self):
        surface, _ = self.create()
        tick(surface, 60)
        self.song.root_note = 2
        self.song.scale_name = 'Minor'
        self.song.scale_intervals = [0, 2, 3, 5, 7, 8, 10]
        for palette in range(3):
            with self.subTest(palette=palette):
                surface.set_roli_key_colors(palette)
                self.song.scale_mode = True
                tick(surface, 2)
                self.assertEqual(DEVICE[22], 1)
                self.assertEqual(DEVICE[104], 1)
                self.song.scale_mode = False
                tick(surface, 2)
                self.assertEqual(DEVICE[22], 18, 'all notes must be in the native mask when disabled')
                self.assertEqual(DEVICE[104], 0)
                self.assertEqual(DEVICE[27], 2)
                self.assertEqual(DEVICE[100], 4 if palette == 2 else 1)
                self.assertEqual(self.song.scale_intervals, [0, 2, 3, 5, 7, 8, 10])
                self.song.scale_mode = True
                tick(surface, 2)
                self.assertEqual(DEVICE[22], 1)
                self.assertEqual(DEVICE[104], 1)

    def test_scale_mode_off_does_not_warn_about_an_unused_unsupported_scale(self):
        surface, _ = self.create()
        tick(surface, 60)
        self.song.scale_mode = False
        self.song.scale_intervals = [0, 1, 4, 5, 7, 8, 10]
        self.song.scale_name = 'Phrygian Dominant'
        tick(surface, 2)
        self.assertEqual(DEVICE[22], 18)
        self.assertFalse(any('unsupported scale' in log for log in ControlSurface.logs))

    def test_rainbow_scheme_matches_dashboard_hardware_readback(self):
        self.assertEqual(roli_for_live.COLOR_TYPE_RAINBOW, 4)
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_key_colors(2)
        tick(surface, 2)
        self.assertEqual(DEVICE[100], 4, 'scheme 3 is not the scale-aware Rainbow scheme')
        self.assertEqual(DEVICE[104], 1)

    def test_version_four_color_preferences_migrate_to_named_palettes_without_resetting_levels(self):
        for white in (True, False):
            stored = dict(version=4, white_keys=white, scale_lighting=True, playing_notes=False,
                          root_color=False, clip_scale=True, background_intensity=25, global_brightness=61)
            with open(roli_for_live.SETTINGS_PATH, 'w') as file:
                json.dump(stored, file)
            surface, _ = self.create()
            self.assertEqual(self.read_settings(), stored, 'loading must not rewrite preferences')
            self.assertEqual(surface._settings['key_colors'], 'white' if white else 'track')
            surface.set_roli_key_colors(2)
            expected = dict(stored, version=6, key_colors='rainbow', pitch_bend=True, pressure=True)
            del expected['white_keys']
            self.assertEqual(self.read_settings(), expected)
            surface.disconnect()
            self.surfaces.remove(surface)

    def test_rainbow_uses_native_colors_without_changing_playing_mode_on_both_profiles(self):
        for serial in (b'RP4800000000TEST', b'LKB000000000TEST'):
            with self.subTest(serial=serial):
                fake.SERIAL_REPLY = fake.serial_reply(serial)
                surface, instance = self.create()
                tick(surface, 60)
                surface.set_roli_clip_scale(1)
                surface.set_roli_root_color(0)
                surface.set_roli_background_intensity(25)
                surface.set_roli_global_brightness(60)
                surface.set_roli_key_colors(2)
                tick(surface, 5)
                self.assertEqual(DEVICE[100], roli_for_live.COLOR_TYPE_RAINBOW)
                self.assertEqual(DEVICE[104], 1, 'Rainbow retains scale highlighting')
                self.assertEqual(DEVICE[20], self.original[20], 'native playing mode is unchanged')
                for item in (34, 35):
                    self.assertEqual(DEVICE[item], self.original[item], 'restore native shared colors')
                self.assertEqual(DEVICE[27], self.song.root_note)
                self.assertEqual(DEVICE[36], 60)
                self.assertEqual(instance.velocity, 127)
                self.assertEqual(ControlSurface.feedback_channels, [0])
                self.assertTrue(surface._settings['clip_scale'])
                self.assertFalse(surface._settings['root_color'])
                self.assertEqual(surface._settings['background_intensity'], 25)
                self.assertTrue(surface.get_roli_controls_state_v6().endswith('60 25 rainbow'))
                self.song.root_note = 9
                self.track.color = 0x123456
                tick(surface, 5)
                self.assertEqual(DEVICE[100], roli_for_live.COLOR_TYPE_RAINBOW)
                self.assertEqual(DEVICE[27], 9)
                self.song.scale_mode = False
                tick(surface, 5)
                self.assertEqual(DEVICE[104], 0, 'Live scale mode off shows the full rainbow')
                self.song.scale_mode = True
                self.song.is_playing = True
                self.song.current_song_time = 0.25
                self.assertIn((0x90, 60, 127), ControlSurface.notes_out)
                surface.disconnect()
                fake.run_device(surface)
                self.assert_original_lighting()
                self.surfaces.remove(surface)

    def test_leaving_rainbow_reapplies_saved_scale_root_and_background_preferences(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_root_color(0)
        surface.set_roli_background_intensity(25)
        surface.set_roli_key_colors(2)
        tick(surface, 2)
        surface.set_roli_key_colors(1)
        tick(surface, 2)
        expected = roli_for_live._argb(roli_for_live._dim(self.track.color, 0.25))
        self.assertEqual(DEVICE[100], roli_for_live.COLOR_TYPE_USER)
        self.assertEqual(DEVICE[104], 1)
        self.assertEqual(DEVICE[34], expected)
        self.assertEqual(DEVICE[35], expected)
        self.assertEqual(DEVICE[27], self.song.root_note)

    def test_rainbow_survives_restart_reconnect_and_scale_off_without_rewriting_preferences(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_key_colors(2)
        saved = self.read_settings()
        surface, _ = self.restart(surface)
        tick(surface, 60)
        self.assertEqual(self.read_settings(), saved)
        self.assertEqual(DEVICE[100], roli_for_live.COLOR_TYPE_RAINBOW)
        surface.port_settings_changed()
        tick(surface, 60)
        self.assertEqual(DEVICE[100], roli_for_live.COLOR_TYPE_RAINBOW)
        surface.set_roli_scale_lighting(0)
        tick(surface, 2)
        self.assert_original_lighting()
        self.assertEqual(surface._settings['key_colors'], 'rainbow')
        surface.set_roli_scale_lighting(1)
        tick(surface, 2)
        self.assertEqual(DEVICE[100], roli_for_live.COLOR_TYPE_RAINBOW)

    def test_failed_color_save_preserves_previous_palette_and_pending_writes(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_key_colors(1)
        tick(surface, 2)
        saved = self.read_settings()
        with patch.object(roli_for_live.os, 'replace', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                surface.set_roli_key_colors(2)
        self.assertEqual(self.read_settings(), saved)
        self.assertEqual(surface._settings['key_colors'], 'track')
        self.assertEqual(surface._pending, {})

    def test_invalid_color_values_fail_explicitly_and_legacy_setter_still_selects_white_or_track(self):
        surface, _ = self.create()
        for value in (-1, 3, 1.0, True, False, 'rainbow', None):
            with self.assertRaises(ValueError):
                surface.set_roli_key_colors(value)
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))
        for legacy, expected in ((1, 'white'), (0, 'track')):
            surface.set_roli_key_colors(2)
            surface.set_roli_white_keys(legacy)
            self.assertEqual(surface._settings['key_colors'], expected)
            self.assertEqual(surface.get_roli_lighting_state(), 'roli_lighting_v1 %d 0' % legacy)

    def test_invalid_saved_color_reports_error_and_preserves_file(self):
        for value in ('invalid', 2, None, True, []):
            with self.subTest(value=value):
                stored = dict(roli_for_live.DEFAULT_SETTINGS, version=6, key_colors=value)
                with open(roli_for_live.SETTINGS_PATH, 'w') as file:
                    json.dump(stored, file)
                surface, _ = self.create()
                self.assertTrue(surface._settings_error)
                self.assertEqual(surface._settings['key_colors'], 'white')
                self.assertEqual(self.read_settings(), stored)
                surface.disconnect()
                self.surfaces.remove(surface)


if __name__ == '__main__':
    unittest.main()
