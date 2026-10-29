from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from maya_ffmpeg_playblast import output


class OutputTests(unittest.TestCase):
    def test_default_scene_name_and_project_movie_rule(self):
        self.assertEqual(output.project_path('', 'C:/scenes/Shot17.ma', 'C:/project', 'movies'),
                         Path('C:/project/movies/Shot17.mp4'))

    def test_custom_movie_rule_and_saved_name(self):
        self.assertEqual(output.project_path('Shot17.mov', '', 'C:/project', 'reviews'),
                         Path('C:/project/reviews/Shot17.mp4'))

    def test_unsaved_scene_fallback(self):
        self.assertEqual(output.project_path('', '', 'C:/project', ''),
                         Path('C:/project/movies/playblast.mp4'))

    def test_explicit_absolute_and_relative_directories(self):
        self.assertEqual(output.project_path('S:/blast/Shot17.mp4', '', 'C:/project', 'movies'),
                         Path('S:/blast/Shot17.mp4'))
        self.assertEqual(output.project_path('review/Shot17', '', 'C:/project', 'movies'),
                         Path('C:/project/review/Shot17.mp4'))

    def test_version_number_is_not_treated_as_movie_extension(self):
        self.assertEqual(output.movie_name('Shot17.v003', ''), Path('Shot17.v003.mp4'))

    def test_success_replaces_existing_file_without_dialog(self):
        with tempfile.TemporaryDirectory(prefix='mfp-test-', dir=str(Path(__file__).parent)) as directory:
            job = Path(directory)
            encoded, target = job / 'encoded.mp4', job / 'saved.mp4'
            encoded.write_bytes(b'new')
            target.write_bytes(b'old')
            actual, notice = output.publish(encoded, target, job)
            self.assertEqual(actual, target)
            self.assertIsNone(notice)
            self.assertEqual(target.read_bytes(), b'new')
            self.assertFalse(encoded.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows file-lock regression')
    def test_real_locked_file_preserves_old_video_and_saves_new_to_temp(self):
        import ctypes as c
        from ctypes import wintypes as w
        api = c.WinDLL('kernel32', use_last_error=True)
        api.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p,
                                   w.DWORD, w.DWORD, w.HANDLE]
        api.CreateFileW.restype = w.HANDLE
        api.CloseHandle.argtypes = [w.HANDLE]
        with tempfile.TemporaryDirectory(prefix='mfp-test-', dir=str(Path(__file__).parent)) as directory:
            root = Path(directory)
            job = root / 'job'
            job.mkdir()
            encoded, target = job / 'encoded.mp4', root / 'Shot17.mp4'
            encoded.write_bytes(b'new video')
            target.write_bytes(b'old video')
            handle = api.CreateFileW(str(target), 0x80000000, 0, None, 3, 0, None)
            self.assertNotEqual(handle, c.c_void_p(-1).value)
            try:
                actual, notice = output.publish(encoded, target, job)
                self.assertEqual(actual.parent, job)
                self.assertTrue(actual.name.startswith('Shot17_'))
                self.assertEqual(actual.read_bytes(), b'new video')
                self.assertIn('open or write-protected', notice)
                self.assertIn('temporary folder', notice)
            finally:
                api.CloseHandle(handle)
            self.assertEqual(target.read_bytes(), b'old video')

    def test_unavailable_project_falls_back_with_accurate_message(self):
        with tempfile.TemporaryDirectory(prefix='mfp-test-', dir=str(Path(__file__).parent)) as directory:
            job = Path(directory)
            encoded = job / 'encoded.mp4'
            encoded.write_bytes(b'new')
            with patch.object(Path, 'mkdir', side_effect=PermissionError('denied')):
                actual, notice = output.publish(encoded, job / 'project' / 'shot.mp4', job)
            self.assertTrue(actual.is_file())
            self.assertNotIn('is open', notice)
