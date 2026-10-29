import sys
from pathlib import Path
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from maya_ffmpeg_playblast import completion, clipboard, config


class CompletionTests(unittest.TestCase):
    def test_clipboard_failure_still_opens_video(self):
        warning = Mock()
        with patch.object(completion.os, 'startfile') as viewer, \
                patch.object(config, 'COPY_TO_CLIPBOARD', True), \
                patch.object(clipboard, 'copy_video', side_effect=RuntimeError('busy')):
            completion.finish('video.mp4', warning)
        viewer.assert_called_once()
        warning.assert_called_once()

    def test_viewer_failure_still_copies_video(self):
        with patch.object(completion.os, 'startfile', side_effect=OSError('no player')), \
                patch.object(config, 'COPY_TO_CLIPBOARD', True), \
                patch.object(clipboard, 'copy_video') as copy:
            completion.finish('video.mp4', Mock())
        copy.assert_called_once()

    def test_default_does_not_touch_clipboard_and_still_opens_video(self):
        self.assertFalse(config.COPY_TO_CLIPBOARD)
        with patch.object(completion.os, 'startfile') as viewer, \
                patch.object(clipboard, 'copy_video') as copy:
            completion.finish('video.mp4', Mock())
        viewer.assert_called_once()
        copy.assert_not_called()

    def test_native_payload_layout(self):
        import struct
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'space \u52d5.mp4'
            file.touch()
            data = clipboard.drop_payload(file)
            self.assertEqual(struct.unpack('<IiiII', data[:20]), (20, 0, 0, 0, 1))
            self.assertEqual(data[20:].decode('utf-16-le'), str(file.resolve()) + '\0\0')
