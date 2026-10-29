"""Exercise full capture completion with Maya/encoding stubbed and real file moves."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from maya_ffmpeg_playblast import capture, output


class CaptureOutputTests(unittest.TestCase):
    def run_capture(self, locked, save_to_file=True):
        with tempfile.TemporaryDirectory(prefix='mfp-capture-test-', dir=str(Path(__file__).parent)) as directory:
            root = Path(directory)
            temp_root = root / 'Temp'
            temp_root.mkdir()
            unrelated = temp_root / 'other-app.tmp'
            unrelated.write_bytes(b'keep this')
            target = root / 'movies/Shot17.mp4'
            target.parent.mkdir()
            target.write_bytes(b'old video')
            values = dict(MultiCamera=0, UseSequenceTime=0, SaveDepth=0,
                          Offscreen=0, UseStartEnd=0, File='' if save_to_file else 'S:/ignore/OldName.mov', SaveToFile=int(save_to_file),
                          Scale=1.0, ShowOrnaments=1, DisplaySizeSource=1, Quality=90)
            original_replace = output.os.replace

            def replace(source, destination):
                if locked and Path(destination) == target:
                    raise PermissionError('Destination locked')
                return original_replace(source, destination)

            def playblast(**kwargs):
                movie = Path(kwargs['filename'])
                movie.write_bytes(b'capture')
                return str(movie)

            def encode(source, rate, count, staging, quality, **kwargs):
                Path(staging).write_bytes(b'new video')

            with patch.object(capture, 'cmds') as cmds, patch.object(capture.mel, 'eval'), \
                    patch.object(capture.audio, 'selected', return_value=None), \
                    patch.object(capture.viewport, 'capture_options', return_value={}), \
                    patch.object(capture.encoder, 'binary'), \
                    patch.object(capture.encoder, 'encode', side_effect=encode), \
                    patch.object(capture.tempfile, 'gettempdir', return_value=str(temp_root)), \
                    patch.object(capture.tempfile, 'mkdtemp', side_effect=AssertionError('No temp subfolders')), \
                    patch.object(capture.om, 'MTime') as mtime, \
                    patch.object(capture.completion, 'finish') as finish, \
                    patch.object(output.os, 'replace', side_effect=replace):
                mtime.return_value.asUnits.return_value = 1 / 24
                cmds.optionVar.side_effect = lambda **kw: values[kw['q'][9:]]
                cmds.file.return_value = 'C:/scenes/Shot17.ma'
                cmds.workspace.side_effect = lambda **kw: 'movies' if 'fileRuleEntry' in kw else str(root)
                cmds.playbackOptions.side_effect = lambda **kw: 1 if 'minTime' in kw else 48
                cmds.playblast.side_effect = playblast
                result = Path(capture.execute(0))
                cmds.fileDialog2.assert_not_called()
                finish.assert_called_once_with(result, cmds.warning)
                self.assertEqual(result.read_bytes(), b'new video')
                if locked:
                    self.assertEqual(result.parent, temp_root)
                    self.assertTrue(result.name.startswith('Shot17_'))
                    self.assertEqual(target.read_bytes(), b'old video')
                    self.assertEqual(set(temp_root.iterdir()), {unrelated, result})
                    self.assertIn('temporary folder', cmds.confirmDialog.call_args.kwargs['message'])
                else:
                    self.assertEqual(result, target)
                    self.assertEqual(list(temp_root.iterdir()), [unrelated])
                    cmds.confirmDialog.assert_not_called()
                self.assertEqual(unrelated.read_bytes(), b'keep this')

    def test_save_uses_maya_name_without_prompt_and_deletes_avi(self):
        self.run_capture(False)

    def test_locked_file_is_successful_temporary_playblast_and_deletes_avi(self):
        self.run_capture(True)

    def test_save_off_uses_project_scene_name_and_no_temp_subfolders(self):
        self.run_capture(False, save_to_file=False)

    def test_save_off_locked_output_goes_directly_in_temp(self):
        self.run_capture(True, save_to_file=False)
