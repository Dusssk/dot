import bpy
from ...utility.object import smooth_batch_set


class HOPS_OT_SetSmooth(bpy.types.Operator):
    bl_idname = "hops.set_smooth"
    bl_label = "Set Shading"
    bl_description = "Set object smoothing"
    bl_options = {"REGISTER", "UNDO", 'INTERNAL'}


    smooth: bpy.props.BoolProperty()
    mode: bpy.props.EnumProperty(
        items= [
        ('ACTIVE', 'Active', 'Active only'),
        ('SELECT', 'Selectionm', 'Selection')
        ],
        default='ACTIVE'
    )

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'SCULPT'}

    def execute(self, context):

        objects = []

        if self.mode == 'ACTIVE':
            if context.active_object:
                objects = [context.active_object]

        else:
            objects = context.selected_objects

        smooth_batch_set(objects, self.smooth)

        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return {"FINISHED"}
