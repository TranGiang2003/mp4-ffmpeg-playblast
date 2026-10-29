"""Timeline sound selection and timing, expressed in seconds for FFmpeg."""
import os
import json
from pathlib import Path


def timing(offset, silence, source_start, source_end, clip_end, start, duration, fps):
    audible_start = (offset + silence - start) / fps
    source_begin = source_start / fps + max(0.0, -audible_start)
    delay = max(0.0, audible_start)
    length = min((source_end / fps) - source_begin,
                 (clip_end - start) / fps - delay, duration - delay)
    return dict(trim=max(0.0, source_begin), delay=delay, length=max(0.0, length))


def selected(slider, start, duration, fps):
    from maya import cmds
    node = cmds.timeControl(slider, q=True, sound=True)
    if not node:
        return None
    attr = lambda name: cmds.getAttr(node + '.' + name)
    if attr('mute') or int(attr('trackState')) & (4 | 8 | 16):
        return None
    path = Path(cmds.workspace(expandName=os.path.expandvars(attr('filename'))))
    if not path.is_file():
        raise RuntimeError('Timeline audio file is missing: %s' % path)
    source_start, source_end = attr('sourceStart'), attr('sourceEnd')
    offset, silence, clip_end = attr('offset'), attr('silence'), attr('endFrame')
    if source_end == 0 and clip_end <= offset + silence:
        # Some imported/standalone nodes have not populated duration attributes.
        from . import encoder
        info = json.loads(encoder.run([encoder.binary('ffprobe'), '-v', 'error',
                          '-show_format', '-of', 'json', str(path)]))
        source_end = float(info['format']['duration']) * fps
        clip_end = offset + silence + source_end - source_start
    result = timing(offset, silence, source_start, source_end, clip_end, start, duration, fps)
    result['path'] = str(path)
    return result
