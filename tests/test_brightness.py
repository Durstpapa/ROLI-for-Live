"""Persistent global brightness and relative background intensity."""
import json
import os
import unittest
from unittest.mock import patch

from test_script import ControlSurface, DEVICE, roli_for_live, run_device, tick
from test_settings import SurfaceTestCase


class BrightnessTests(SurfaceTestCase):
    def test_initial_state_reads_hardware_without_applying_a_default_brightness(self):
        DEVICE[36] = 61
        surface, _ = self.create()
        self.assertTrue(surface.get_roli_controls_state_v5().endswith('live -1 100'))
        tick(surface, 60)
        self.assertTrue(surface.get_roli_controls_state_v5().endswith('live 61 100'))
        self.assertEqual(DEVICE[36], 61)
        self.assertNotIn(36, surface._sent)
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))

    def test_global_range_endpoints_change_only_native_brightness(self):
        surface, instance = self.create()
        tick(surface, 60)
        colors = DEVICE[34], DEVICE[35]
        for value in (0, 1, 25, 64, 100):
            surface.set_roli_global_brightness(value)
            tick(surface, 2)
            self.assertEqual(DEVICE[36], value)
            self.assertEqual((DEVICE[34], DEVICE[35]), colors)
            self.assertEqual(instance.velocity, 127)
            self.assertEqual(self.read_settings()['global_brightness'], value)

    def test_background_range_endpoints_leave_global_brightness_and_feedback_unchanged(self):
        surface, instance = self.create()
        tick(surface, 60)
        for value, color in ((0, 0x000000), (25, 0x3F3F3F), (100, 0xFFFFFF)):
            surface.set_roli_background_intensity(value)
            tick(surface, 2)
            self.assertEqual(DEVICE[34], roli_for_live._argb(color))
            self.assertEqual(DEVICE[36], 100)
            self.assertEqual(instance.velocity, 127)

    def test_both_levels_survive_restart_without_max(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_global_brightness(60)
        surface.set_roli_background_intensity(25)
        surface, instance = self.restart(surface)
        tick(surface, 60)
        self.assertEqual(DEVICE[36], 60)
        self.assertEqual(DEVICE[34], roli_for_live._argb(0x3F3F3F))
        self.assertEqual(instance.velocity, 127)
        self.assertTrue(surface.get_roli_controls_state_v5().endswith('live 60 25'))

    def test_global_remains_active_with_scale_lighting_off_and_shutdown_restores_it(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_global_brightness(40)
        surface.set_roli_scale_lighting(0)
        surface.set_roli_background_intensity(25)
        tick(surface, 2)
        self.assertEqual(DEVICE[36], 40)
        for item in list(roli_for_live.SHARED_LIGHTING_ITEMS) + [100, 104]:
            if item != 36:
                self.assertEqual(DEVICE[item], self.original[item])
        surface.set_roli_global_brightness(70)
        tick(surface, 2)
        self.assertEqual(DEVICE[36], 70)
        surface.disconnect()
        self.surfaces.remove(surface)
        run_device(surface)
        self.assert_original_lighting()

    def test_failed_level_saves_preserve_file_runtime_and_queued_writes(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_background_intensity(25)
        tick(surface, 2)
        before = self.read_settings()
        for setter in (surface.set_roli_global_brightness, surface.set_roli_background_intensity):
            with patch.object(roli_for_live.os, 'replace', side_effect=PermissionError('denied')):
                with self.assertRaises(PermissionError):
                    setter(50)
            self.assertEqual(self.read_settings(), before)
            self.assertEqual(surface._settings['background_intensity'], 25)
            self.assertIsNone(surface._settings['global_brightness'])
            self.assertEqual(surface._pending, {})
        self.assertEqual(DEVICE[36], 100)

    def test_invalid_values_are_rejected_without_creating_preferences(self):
        surface, _ = self.create()
        for setter in (surface.set_roli_global_brightness, surface.set_roli_background_intensity):
            for invalid in (-1, 101, 1.0, True, False, '25', None):
                with self.assertRaises(ValueError):
                    setter(invalid)
        self.assertFalse(os.path.exists(roli_for_live.SETTINGS_PATH))

    def test_all_legacy_schemas_migrate_without_enabling_global_brightness(self):
        for version in (1, 2, 3):
            stored = dict(version=version, white_keys=False, scale_lighting=False, playing_notes=False)
            if version >= 2:
                stored['root_color'] = False
            if version >= 3:
                stored['clip_scale'] = True
            with open(roli_for_live.SETTINGS_PATH, 'w') as file:
                json.dump(stored, file)
            surface, _ = self.create()
            self.assertEqual(self.read_settings(), stored)
            self.assertEqual(surface._settings['background_intensity'], 100)
            self.assertIsNone(surface._settings['global_brightness'])
            surface.set_roli_background_intensity(25)
            updated = self.read_settings()
            self.assertEqual(updated['version'], 4)
            self.assertEqual(updated['background_intensity'], 25)
            self.assertIsNone(updated['global_brightness'])
            for name, value in stored.items():
                if name != 'version':
                    self.assertEqual(updated[name], value)
            surface.disconnect()
            self.surfaces.remove(surface)

    def test_invalid_saved_levels_report_an_error_instead_of_applying_them(self):
        for name, value in (('background_intensity', True), ('background_intensity', 101),
                            ('global_brightness', False), ('global_brightness', -1)):
            stored = dict(roli_for_live.DEFAULT_SETTINGS, version=4)
            stored[name] = value
            with open(roli_for_live.SETTINGS_PATH, 'w') as file:
                json.dump(stored, file)
            surface, _ = self.create()
            self.assertTrue(surface._settings_error)
            self.assertEqual(surface._settings['background_intensity'], 100)
            self.assertIsNone(surface._settings['global_brightness'])
            self.assertEqual(self.read_settings(), stored)
            surface.disconnect()
            self.surfaces.remove(surface)

    def test_legacy_snapshot_adds_current_brightness_without_replacing_original_colors(self):
        surface, _ = self.create()
        tick(surface, 60)
        with open(roli_for_live.SNAPSHOT_PATH) as file:
            legacy = json.load(file)
        del legacy['items']['36']
        with open(roli_for_live.SNAPSHOT_PATH, 'w') as file:
            json.dump(legacy, file)
        surface.port_settings_changed()
        DEVICE[36], DEVICE[34] = 61, roli_for_live._argb(0x222222)
        tick(surface, 60)
        with open(roli_for_live.SNAPSHOT_PATH) as file:
            migrated = json.load(file)
        self.assertEqual(migrated['items']['36'], 61)
        for item, value in legacy['items'].items():
            self.assertEqual(migrated['items'][item], value)
        self.assertEqual(DEVICE[36], 61)

    def test_reconnect_reapplies_saved_levels_and_keeps_native_brightness_snapshot(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_global_brightness(40)
        surface.set_roli_background_intensity(25)
        tick(surface, 2)
        surface.port_settings_changed()
        DEVICE[36] = 80
        tick(surface, 60)
        self.assertEqual(DEVICE[36], 40)
        self.assertEqual(DEVICE[34], roli_for_live._argb(0x3F3F3F))
        self.assertEqual(surface._snapshot[36], 100)

    def test_rapid_brightness_changes_cancel_stale_pending_values(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_global_brightness(40)
        surface.set_roli_global_brightness(80)
        surface.set_roli_background_intensity(0)
        surface.set_roli_background_intensity(25)
        tick(surface, 2)
        self.assertEqual(DEVICE[36], 80)
        self.assertEqual(DEVICE[34], roli_for_live._argb(0x3F3F3F))


if __name__ == '__main__':
    unittest.main()
