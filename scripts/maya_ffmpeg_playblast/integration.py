"""Runtime MEL adapters. No Autodesk scripts are shipped or edited."""
import json
import os
import re
from pathlib import Path
from maya import cmds, mel

LABEL = 'MP4 (FFmpeg)'
KEY = 'mfpEnabled'
_source = None
_busy = False
_names = ('playblastSetup', 'playblastCallback', 'changePlayblastFormat', 'performPlayblast')


def enabled():
    return cmds.optionVar(exists=KEY) and bool(cmds.optionVar(q=KEY))


def call(name, *args):
    return mel.eval('mfpOriginal_' + name + '(' + ','.join(json.dumps(a) for a in args) + ')')


def install():
    global _source
    if _source is not None:
        return
    match = re.match(r'^(\d{4})', str(cmds.about(version=True)))
    if not match or not 2023 <= int(match.group(1)) <= 2027:
        raise RuntimeError('MP4 FFmpeg requires Maya 2023–2027 on Windows.')
    path = Path(os.environ['MAYA_LOCATION']) / 'scripts' / 'others' / 'performPlayblast.mel'
    source = path.read_text(encoding='utf-8-sig')
    patched = source
    for name in _names:
        pattern = r'(global\s+proc\s+(?:string\s+)?)' + name + r'(\s*\()'
        patched, count = re.subn(pattern, r'\1mfpOriginal_' + name + r'\2', patched)
        if count != 1:
            raise RuntimeError('Unsupported Maya Playblast script: ' + name)
    mel.eval(patched)
    wrappers = '''
global proc playblastSetup(string $p, int $reset) {
 python("import maya_ffmpeg_playblast.integration as mfp; mfp.setup(" + python("repr(" + ("'" + $p + "'") + ")") + "," + $reset + ")");
}
global proc changePlayblastFormat(string $p) {
 python("import maya_ffmpeg_playblast.integration as mfp; mfp.format_changed(" + python("repr(" + ("'" + $p + "'") + ")") + ")");
}
global proc playblastCallback(string $p, int $doIt) {
 python("import maya_ffmpeg_playblast.integration as mfp; mfp.callback(" + python("repr(" + ("'" + $p + "'") + ")") + "," + $doIt + ")");
}
global proc string performPlayblast(int $action) {
 if (($action == 0 || $action == 3) && `optionVar -exists mfpEnabled` && `optionVar -q mfpEnabled`) {
  return python("import maya_ffmpeg_playblast.integration as mfp; mfp.capture(" + $action + ")");
 }
 return mfpOriginal_performPlayblast($action);
}
'''
    try:
        mel.eval(wrappers)
        _source = source
    except Exception:
        mel.eval(source)
        raise


def setup(parent, reset):
    restore_custom = enabled() and not reset
    call('playblastSetup', parent, int(reset))
    if reset:
        cmds.optionVar(iv=(KEY, 0))
    menu = 'playblastFormatWidget|OptionMenu'
    items = cmds.optionMenuGrp('playblastFormatWidget', q=True, itemListLong=True) or []
    if not any(cmds.menuItem(i, q=True, label=True) == LABEL for i in items):
        cmds.menuItem(label=LABEL, parent=menu)
    if restore_custom:
        cmds.optionMenuGrp('playblastFormatWidget', e=True, value=LABEL)
        format_changed(parent)


def format_changed(parent):
    selected = cmds.optionMenuGrp('playblastFormatWidget', q=True, value=True)
    cmds.optionVar(iv=(KEY, int(selected == LABEL)))
    if selected != LABEL:
        return call('changePlayblastFormat', parent)
    menu = 'playblastCompressWidget|OptionMenu'
    for item in cmds.optionMenuGrp('playblastCompressWidget', q=True, itemListLong=True) or []:
        cmds.deleteUI(item)
    cmds.menuItem(label='H.264', parent=menu)


def callback(parent, do_it):
    custom = cmds.optionMenuGrp('playblastFormatWidget', q=True, value=True) == LABEL
    cmds.optionVar(iv=(KEY, int(custom)))
    if not custom:
        return call('playblastCallback', parent, int(do_it))
    # Save ordinary controls through Maya's own callback, with valid native values.
    cmds.optionMenuGrp('playblastFormatWidget', e=True, value=cmds.optionVar(q='playblastFormat'))
    call('changePlayblastFormat', parent)
    try:
        call('playblastCallback', parent, 0)
    finally:
        cmds.optionMenuGrp('playblastFormatWidget', e=True, value=LABEL)
        format_changed(parent)
    if do_it:
        capture(3 if do_it == 2 else 0)


def uninstall():
    global _source
    if _busy:
        raise RuntimeError('Wait for the current playblast to finish before unloading.')
    if _source is not None:
        mel.eval(_source)
        _source = None
        if cmds.optionMenuGrp('playblastFormatWidget', exists=True):
            # Rebuild through the native implementation to discard custom controls.
            mel.eval('playblastOptions 0')


def capture(action=0):
    global _busy
    if _busy:
        raise RuntimeError('A playblast is already running.')
    from .capture import execute
    _busy = True
    try:
        return execute(action)
    except Exception as exc:
        cmds.confirmDialog(title='FFmpeg Playblast', message=str(exc), button=['OK'])
        cmds.warning(str(exc))
        return ''
    finally:
        _busy = False
