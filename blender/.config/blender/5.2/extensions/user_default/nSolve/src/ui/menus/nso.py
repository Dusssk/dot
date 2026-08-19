import bpy
from .... import bl_info
from ....utils import addon


class NSOLVE_MT_NsoMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_NsoMenu"
    bl_label = f"nSolve: {bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        nsolve = addon.pref().tools.nsolve
        items = nsolve.main_gizmo_list_items

        for item in items:
            operator = layout.operator('nsolve.set_gizmo', text=item.operator.lower().capitalize())
            operator.gizmo = item.operator
            operator.mode = 'SET'
