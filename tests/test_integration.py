"""Regression tests for the native callback bridge; run with mayapy."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from maya_ffmpeg_playblast import integration as ui


class ParentRegression(unittest.TestCase):
    def test_native_format_keeps_parent(self):
        with patch.object(ui, 'cmds') as cmds, patch.object(ui, 'call') as call:
            cmds.optionMenuGrp.return_value = 'avi'
            ui.format_changed('playblastOptionsWindow')
            call.assert_called_once_with('changePlayblastFormat', 'playblastOptionsWindow')

    def test_setup_preserves_custom_selection_across_native_refresh(self):
        with patch.object(ui, 'cmds') as cmds, patch.object(ui, 'call') as call, \
                patch.object(ui, 'enabled', return_value=True), \
                patch.object(ui, 'format_changed') as changed:
            cmds.optionMenuGrp.return_value = []
            ui.setup('playblastOptionsWindow', 0)
            changed.assert_called_once_with('playblastOptionsWindow')
            cmds.optionMenuGrp.assert_any_call('playblastFormatWidget', e=True, value=ui.LABEL)

    def test_reset_does_not_restore_custom_format(self):
        with patch.object(ui, 'cmds') as cmds, patch.object(ui, 'call'), \
                patch.object(ui, 'enabled', return_value=True), \
                patch.object(ui, 'format_changed') as changed:
            cmds.optionMenuGrp.return_value = []
            ui.setup('playblastOptionsWindow', 1)
            changed.assert_not_called()


if __name__ == '__main__':
    unittest.main()
