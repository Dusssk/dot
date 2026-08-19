import bpy


class NSOLVE_MT_EdgeMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_EdgeMenu"
    bl_label = "Edge"

    def draw(self, _context):
        layout = self.layout

        layout.operator("nsolve.hard_loop_cut").release_confirm = False
        layout.operator("mesh.loopcut_slide").TRANSFORM_OT_edge_slide.release_confirm = False
        layout.separator()
        layout.operator("nsolve.hard_edge_slide")
        layout.operator("nsolve.offset_edges")
        layout.separator()
        layout.operator("nsolve.bevel")
        layout.separator()
        layout.operator("nsolve.project_loop", text="Project Loop").mode = 'OFFSET'
