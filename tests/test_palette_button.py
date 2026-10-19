"""Direct Piano mode-button lighting-state cycling."""
import os
from unittest.mock import patch

import test_script as fake
from test_script import DEVICE, ControlSurface, roli_for_live, tick
from test_settings import SurfaceTestCase


class PaletteButtonTests(SurfaceTestCase):
    def start(self):
        surface, _ = self.create()
        tick(surface, 60)
        return surface

    def press(self, surface):
        surface.handle_sysex(fake.button_packet(0))
        surface.handle_sysex(fake.button_packet(0, down=False))

    def check_cycle(self, surface):
        unchanged = {key: value for key, value in surface._settings.items()
                     if key not in ('key_colors', 'scale_lighting', 'root_color')}
        states = (('white', True, False), ('track', True, True),
                  ('track', True, False), ('rainbow', True, False),
                  ('rainbow', False, False), ('white', True, True))
        for palette, lighting, root in states:
            with patch.object(surface, '_save_settings', wraps=surface._save_settings) as save:
                self.press(surface)
                save.assert_called_once()
            tick(surface, 2)
            for state in (surface._settings, self.read_settings()):
                self.assertEqual((state['key_colors'], state['scale_lighting'], state['root_color']),
                                 (palette, lighting, root))
                self.assertEqual({key: state[key] for key in unchanged}, unchanged)
            self.assertEqual(surface.get_roli_controls_state_v6().split()[-1], palette)
            self.assertEqual(surface.get_roli_controls_state_v3().split()[2], str(int(lighting)))
            self.assertEqual(surface.get_roli_controls_state_v3().split()[4], str(int(root)))
            if not lighting:
                self.assert_original_lighting()

    def test_each_press_cycles_saved_lighting_and_release_does_not_cycle(self):
        surface = self.start()
        self.check_cycle(surface)
        self.press(surface)
        surface, _ = self.restart(surface)
        tick(surface, 60)
        self.assertEqual(surface._settings['key_colors'], 'white')
        self.assertFalse(surface._settings['root_color'])

    def test_mode_transition_keeps_palette_and_expression_choices(self):
        self.check_mode_transition()

    def test_lumi_mode_transition_keeps_palette_and_expression_choices(self):
        fake.SERIAL_REPLY = fake.serial_reply(b'LKB000000000TEST')
        self.check_mode_transition()

    def check_mode_transition(self):
        surface = self.start()
        surface.set_roli_pitch_bend(0)
        surface.set_roli_pressure(1)
        tick(surface, 2)
        self.press(surface)
        DEVICE.update({20: 1, 107: 0, 108: 0, 109: 1, 110: 0, 111: 0})
        surface.handle_sysex(fake.config_packet(20, 1))
        # Another direct press during reinitialization must not be lost.
        for _ in range(3):
            self.press(surface)
        tick(surface, 60)
        self.assertEqual(surface._settings['key_colors'], 'rainbow')
        self.assertEqual([DEVICE[item] for item in (108, 109, 110)], [1, 0, 1])
        self.assertEqual(DEVICE[107], roli_for_live.COLOR_TYPE_RAINBOW)
        surface.disconnect()
        self.surfaces.remove(surface)
        fake.run_device(surface)
        self.assertEqual([DEVICE[item] for item in (108, 109, 110)], [0, 1, 0])
        self.assertEqual(DEVICE[20], 1)

    def test_config_only_mode_change_and_other_buttons_do_not_cycle(self):
        surface = self.start()
        DEVICE[20] = 1
        surface.handle_sysex(fake.config_packet(20, 1))
        tick(surface, 60)
        for button in (1, 2, 3, 4, 5):
            surface.handle_sysex(fake.button_packet(button))
        self.assertEqual(surface._settings['key_colors'], 'white')
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))

    def test_failed_save_is_visible_and_does_not_advance_palette(self):
        surface = self.start()
        surface.set_roli_key_colors(0)
        stored = self.read_settings()
        with patch.object(roli_for_live.os, 'replace', side_effect=PermissionError('denied')):
            self.press(surface)
        self.assertEqual(surface._settings['key_colors'], 'white')
        self.assertEqual(self.read_settings(), stored)
        self.assertEqual(surface._settings, {key: value for key, value in stored.items()
                                             if key != 'version'})
        self.assertTrue(any('SHOW:' in log and 'denied' in log for log in ControlSurface.logs))
        self.press(surface)
        self.assertEqual(surface._settings['key_colors'], 'white')
        self.assertFalse(surface._settings['root_color'])

    def test_lumi_palette_button_without_track_navigation_and_api_release(self):
        fake.SERIAL_REPLY = fake.serial_reply(b'LKB000000000TEST')
        surface = self.start()
        self.check_cycle(surface)
        for button in (1, 2, 3, 4):
            surface.handle_sysex(fake.button_packet(button))
        self.assertIs(self.song.view.selected_track, self.track)
        self.assertEqual(surface._settings['key_colors'], 'white')
        self.assertIn(fake.blocks.CMD_BEGIN_API_MODE, fake.COMMANDS)
        surface.disconnect()
        self.surfaces.remove(surface)
        fake.run_device(surface)
        self.assertEqual(fake.COMMANDS[-1], fake.blocks.CMD_END_API_MODE)

    def test_shutdown_and_scale_lighting_off(self):
        surface = self.start()
        surface.set_roli_scale_lighting(0)
        self.press(surface)
        tick(surface, 2)
        self.assertEqual(surface._settings['key_colors'], 'white')
        self.assertTrue(surface._settings['scale_lighting'])
        self.assertTrue(surface._settings['root_color'])
        surface.disconnect()
        self.surfaces.remove(surface)
        stored = self.read_settings()
        self.press(surface)
        self.assertEqual(self.read_settings(), stored)

    def test_manual_controls_determine_next_step_and_rainbow_preserves_root(self):
        surface = self.start()
        surface.set_roli_key_colors(1)
        surface.set_roli_root_color(0)
        self.press(surface)
        self.assertEqual(surface._settings['key_colors'], 'rainbow')
        self.assertFalse(surface._settings['root_color'])
        surface.set_roli_root_color(1)
        self.press(surface)
        self.assertFalse(surface._settings['scale_lighting'])
        self.assertTrue(surface._settings['root_color'])
        self.press(surface)
        self.assertEqual(surface._settings['key_colors'], 'white')
        self.assertTrue(surface._settings['scale_lighting'])
        self.assertTrue(surface._settings['root_color'])

    def test_full_cycle_preserves_nondefault_independent_preferences(self):
        surface = self.start()
        surface.set_roli_pitch_bend(0)
        surface.set_roli_pressure(0)
        surface.set_roli_playing_notes(0)
        surface.set_roli_clip_scale(1)
        surface.set_roli_global_brightness(42)
        surface.set_roli_background_intensity(17)
        original = dict(surface._settings)
        for _ in range(6):
            self.press(surface)
            tick(surface, 2)
            self.assertEqual([DEVICE[item] for item in (101, 102, 103)], [1, 0, 0])
            self.assertEqual(ControlSurface.feedback_channels, [])
        self.assertEqual(surface._settings, original)

    def test_mode_transition_does_not_restore_shared_lighting_and_applies_within_one_tick(self):
        surface = self.start()
        surface.set_roli_pitch_bend(0)
        surface.set_roli_key_colors(1)
        tick(surface, 2)
        original_shared = {item: surface._snapshot[item]
                           for item in roli_for_live.SHARED_LIGHTING_ITEMS}
        shared_before = {item: DEVICE[item] for item in original_shared}
        DEVICE.update({20: 1, 107: 4, 108: 0, 109: 1, 110: 0, 111: 0})
        # Simulate configuration echoes updating the cache with the active colors.
        for item, value in shared_before.items():
            surface.handle_sysex(fake.config_packet(item, value))
        ControlSurface.sent[:] = []
        surface.handle_sysex(fake.config_packet(20, 1))
        self.assertFalse(surface._keyboard_ready())
        self.assertFalse(any(fake.blocks.config_set(item, original_shared[item]) in ControlSurface.sent
                             for item in original_shared))
        self.assertIn(fake.blocks.config_request(107), ControlSurface.sent)
        self.assertIn(fake.blocks.config_request(108), ControlSurface.sent)
        fake.run_device(surface)
        self.assertEqual({item: DEVICE[item] for item in original_shared}, shared_before)
        tick(surface)
        self.assertTrue(surface._keyboard_ready())
        self.assertEqual(DEVICE[107], roli_for_live.COLOR_TYPE_USER)
        self.assertEqual([DEVICE[item] for item in (108, 109, 110)], [1, 0, 1])
        self.assertEqual({item: surface._snapshot[item] for item in original_shared}, original_shared)
        surface.disconnect()
        self.surfaces.remove(surface)
        fake.run_device(surface)
        self.assertEqual({item: DEVICE[item] for item in original_shared}, original_shared)
        self.assertEqual([DEVICE[item] for item in (107, 108, 109, 110, 111)], [4, 0, 1, 0, 0])

    def test_shutdown_during_mode_initialization_still_restores_shared_settings(self):
        surface = self.start()
        surface.set_roli_global_brightness(42)
        surface.set_roli_key_colors(1)
        tick(surface, 2)
        original = dict(surface._snapshot)
        DEVICE.update({20: 1, 107: 4, 108: 0, 109: 1, 110: 0, 111: 0})
        surface.handle_sysex(fake.config_packet(20, 1))
        surface.disconnect()
        self.surfaces.remove(surface)
        fake.run_device(surface)
        for item, value in original.items():
            self.assertEqual(DEVICE[item], value)
        self.assertEqual([DEVICE[item] for item in (107, 108, 109, 110, 111)], [4, 0, 1, 0, 0])

    def test_reconnect_in_different_mode_keeps_original_shared_recovery_values(self):
        surface = self.start()
        original = {item: surface._snapshot[item]
                    for item in roli_for_live.SHARED_LIGHTING_ITEMS}
        surface.set_roli_key_colors(1)
        tick(surface, 2)
        surface.port_settings_changed()
        DEVICE.update({20: 1, 107: 4, 108: 0, 109: 1, 110: 0, 111: 0})
        tick(surface, 60)
        self.assertEqual({item: surface._snapshot[item] for item in original}, original)
