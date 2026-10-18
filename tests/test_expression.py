"""Independent native expression controls, persistence and restoration."""
import json
import os
from unittest.mock import patch

import test_script as fake
from test_script import ControlSurface, DEVICE, roli_for_live, tick
from test_settings import SurfaceTestCase


class ExpressionTests(SurfaceTestCase):
    def start(self):
        surface, _ = self.create()
        tick(surface, 60)
        return surface

    def test_defaults_preserve_native_mpe_expression_and_legacy_bridge_replies(self):
        surface = self.start()
        self.assertEqual([DEVICE[item] for item in (101, 102, 103)], [1, 1, 1])
        self.assertEqual(surface.get_roli_controls_state_v8(),
                         surface.get_roli_controls_state_v7().replace(
                             'roli_controls_v7', 'roli_controls_v8', 1) + ' 1 1 1')
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))

    def test_switches_are_independent_of_each_other_lighting_and_palette(self):
        surface = self.start()
        for palette in range(3):
            surface.set_roli_key_colors(palette)
            for lighting in (0, 1):
                surface.set_roli_scale_lighting(lighting)
                for pitch, pressure in ((0, 1), (1, 0), (0, 0), (1, 1)):
                    surface.set_roli_pitch_bend(pitch)
                    surface.set_roli_pressure(pressure)
                    tick(surface, 2)
                    self.assertEqual([DEVICE[item] for item in (101, 102, 103)],
                                     [1, pitch, pressure])
                    self.assertTrue(surface.get_roli_controls_state_v8().endswith(
                        ' %d %d 1' % (pitch, pressure)))
        self.assertEqual(ControlSurface.feedback_channels, [0])

    def test_rapid_changes_cancel_stale_pending_expression_writes(self):
        surface = self.start()
        for setter in (surface.set_roli_pitch_bend, surface.set_roli_pressure):
            setter(0)
            setter(1)
        tick(surface, 2)
        self.assertEqual((DEVICE[102], DEVICE[103]), (1, 1))
        for setter in (surface.set_roli_pitch_bend, surface.set_roli_pressure):
            setter(0)
            setter(1)
            setter(0)
        tick(surface, 2)
        self.assertEqual((DEVICE[102], DEVICE[103]), (0, 0))

    def test_preferences_survive_restart_and_native_values_are_restored_on_exit(self):
        surface = self.start()
        surface.set_roli_pitch_bend(0)
        surface.set_roli_pressure(0)
        tick(surface, 2)
        stored = self.read_settings()
        self.assertEqual(stored['version'], 6)
        self.assertFalse(stored['pitch_bend'])
        self.assertFalse(stored['pressure'])
        surface, _ = self.restart(surface)
        tick(surface, 60)
        self.assertEqual([DEVICE[item] for item in (101, 102, 103)], [1, 0, 0])
        surface.disconnect()
        self.surfaces.remove(surface)
        fake.run_device(surface)
        self.assertEqual([DEVICE[item] for item in (101, 102, 103)], [0, 0, 0])
        self.assertEqual(self.read_settings(), stored)

    def test_reconnection_reapplies_preferences_without_replacing_original_snapshot(self):
        surface = self.start()
        surface.set_roli_pressure(0)
        tick(surface, 2)
        snapshot = dict(surface._snapshot)
        surface.port_settings_changed()
        DEVICE[102], DEVICE[103] = 0, 1
        tick(surface, 60)
        self.assertEqual((DEVICE[102], DEVICE[103]), (1, 0))
        self.assertEqual(surface._snapshot, snapshot)

    def test_mode_change_restores_old_mode_then_captures_and_restores_new_mode(self):
        surface = self.start()
        surface.set_roli_pitch_bend(0)
        surface.set_roli_pressure(0)
        tick(surface, 2)
        DEVICE.update({20: 1, 107: 0, 108: 0, 109: 1, 110: 0, 111: 0})
        surface.handle_sysex(fake.config_packet(20, 1))
        tick(surface, 60)
        self.assertEqual([DEVICE[item] for item in (101, 102, 103)], [0, 0, 0])
        self.assertEqual([DEVICE[item] for item in (108, 109, 110)], [1, 0, 0])
        surface.disconnect()
        self.surfaces.remove(surface)
        fake.run_device(surface)
        self.assertEqual([DEVICE[item] for item in (108, 109, 110)], [0, 1, 0])
        self.assertEqual(DEVICE[20], 1, 'never change the native playing mode')

    def test_invalid_inputs_and_failed_saves_cannot_change_expression(self):
        surface = self.start()
        surface.set_roli_pitch_bend(1)
        tick(surface, 2)
        stored = self.read_settings()
        for setter in (surface.set_roli_pitch_bend, surface.set_roli_pressure):
            for invalid in (-1, 2, 1.0, True, False, '0', None):
                with self.assertRaises(ValueError):
                    setter(invalid)
            with patch.object(roli_for_live.os, 'replace', side_effect=PermissionError('denied')):
                with self.assertRaises(PermissionError):
                    setter(0)
            self.assertEqual(surface._pending, {})
            self.assertEqual(self.read_settings(), stored)
            self.assertEqual((DEVICE[102], DEVICE[103]), (1, 1))
            self.assertTrue(surface._settings['pitch_bend'])
            self.assertTrue(surface._settings['pressure'])

    def test_disconnected_and_unverified_profiles_reject_controls_without_saving(self):
        surface, _ = self.create()
        for setter in (surface.set_roli_pitch_bend, surface.set_roli_pressure):
            with self.assertRaises(RuntimeError):
                setter(0)
        fake.SERIAL_REPLY = fake.serial_reply(b'LKB000000000TEST')
        tick(surface, 60)
        self.assertTrue(surface.get_roli_controls_state_v8().endswith(' 1 1 0'))
        for setter in (surface.set_roli_pitch_bend, surface.set_roli_pressure):
            with self.assertRaises(RuntimeError):
                setter(0)
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))
        self.assertEqual([DEVICE[item] for item in (101, 102, 103)], [0, 0, 0])
        self.assertFalse(any(item in surface._snapshot for item in (101, 102, 103)))

    def test_legacy_preferences_default_expression_on_without_rewriting_on_load(self):
        for version in range(1, 6):
            stored = dict(version=version, scale_lighting=False, playing_notes=False)
            stored['key_colors' if version == 5 else 'white_keys'] = 'rainbow' if version == 5 else False
            if version >= 2:
                stored['root_color'] = False
            if version >= 3:
                stored['clip_scale'] = True
            if version >= 4:
                stored.update(background_intensity=25, global_brightness=60)
            with open(roli_for_live.SETTINGS_PATH, 'w') as file:
                json.dump(stored, file)
            surface, _ = self.create()
            self.assertFalse(surface._settings_error)
            self.assertEqual(self.read_settings(), stored)
            self.assertTrue(surface._settings['pitch_bend'])
            self.assertTrue(surface._settings['pressure'])
            surface.set_roli_playing_notes(1)
            saved = self.read_settings()
            self.assertEqual(saved['version'], 6)
            self.assertTrue(saved['pitch_bend'])
            self.assertTrue(saved['pressure'])
            surface.disconnect()
            self.surfaces.remove(surface)

    def test_invalid_saved_expression_preferences_fail_explicitly(self):
        for name in ('pitch_bend', 'pressure'):
            stored = dict(roli_for_live.DEFAULT_SETTINGS, version=6)
            stored[name] = 0
            with open(roli_for_live.SETTINGS_PATH, 'w') as file:
                json.dump(stored, file)
            surface, _ = self.create()
            self.assertTrue(surface._settings_error)
            self.assertEqual(self.read_settings(), stored)
            surface.disconnect()
            self.surfaces.remove(surface)

    def test_legacy_snapshot_adds_current_expression_without_replacing_lighting(self):
        surface = self.start()
        with open(roli_for_live.SNAPSHOT_PATH) as file:
            legacy = json.load(file)
        for item in (101, 102, 103):
            del legacy['items'][str(item)]
        with open(roli_for_live.SNAPSHOT_PATH, 'w') as file:
            json.dump(legacy, file)
        surface.port_settings_changed()
        tick(surface, 60)
        self.assertEqual([surface._snapshot[item] for item in (101, 102, 103)], [1, 1, 1])
        for item, value in legacy['items'].items():
            self.assertEqual(surface._snapshot[int(item)], value)
