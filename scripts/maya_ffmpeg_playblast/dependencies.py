"""Install pinned upstream tools for the small public source package."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import urllib.request
from zipfile import ZipFile

URL = 'https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip'
SHA256 = '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba'
PREFIX = 'ffmpeg-9.0.2-essentials_build/'


def ensure_tools(root, report=None):
    root = Path(root)
    target = root / 'bin/windows'
    if all((target / name).is_file() for name in ('ffmpeg.exe', 'ffprobe.exe')):
        return
    def progress(percent):
        if report:
            report(percent)
    progress(0)
    with tempfile.NamedTemporaryFile(prefix='maya-ffmpeg-download-', suffix='.zip') as download:
        request = urllib.request.Request(URL, headers={'User-Agent': 'MayaFFmpegPlayblast/0.5'})
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get('Content-Length', 0))
            size = 0
            digest = hashlib.sha256()
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                download.write(chunk)
                digest.update(chunk)
                size += len(chunk)
                progress(min(95, int(size * 95 / total)) if total else 0)
        download.flush()
        if digest.hexdigest() != SHA256:
            raise RuntimeError('FFmpeg download verification failed. Please retry installation.')
        # Use the open handle: Windows locks NamedTemporaryFile against reopening.
        with ZipFile(download) as archive:
            required = ['bin/ffmpeg.exe', 'bin/ffprobe.exe', 'LICENSE', 'README.txt']
            for name in required:
                archive.getinfo(PREFIX + name)
            for name in required:
                output = target / Path(name).name if name.startswith('bin/') else root / 'licenses/ffmpeg' / name
                output.parent.mkdir(parents=True, exist_ok=True)
                staging = output.with_name(output.name + '.download')
                try:
                    with archive.open(PREFIX + name) as source, staging.open('wb') as dest:
                        shutil.copyfileobj(source, dest)
                    staging.replace(output)
                finally:
                    if staging.exists():
                        staging.unlink()
    progress(100)
