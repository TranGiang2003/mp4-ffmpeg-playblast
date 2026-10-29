import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from maya_ffmpeg_playblast import encoder


class FastEncoding(unittest.TestCase):
    def test_bundled_tools_work_without_path_lookup(self):
        with patch.object(encoder.shutil, 'which', side_effect=AssertionError('No system FFmpeg')):
            self.assertTrue(Path(encoder.binary('ffmpeg')).is_file())
            self.assertTrue(Path(encoder.binary('ffprobe')).is_file())

    def test_fast_path_has_one_encode_and_metadata_only_validation(self):
        metadata = {'streams': [dict(codec_type='video', codec_name='h264',
                                    nb_frames='48', duration='2.0'),
                                dict(codec_type='audio', codec_name='aac')]}
        sound = dict(path='sound.wav', trim=0, delay=0, length=1)
        with patch.object(encoder, 'run', side_effect=['', json.dumps(metadata)]) as run, \
                patch.object(encoder, 'binary', side_effect=lambda name: name):
            encoder.encode('capture.avi', '24', 48, 'output.mp4', audio=sound, movie=True)
        self.assertEqual(run.call_count, 2)
        command = run.call_args_list[0].args[0]
        self.assertNotIn('-framerate', command)
        self.assertNotIn('-frames:v', command)
        self.assertIn('ultrafast', command)
        self.assertIn('aac', command)
        self.assertNotIn('-count_frames', run.call_args_list[1].args[0])
