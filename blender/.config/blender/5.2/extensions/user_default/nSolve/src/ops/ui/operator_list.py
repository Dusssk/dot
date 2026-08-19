import bpy
from .... import __package__ as base_package

class NSOLVE_OT_add_operator_to_list(bpy.types.Operator):
    bl_idname = "nsolve.add_operator_to_list"
    bl_label = "Add Operator"
    bl_description = "Add a new operator to the list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        preferences = context.preferences.addons[base_package].preferences
        preferences.pie_operator_list.add()
        return {'FINISHED'}

class NSOLVE_OT_remove_operator_from_list(bpy.types.Operator):
    bl_idname = "nsolve.remove_operator_from_list"
    bl_label = "Remove Operator"
    bl_description = "Remove operator from the list"
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        preferences = context.preferences.addons[base_package].preferences
        preferences.pie_operator_list.remove(self.index)
        return {'FINISHED'}

classes = (
    NSOLVE_OT_add_operator_to_list,
    NSOLVE_OT_remove_operator_from_list,
)
