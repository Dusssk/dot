import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *


class Select_Any(NFlowBehavior):
    undo_message = 'Select'

    def invoke(self, context, event):
        mouse_pos = self.invoke_mouse_pos
        
        if context.mode == 'OBJECT':
            self.selection_helper.init_object(context, mouse_pos)
        elif context.mode == 'EDIT_MESH':
            self.selection_helper.init_mesh(context, mouse_pos,
                self.obj, self.bm, self.elem_type, self.elements)
        
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.selection_helper.on_mousemove(context, event)
        elif event.type in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE'):
            self.selection_helper.on_wheel(context, event)
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            return 'FINISHED'
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.selection_helper.on_cancel(context)
            return 'CANCELLED'


NFlow.behaviors['nFlow: Select'] = dict(
    type=Select_Any,
    description='Select or deselect objects or elements',
    cursor='COPY',
    elements={'NONE', 'VERTEX', 'EDGE', 'EDGE_LOOP', 'BOUNDARY', 'PERIMETER', 'FACE'},
    options=[],
    context_modes={'EDIT_MESH', 'OBJECT'},
)
