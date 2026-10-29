"""Independent post-export actions: opening must survive clipboard errors."""
import os
from pathlib import Path
from . import clipboard, config


def finish(path, warning):
    path = str(Path(path).resolve())
    try:
        os.startfile(path)
    except Exception as exc:
        warning('MP4 saved at %s; viewer could not open: %s' % (path, exc))
    if not config.COPY_TO_CLIPBOARD:
        return
    try:
        clipboard.copy_video(path)
        print('FFmpeg Playblast: video file copied. Paste into your chat to attach it.')
    except Exception as exc:
        warning('MP4 saved at %s; clipboard copy failed: %s' % (path, exc))
