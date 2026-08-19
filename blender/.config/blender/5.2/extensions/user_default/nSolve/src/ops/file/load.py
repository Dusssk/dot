import bpy
import os


class NSOLVE_OT_LoadFile(bpy.types.Operator):
    bl_idname = "nsolve.load_file"
    bl_label = "Load File"
    bl_description = "Load File"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    filepath: bpy.props.StringProperty(name="File Path", default="")

    def execute(self, context):
        # Ensure the file path is valid
        if os.path.exists(self.filepath):
            bpy.ops.wm.open_mainfile(filepath=self.filepath)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"File not found: {self.filepath}")
            return {'CANCELLED'}
