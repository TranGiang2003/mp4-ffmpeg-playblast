import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from maya_ffmpeg_playblast import dependencies


class DependencyInstallTests(unittest.TestCase):
    def archive(self):
        stream = io.BytesIO()
        with ZipFile(stream, 'w') as archive:
            for name in ('bin/ffmpeg.exe', 'bin/ffprobe.exe', 'LICENSE', 'README.txt'):
                archive.writestr(dependencies.PREFIX + name, b'upstream fixture')
        return stream.getvalue()

    def test_download_verifies_and_installs_without_system_ffmpeg(self):
        data = self.archive()
        response = io.BytesIO(data)
        response.headers = {'Content-Length': str(len(data))}
        with tempfile.TemporaryDirectory(dir=str(Path(__file__).parent)) as folder, \
                patch.object(dependencies.urllib.request, 'urlopen', return_value=response), \
                patch.object(dependencies, 'SHA256', hashlib.sha256(data).hexdigest()):
            dependencies.ensure_tools(folder)
            self.assertEqual((Path(folder) / 'bin/windows/ffmpeg.exe').read_bytes(), b'upstream fixture')
            self.assertTrue((Path(folder) / 'licenses/ffmpeg/LICENSE').is_file())
            with patch.object(dependencies.urllib.request, 'urlopen', side_effect=AssertionError('No re-download')):
                dependencies.ensure_tools(folder)

    def test_bad_checksum_does_not_install_executables(self):
        response = io.BytesIO(self.archive())
        response.headers = {}
        with tempfile.TemporaryDirectory(dir=str(Path(__file__).parent)) as folder, \
                patch.object(dependencies.urllib.request, 'urlopen', return_value=response), \
                patch.object(dependencies, 'SHA256', 'wrong'):
            with self.assertRaises(RuntimeError):
                dependencies.ensure_tools(folder)
            self.assertFalse((Path(folder) / 'bin/windows/ffmpeg.exe').exists())
