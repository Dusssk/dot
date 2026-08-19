import bpy
from ....utils import addon


class NSOLVE_OT_PlaceGizmo(bpy.types.Operator):
    bl_idname = "nsolve.place_gizmo"
    bl_label = "Place Gizmo"
    bl_description = "Set Gizmo"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    gizmo: bpy.props.EnumProperty(name="Gizmo", description="Gizmo", items=[('NSU', 'NSU Gizmo', 'NSU Gizmo'), ('NSO', 'NSO Gizmo', 'NSO Gizmo')], default='NSO')

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def execute(self, context):

        if self.gizmo == 'NSO':
            nsolve = addon.pref().tools.nsolve
            nsolve.main_gizmo_location = (15, 60)
            nsolve.main_gizmo_scale = 46
            nsolve.main_gizmo_flip = False
            nsolve.nso.hide = True

        elif self.gizmo == 'NSU':
            nsuite = addon.pref().tools.nsuite

            nsuite.ops_gizmo_location = (45, 20)
            nsuite.ops_gizmo_scale = 44
            nsuite.ops_gizmo_flip = True
            nsuite.nsu.hide = True
            nsolve = addon.pref().tools.nsolve
            nsolve.nsu.hide = True

        return {'FINISHED'}
