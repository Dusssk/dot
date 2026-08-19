import bmesh
import bpy

from ....utils import addon


class NSOLVE_OT_NdrawDraw(bpy.types.Operator):
    bl_idname = "nsolve.ndraw_draw"
    bl_label = "nDraw"
    bl_description = ""
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR'}

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return True

    def invoke(self, context, event):

        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"nDraw Draw", position=(50, 2))
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not context.mode == 'EDIT_MESH':
            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE' and event.ctrl:

            addon.pref().tools.ndraw.running = True

            ndraw = addon.pref().tools.ndraw
            ndraw.running = True
            pencil_mode = ndraw.pencil_mode

            bpy.ops.nsolve.pencil('INVOKE_DEFAULT', mode=pencil_mode)
            return {'FINISHED'}

        return {'PASS_THROUGH'}
