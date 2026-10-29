"""Maya-independent encoding helpers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from fractions import Fraction


def binary(name):
    bundled = Path(__file__).resolve().parents[2] / 'bin' / 'windows' / (name + '.exe')
    found = str(bundled) if bundled.is_file() else shutil.which(name)
    if not found:
        raise RuntimeError('%s was not found. This development package needs FFmpeg on PATH.' % name)
    return found


def run(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            encoding='utf-8', errors='replace',
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:])
    return result.stdout


def encode(sequence, fps, count, destination, quality=90, audio=None,
           movie=False, preset='ultrafast'):
    """Write and validate a new file; caller owns final destination replacement."""
    crf = round(30 - max(0, min(100, quality)) * 0.12)
    duration = count / float(Fraction(str(fps)))
    args = [binary('ffmpeg'), '-nostdin', '-y']
    if not movie:
        args += ['-framerate', str(fps), '-start_number', '0']
    args += ['-i', str(sequence)]
    if audio is not None:
        args += audio_arguments(audio, duration)
    else:
        args += ['-map', '0:v:0', '-an']
    args += ['-t', str(duration), '-r', str(fps), '-fps_mode', 'cfr',
            '-c:v', 'libx264', '-crf', str(crf), '-preset', preset,
            '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(destination)]
    run(args)
    # MP4 records sample counts in its index. Avoid decoding the entire movie again.
    data = json.loads(run([binary('ffprobe'), '-v', 'error',
                           '-show_streams', '-of', 'json', str(destination)]))
    video = next(s for s in data['streams'] if s['codec_type'] == 'video')
    if video['codec_name'] != 'h264' or int(video.get('nb_frames', 0)) != count:
        raise RuntimeError('Encoded video failed codec/frame count validation.')
    if abs(float(video['duration']) - duration) > 1 / float(Fraction(str(fps))):
        raise RuntimeError('Encoded video failed duration validation.')
    if audio is not None:
        stream = next((s for s in data['streams'] if s['codec_type'] == 'audio'), None)
        if stream is None or stream['codec_name'] != 'aac':
            raise RuntimeError('Encoded video is missing its AAC audio track.')
    return data


def audio_arguments(audio, duration):
    """Encode audio in the video pass, bounded by duration rather than frames:v."""
    args = []
    if audio['length'] > 0:
        args += ['-i', audio['path']]
        filters = ('atrim=start=%.9f:duration=%.9f,asetpts=PTS-STARTPTS,'
                   'aresample=48000,adelay=%dS:all=1,apad,atrim=duration=%.9f') % (
                       audio['trim'], audio['length'], round(audio['delay'] * 48000), duration)
        args += ['-map', '0:v:0', '-map', '1:a:0', '-af', filters]
    else:
        args += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
                 '-map', '0:v:0', '-map', '1:a:0']
    args += ['-c:a', 'aac', '-b:a', '192k']
    return args
