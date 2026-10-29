"""Viewport capture with active timeline audio."""
from pathlib import Path
import tempfile
import time
import uuid
from maya import cmds, mel
from maya.api import OpenMaya as om
from . import encoder, audio, viewport, completion, output


def option(name):
    return cmds.optionVar(q='playblast' + name)


def execute(action):
    encoder.binary('ffmpeg')
    encoder.binary('ffprobe')
    if option('MultiCamera') or option('UseSequenceTime') or option('SaveDepth'):
        raise RuntimeError('This prototype supports a single viewport, timeline time, and color output only.')
    # Resolve the intended editor before any file dialog changes UI focus.
    viewport_options = viewport.capture_options(bool(option('Offscreen')))
    slider = mel.eval('$mfpSlider = $gPlayBackSlider')
    start = cmds.playbackOptions(q=True, minTime=True)
    end = cmds.playbackOptions(q=True, maxTime=True)
    if action == 3 and cmds.timeControl(slider, q=True, rangeVisible=True):
        start, end = cmds.timeControl(slider, q=True, rangeArray=True)
        end -= 1
    elif action != 3 and option('UseStartEnd'):
        start, end = option('StartTime'), option('EndTime')
    if start != int(start) or end != int(end) or end < start:
        raise RuntimeError('This prototype requires an increasing range of whole scene frames.')
    count = int(end - start + 1)
    fps = 1.0 / om.MTime(1, om.MTime.uiUnit()).asUnits(om.MTime.kSeconds)
    # Displayed decimal rates are converted from Maya's actual time unit.
    from fractions import Fraction
    rate = str(Fraction(fps).limit_denominator(100000))
    sound = audio.selected(slider, start, count / fps, fps)
    temp_root = Path(tempfile.gettempdir())
    token = uuid.uuid4().hex
    capture_path = temp_root / ('maya-ffmpeg-' + token + '.avi')
    error_path = temp_root / ('maya-ffmpeg-' + token + '.error.txt')
    scene = cmds.file(q=True, sceneName=True)
    # Save to File off means automatic project naming for this plugin.
    filename = option('File') if option('SaveToFile') else ''
    destination = output.project_path(filename, scene,
                                      cmds.workspace(q=True, rootDirectory=True),
                                      cmds.workspace(fileRuleEntry='movie'))
    staging = temp_root / ('.maya-ffmpeg-' + token + '.mp4')
    current = cmds.currentTime(q=True)
    try:
        kwargs = dict(format='avi', compression='none', filename=str(capture_path),
                      startTime=start, endTime=end, viewer=False, forceOverwrite=True,
                      percent=round(float(option('Scale')) * 100),
                      showOrnaments=bool(option('ShowOrnaments')), framePadding=8,
                      **viewport_options)
        size = option('DisplaySizeSource')
        if size == 2:
            kwargs['widthHeight'] = (cmds.getAttr('defaultResolution.width'), cmds.getAttr('defaultResolution.height'))
        elif size == 3:
            kwargs['widthHeight'] = (option('Width'), option('Height'))
        started = time.perf_counter()
        result = cmds.playblast(**kwargs)
        captured = time.perf_counter()
        movie = Path(result) if result else capture_path
        # Temp is shared: only touch the exact unique file allocated for this capture.
        if movie.resolve() != capture_path.resolve() or not movie.is_file():
            raise RuntimeError('Maya did not create the expected temporary AVI.')
        encoder.encode(movie, rate, count, staging, option('Quality'), audio=sound, movie=True)
        encoded = time.perf_counter()
        destination, notice = output.publish(staging, destination, temp_root)
        try:
            movie.unlink()
        except OSError as exc:
            cmds.warning('MP4 saved, but temporary AVI cleanup failed: %s' % exc)
        print('FFmpeg Playblast: capture %.2fs; encode + validation %.2fs; total %.2fs' %
              (captured - started, encoded - captured, time.perf_counter() - started))
        # User preference: always open completed MP4s, independent of clipboard success.
        completion.finish(destination, cmds.warning)
        if notice:
            cmds.warning(notice)
            cmds.confirmDialog(title='Playblast saved to temporary folder',
                               message=notice, icon='information', button=['OK'])
        return str(destination)
    except Exception as exc:
        error_path.write_text(str(exc), encoding='utf-8')
        raise RuntimeError('%s\nRecovery capture: %s\nLog: %s' % (exc, capture_path, error_path))
    finally:
        cmds.currentTime(current)
        if staging.exists():
            staging.unlink()
