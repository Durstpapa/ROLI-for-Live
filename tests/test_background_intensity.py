"""Reversible background RGB experiment, independent of global brightness and feedback."""
import unittest
from unittest.mock import patch

from test_script import ControlSurface, DEVICE, roli_for_live, run_device, tick
from test_settings import SurfaceTestCase


class BackgroundIntensityTests(SurfaceTestCase):
    def setUp(self):
        super().setUp()
        DEVICE[36] = 61
        self.original[36] = 61

    def create(self):
        surface, instance = super().create()
        surface.set_roli_background_intensity(25)
        return surface, instance

    def test_rgb_scaling_preserves_channels_at_full_intensity(self):
        for color in (0, 0xFFFFFF, 0x123456, 0xFF0000, 0x00FF00, 0x0000FF):
            self.assertEqual(roli_for_live._dim(color, 1.0), color)
            self.assertEqual(roli_for_live._dim(color, 0.0), 0)
        self.assertEqual(roli_for_live._dim(0xFFFFFF, 0.25), 0x3F3F3F)
        self.assertEqual(roli_for_live._dim(0x123456, 0.25), 0x040D15)

    def test_both_palettes_and_root_options_dim_background_only(self):
        surface, _ = self.create()
        tick(surface, 60)
        for white in (1, 0):
            for root in (1, 0):
                surface.set_roli_white_keys(white)
                surface.set_roli_root_color(root)
                tick(surface, 2)
                base = 0xFFFFFF if white else self.track.color
                accent = self.track.color if white else roli_for_live._brighter(self.track.color)
                self.assertEqual(DEVICE[34], roli_for_live._argb(roli_for_live._dim(base, 0.25)))
                self.assertEqual(DEVICE[35], roli_for_live._argb(
                    roli_for_live._dim(accent if root else base, 0.25)))
                self.assertEqual(DEVICE[36], 61, 'never write global brightness')

    def test_native_restore_bypasses_dimming_and_reenable_reapplies_it(self):
        surface, _ = self.create()
        tick(surface, 60)
        surface.set_roli_scale_lighting(0)
        tick(surface, 2)
        self.assert_original_lighting()
        self.assertEqual(DEVICE[36], 61)
        surface.set_roli_scale_lighting(1)
        tick(surface, 2)
        self.assertEqual(DEVICE[34], roli_for_live._argb(0x3F3F3F))
        surface.disconnect()
        self.surfaces.remove(surface)
        run_device(surface)
        self.assert_original_lighting()
        self.assertEqual(DEVICE[36], 61)

    def test_playback_highlights_keep_maximum_velocity_and_feedback_channels(self):
        surface, instance = self.create()
        tick(surface, 60)
        ControlSurface.notes_out[:] = []
        self.track.clip.playing_position = 0.25
        self.song.is_playing = True
        self.song.current_song_time = 0.25
        tick(surface, 2)
        self.assertIn((0x90, 60, 127), ControlSurface.notes_out)
        self.assertEqual(instance.velocity, 127)
        self.assertEqual(ControlSurface.feedback_channels, [0])
        self.assertEqual(DEVICE[34], roli_for_live._argb(0x3F3F3F))
        self.assertEqual(DEVICE[36], 61)
        self.assertTrue(any('saved background_intensity 25%' in log
                            for log in ControlSurface.logs))

    def test_full_intensity_retains_the_existing_default_palette(self):
        surface, _ = self.create()
        surface.set_roli_background_intensity(100)
        tick(surface, 60)
        self.assertEqual(DEVICE[34], roli_for_live._argb(0xFFFFFF))
        self.assertEqual(DEVICE[35], roli_for_live._argb(self.track.color))
        self.assertEqual(DEVICE[36], 61)

    def test_reduced_velocity_controls_both_feedback_paths_without_changing_background(self):
        with patch.object(roli_for_live, 'PLAYING_NOTES_FEEDBACK_VELOCITY', 64):
            surface, instance = self.create()
            tick(surface, 60)
            ControlSurface.notes_out[:] = []
            self.track.clip.playing_position = 0.25
            self.song.is_playing = True
            self.song.current_song_time = 0.25
            tick(surface, 2)
            self.assertIn((0x90, 60, 64), ControlSurface.notes_out)
            self.assertNotIn((0x90, 60, 127), ControlSurface.notes_out)
            self.assertEqual(instance.velocity, 64)
            self.assertEqual(ControlSurface.feedback_channels, [0])
            self.assertIs(ControlSurface.controlled_track, self.track)
            self.assertEqual(DEVICE[34], roli_for_live._argb(0x3F3F3F))
            self.assertEqual(DEVICE[36], 61)
            surface.set_roli_playing_notes(0)
            self.assertEqual(instance.velocity, 0)
            surface.set_roli_playing_notes(1)
            tick(surface, 2)
            self.assertEqual(instance.velocity, 64)
            self.assertEqual(ControlSurface.notes_out[-1], (0x90, 60, 64))


if __name__ == '__main__':
    unittest.main()
