"""Keep capture attached to the existing viewport and its loaded texture previews."""
from maya import cmds


def capture_options(offscreen):
    editor = cmds.playblast(activeEditor=True)
    if not editor:
        raise RuntimeError('Activate your camera viewport before opening Playblast Options.')
    tiled = any(cmds.getAttr(node + '.uvTilingMode') != 0
                for node in (cmds.ls(type='file') or []))
    if tiled and offscreen:
        cmds.warning('FFmpeg Playblast: tiled textures detected; using the visible viewport '
                     'to preserve UV-tile previews. Keep Maya visible during capture. '
                     'Output size may be limited by the viewport.')
    # Do not regenerate previews, reload files, reset OGS, or alter shading settings.
    return dict(editorPanelName=editor, offScreen=bool(offscreen and not tiled),
                clearCache=False)
