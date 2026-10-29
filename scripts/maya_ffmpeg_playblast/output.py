"""Maya-style filenames and atomic output publication with temporary fallback."""
import os
from pathlib import Path
import shutil
import uuid


def movie_name(filename, scene):
    name = str(filename or '').strip()
    if not name:
        name = Path(scene).stem if scene else 'playblast'
    path = Path(os.path.expandvars(name))
    if path.suffix.lower() in ('.mov', '.avi', '.qt', '.mp4'):
        return path.with_suffix('.mp4')
    return Path(str(path) + '.mp4')


def project_path(filename, scene, project, movie_rule):
    path = movie_name(filename, scene)
    if path.is_absolute():
        return path
    raw = str(filename or '').replace('\\', '/')
    if '/' in raw:
        return Path(project) / path
    rule = os.path.expandvars((movie_rule or 'movies').split(';')[0])
    folder = Path(rule)
    if not folder.is_absolute():
        folder = Path(project) / folder
    return folder / path


def publish(encoded, destination, temp_dir):
    """Return (actual output, notification). Never discard a valid encoded MP4."""
    encoded, destination, temp_dir = Path(encoded), Path(destination), Path(temp_dir)
    transfer = None
    existed = destination.exists()
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if encoded.drive.lower() == destination.drive.lower():
            os.replace(str(encoded), str(destination))
        else:
            # Stage beside the destination for an atomic replacement across drives.
            transfer = destination.parent / ('.mfp-' + uuid.uuid4().hex + '.mp4')
            shutil.copyfile(str(encoded), str(transfer))
            os.replace(str(transfer), str(destination))
            encoded.unlink()
        return destination, None
    except OSError as exc:
        # Shared Windows Temp directory: unique filenames avoid earlier open videos.
        fallback = temp_dir / (destination.stem + '_' + uuid.uuid4().hex[:12] + '.mp4')
        if encoded != fallback:
            os.replace(str(encoded), str(fallback))
        if existed and (isinstance(exc, PermissionError) or getattr(exc, 'winerror', 0) in (5, 32, 33)):
            reason = 'The destination file is open or write-protected and cannot be overwritten.'
        else:
            reason = 'The playblast could not be saved to the requested location.'
        return fallback, reason + '\nThe new playblast has been saved to a temporary folder:\n' + str(fallback)
    finally:
        if transfer is not None and transfer.exists():
            try:
                transfer.unlink()
            except OSError:
                pass
