import bpy


class NSOLVE_MT_SelectMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_SelectMenu"
    bl_label = "Select"

    def draw(self, _context):
        layout = self.layout

        layout.operator_context = "INVOKE_DEFAULT"
        layout.operator("nsolve.select_multi_smartloop", text="Smart Loop")
        layout.operator("nsolve.select_multi_planarloop", text="Planar Loop")
        layout.separator()
        layout.operator("nsolve.select_similar_strip", text="Similar Strip")
        layout.operator("nsolve.select_rounded_area", text="Rounded")
