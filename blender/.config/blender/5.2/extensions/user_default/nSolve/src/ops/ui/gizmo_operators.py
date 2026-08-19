import bpy
from .... import __package__ as base_package

class NSOLVE_OT_add_row_element(bpy.types.Operator):
    bl_idname = "nsolve.add_row_element"
    bl_label = "Add Element"
    bl_description = "Add a new element to the row"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()
    direction: bpy.props.StringProperty()

    def execute(self, context):
        preferences = context.preferences.addons[base_package].preferences
        columns = getattr(preferences, f"columns_{self.direction}")
        active_index = getattr(preferences, f"active_column_index_{self.direction}")
        row = columns[active_index].rows[self.index]
        element = row.elements.add()
        element.type = 'NONE'
        return {'FINISHED'}

class NSOLVE_OT_remove_row_element(bpy.types.Operator):
    bl_idname = "nsolve.remove_row_element"
    bl_label = "Remove Element"
    bl_description = "Remove element from row"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()
    element_index: bpy.props.IntProperty()
    direction: bpy.props.StringProperty()

    def execute(self, context):
        preferences = context.preferences.addons[base_package].preferences
        columns = getattr(preferences, f"columns_{self.direction}")
        active_index = getattr(preferences, f"active_column_index_{self.direction}")
        row = columns[active_index].rows[self.index]
        row.elements.remove(self.element_index)
        return {'FINISHED'}

class NSOLVE_OT_add_column_row(bpy.types.Operator):
    bl_idname = "nsolve.add_column_row"
    bl_label = "Add Row"
    bl_description = "Add a new row to the column"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.StringProperty()

    def execute(self, context):
        preferences = context.preferences.addons[base_package].preferences
        columns = getattr(preferences, f"columns_{self.direction}")
        active_index = getattr(preferences, f"active_column_index_{self.direction}")
        row = columns[active_index].rows.add()
        row.type = 'NONE'
        return {'FINISHED'}

class NSOLVE_OT_remove_column_row(bpy.types.Operator):
    bl_idname = "nsolve.remove_column_row"
    bl_label = "Remove Row"
    bl_description = "Remove row from column"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()
    direction: bpy.props.StringProperty()

    def execute(self, context):
        preferences = context.preferences.addons[base_package].preferences
        columns = getattr(preferences, f"columns_{self.direction}")
        active_index = getattr(preferences, f"active_column_index_{self.direction}")
        columns[active_index].rows.remove(self.index)
        return {'FINISHED'}

classes = (
    NSOLVE_OT_add_row_element,
    NSOLVE_OT_remove_row_element,
    NSOLVE_OT_add_column_row,
    NSOLVE_OT_remove_column_row,
)
