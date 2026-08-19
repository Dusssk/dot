from pathlib import Path
import bpy

from ...utils import addon
from ... import bl_info

class NSOLVE_MT_Main(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = 'nsolve.main_tool'
    bl_label = "nSolve"
    bl_description = f'Version: {bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}'
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "tools" / "nsolve").as_posix()
    bl_widget = ''
    bl_keymap = (
        ('nsolve.swap_mode', {'type': 'LEFTMOUSE', 'value': 'PRESS'}, {'properties': [('tool', 'NSO')]}),
        ('nsolve.swap_mode', {'type': 'LEFTMOUSE', 'value': 'PRESS', 'ctrl': True}, {'properties': [('tool', 'NSU')]}),
        ('nsolve.helper', {'type': 'D', 'value': 'PRESS'}, {'properties': []}),
    )

    def draw_settings(context, layout, tool):

        # layout.operator('nsolve.show_logs', text='', icon='FILE_TEXT')
        layout.separator()
