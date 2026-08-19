import bpy


class NSOLVE_MT_VertMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_VertMenu"
    bl_label = "Vert"

    def draw(self, _context):
        layout = self.layout

        layout.operator("nsolve.collapse_verts").detect_vert = False
        layout.separator()
        layout.operator("nsolve.project_circle")
