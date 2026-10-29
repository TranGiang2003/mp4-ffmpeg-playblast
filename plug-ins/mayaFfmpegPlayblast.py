"""Python API 2 plugin entry point."""
def maya_useNewAPI():
    pass


def initializePlugin(obj):
    from maya.api import OpenMaya
    from maya import cmds, utils
    OpenMaya.MFnPlugin(obj, 'Maya FFmpeg Playblast', '0.5.0', 'Any')
    if not cmds.about(batch=True):
        from maya_ffmpeg_playblast import integration
        utils.executeDeferred(integration.install)


def uninitializePlugin(obj):
    from maya_ffmpeg_playblast import integration
    integration.uninstall()
