import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from maya_ffmpeg_playblast import viewport


class TextureCapture(unittest.TestCase):
    def test_udim_uses_existing_visible_editor_without_cache_mutation(self):
        with patch.object(viewport, 'cmds') as cmds:
            cmds.playblast.return_value = 'modelPanel4'
            cmds.ls.return_value = ['rig:file1']
            cmds.getAttr.return_value = 3
            result = viewport.capture_options(True)
            self.assertEqual(result, dict(editorPanelName='modelPanel4', offScreen=False, clearCache=False))
            cmds.playblast.assert_called_once_with(activeEditor=True)
            cmds.ogs.assert_not_called()
            cmds.setAttr.assert_not_called()
            cmds.refresh.assert_not_called()
            cmds.warning.assert_called_once()

    def test_ordinary_capture_keeps_requested_offscreen_setting(self):
        with patch.object(viewport, 'cmds') as cmds:
            cmds.playblast.return_value = 'modelPanel4'
            cmds.ls.return_value = []
            self.assertTrue(viewport.capture_options(True)['offScreen'])
            cmds.warning.assert_not_called()

    def test_missing_editor_stops_capture(self):
        with patch.object(viewport, 'cmds') as cmds:
            cmds.playblast.return_value = ''
            with self.assertRaises(RuntimeError):
                viewport.capture_options(True)


if __name__ == '__main__':
    unittest.main()
