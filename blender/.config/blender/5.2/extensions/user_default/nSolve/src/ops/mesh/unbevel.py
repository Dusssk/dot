import bpy
import bmesh

from ... import analytics


class NSOLVE_OT_Unbevel(bpy.types.Operator):
    bl_idname = "nsolve.unbevel"
    bl_label = "Unbevel"
    bl_description = f"{bl_label}\n\nConvert beveled polygons back to single edge"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH':
            return True
        return False

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)

        # Ensure selection mode is edge
        bpy.context.tool_settings.mesh_select_mode = (False, True, False)

        # Get all selected edges
        selected_edges = [e for e in bm.edges if e.select]
        if len(selected_edges) < 3:
            self.report({'ERROR'}, "Please select a beveled edge strip.")
            return {'CANCELLED'}

        # Collect all selected faces
        selected_faces = {f for f in bm.faces if f.select}

        # Finding boundary edges
        boundary_edges = []
        for e in selected_edges:
            connected_faces = [f for f in e.link_faces if f in selected_faces]
            if len(connected_faces) == 1:
                if all(sum(1 for f in v.link_faces if f in selected_faces) == 1 for v in e.verts):
                    boundary_edges.append(e)

        if len(boundary_edges) != 2:
            self.report({'ERROR'}, "Selection does not form a proper strip or boundary edges not exactly two.")
            return {'CANCELLED'}

        # Dissolve selected edges connected to exactly two selected faces
        edges_to_dissolve = [e for e in selected_edges if len([f for f in e.link_faces if f in selected_faces]) == 2]
        if edges_to_dissolve:
            bmesh.ops.dissolve_edges(bm, edges=edges_to_dissolve, use_verts=True)

        # Connect vertices of boundary edges
        if len(boundary_edges) == 2:
            verts_0 = sorted(boundary_edges[0].verts, key=lambda v: v.index)
            verts_1 = sorted(boundary_edges[1].verts, key=lambda v: v.index)
            bmesh.ops.connect_verts(bm, verts=[verts_0[0], verts_1[0]])
            bmesh.ops.connect_verts(bm, verts=[verts_0[1], verts_1[1]])

        # Update mesh
        bmesh.update_edit_mesh(obj.data)
        analytics.stats("nSuite: Unbevel")
        return {'FINISHED'}
