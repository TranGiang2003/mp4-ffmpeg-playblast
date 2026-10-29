import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from maya_ffmpeg_playblast import clipboard


class VideoClipboard(unittest.TestCase):
    def test_real_qt_payload_is_unicode_local_file_url(self):
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / 'animation space \u52d5.mp4'
            video.write_bytes(b'payload test')
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('Must not read video')):
                payload = clipboard.file_payload(video)
            self.assertTrue(payload.hasUrls())
            self.assertEqual(Path(payload.urls()[0].toLocalFile()), video.resolve())
            self.assertFalse(payload.hasFormat('video/mp4'))

    def test_missing_file_rejected(self):
        with self.assertRaises(FileNotFoundError):
            clipboard.file_payload('nonexistent-test-file.mp4')

    def test_copy_transfers_payload_to_existing_clipboard(self):
        app_type, thread = MagicMock(), MagicMock()
        app = app_type.instance.return_value
        thread.currentThread.return_value = app.thread.return_value
        payload = MagicMock()
        payload.urls.return_value = ['file-url']
        app.clipboard.return_value.mimeData.return_value.urls.return_value = ['file-url']
        with patch.object(clipboard, 'qt_types', return_value=(None, None, thread, app_type)), \
                patch.object(clipboard, 'file_payload', return_value=payload):
            clipboard.copy_qt_file('video.mp4')
        app.clipboard.return_value.setMimeData.assert_called_once_with(payload)

    def test_clipboard_rejection_is_reported(self):
        app_type, thread = MagicMock(), MagicMock()
        app = app_type.instance.return_value
        thread.currentThread.return_value = app.thread.return_value
        app.clipboard.return_value.mimeData.return_value = None
        with patch.object(clipboard, 'qt_types', return_value=(None, None, thread, app_type)), \
                patch.object(clipboard, 'file_payload') as payload:
            payload.return_value.urls.return_value = ['file-url']
            with self.assertRaises(RuntimeError):
                clipboard.copy_qt_file('video.mp4')


if __name__ == '__main__':
    unittest.main()
