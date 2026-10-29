"""Drag this file into Maya's viewport to install MP4 FFmpeg Playblast."""
import importlib.util
from pathlib import Path
import shutil
import sys


def onMayaDroppedPythonFile(*args):
    from maya import cmds
    source = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('mfp_dependencies', str(source / 'scripts/maya_ffmpeg_playblast/dependencies.py'))
    dependencies = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dependencies)
    cmds.progressWindow(title='Installing MP4 FFmpeg', status='Preparing FFmpeg...', progress=0)
    try:
        dependencies.ensure_tools(source, lambda value: cmds.progressWindow(
            e=True, progress=value, status='Downloading FFmpeg... %s%%' % value))
    finally:
        cmds.progressWindow(endProgress=True)
    modules = Path(cmds.internalVar(userAppDir=True)) / 'modules'
    destination = modules / 'MayaFFmpegPlayblast'
    modules.mkdir(parents=True, exist_ok=True)
    plugin = destination / 'plug-ins' / 'mayaFfmpegPlayblast.py'
    if cmds.pluginInfo('mayaFfmpegPlayblast.py', q=True, registered=True):
        if cmds.pluginInfo('mayaFfmpegPlayblast.py', q=True, loaded=True):
            cmds.unloadPlugin('mayaFfmpegPlayblast.py')
    if source != destination:
        shutil.copytree(str(source), str(destination), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    # Maya keeps Python modules cached after unloading a plugin. Drop only ours.
    for name in list(sys.modules):
        if name == 'maya_ffmpeg_playblast' or name.startswith('maya_ffmpeg_playblast.'):
            del sys.modules[name]
    (modules / 'MayaFFmpegPlayblast.mod').write_text(
        '+ MayaFFmpegPlayblast 0.5.0 ' + destination.as_posix() + '\n', encoding='utf-8')
    scripts = str(destination / 'scripts')
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    cmds.loadPlugin(str(plugin))
    cmds.pluginInfo('mayaFfmpegPlayblast.py', e=True, autoload=True)
    cmds.pluginInfo(savePluginPrefs=True)
    cmds.confirmDialog(title='MP4 FFmpeg', message='MP4 FFmpeg installed successfully.\nRestart Maya, then choose MP4 (FFmpeg) in Playblast Options.', button=['OK'], icon='information')
