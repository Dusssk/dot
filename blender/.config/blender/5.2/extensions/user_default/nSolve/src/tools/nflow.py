import os
from pathlib import Path

import bpy

from ...icons.menus import get_icon_id

from ..ops.nflow.common import *
from ...import bl_info


class NSOLVE_MT_NFlow_base(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_label = 'nFlow'
    bl_description = f'Version: {bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}'
    bl_icon = (Path(__file__).parent.parent.parent / 'icons' / 'tools' / 'NTX').as_posix()
    bl_widget = ''
    bl_keymap = (
        ('nsolve.nflow', {'type': 'MOUSEMOVE', 'value': 'ANY', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'LEFT_CTRL', 'value': 'ANY', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'LEFT_SHIFT', 'value': 'ANY', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'LEFT_ALT', 'value': 'ANY', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'RIGHT_CTRL', 'value': 'ANY', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'RIGHT_SHIFT', 'value': 'ANY', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'RIGHT_ALT', 'value': 'ANY', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'LEFTMOUSE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'BEGIN')]}),
        ('nsolve.nflow', {'type': 'MIDDLEMOUSE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'BEGIN')]}),
        ('nsolve.nflow', {'type': 'RIGHTMOUSE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'BEGIN')]}),
        ('nsolve.nflow', {'type': 'WHEELUPMOUSE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'WHEELDOWNMOUSE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'PAGE_UP', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'PAGE_DOWN', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'LEFT_ARROW', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'RIGHT_ARROW', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'ONE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'TWO', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'THREE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'FOUR', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'FIVE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'SIX', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'SEVEN', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'EIGHT', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'NINE', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.nflow', {'type': 'ZERO', 'value': 'PRESS', 'any': True}, {'properties': [('invoke_mode', 'HOVER')]}),
        ('nsolve.helper', {'type': 'D', 'value': 'PRESS'}, {'properties': []}),
    )

    def draw_settings(context, layout, tool):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        is_active = nflow_config_workspace.is_active
        layout.operator('nsolve.helper', text='', icon_value=get_icon_id('nflow'), depress=is_active)
        layout.label(text=f'{bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}')

        layout.separator_spacer()

        draw_tool_header = NFlowPrefs.get('draw_tool_header')
        draw_tool_header(layout, context)


class NSOLVE_MT_NFlow_object_mode(NSOLVE_MT_NFlow_base):
    bl_context_mode = 'OBJECT'
    bl_idname = 'nsolve.nflow_object_mode'


class NSOLVE_MT_NFlow_edit_mode(NSOLVE_MT_NFlow_base):
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'nsolve.nflow_edit_mode'


classes = (
)
