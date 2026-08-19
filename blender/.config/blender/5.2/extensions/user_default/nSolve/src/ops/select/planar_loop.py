import bpy
import bmesh
from mathutils import Vector

from ... import analytics


def calculate_plane_normal(edge):
    '''Calculate the plane normal of the edge's linked faces'''

    face_normals = [face.normal for face in edge.link_faces]
    if not face_normals:
        return None
    median_normal = sum(face_normals, Vector((0.0, 0.0, 0.0))) / len(face_normals)
    edge_vector = (edge.verts[1].co - edge.verts[0].co).normalized()
    plane_normal = edge_vector.cross(median_normal).normalized()
    if plane_normal == Vector((0.0, 0.0, 0.0)):
        return None
    return plane_normal


def traverse_and_select_edges(starting_edge):
    '''Traverse and select edges based on plane normal'''

    def check_and_select_edge(edge, plane_normal):
        '''Check if the edge's plane normal is similar to the initial edge's plane normal'''

        next_plane_normal = calculate_plane_normal(edge)
        if next_plane_normal and plane_normal.angle(next_plane_normal) < 0.01:  # Tolerance for angle comparison
            edge.select = True
            return True
        return False

    initial_plane_normal = calculate_plane_normal(starting_edge)
    if initial_plane_normal is None:
        return

    for vert in starting_edge.verts:
        current_vert = vert
        current_edge = starting_edge
        while True:
            next_edges = [e for e in current_vert.link_edges if e != current_edge and not e.select]
            for next_edge in next_edges:
                plane_normal = calculate_plane_normal(next_edge)
                if plane_normal and initial_plane_normal.angle(plane_normal) < 0.01:
                    if check_and_select_edge(next_edge, initial_plane_normal):
                        next_vert = next_edge.other_vert(current_vert)
                        current_vert = next_vert
                        current_edge = next_edge
                        break
            else:
                break


class NSOLVE_OT_SelectPlanarLoop(bpy.types.Operator):
    bl_idname = "nsolve.select_planarloop"
    bl_label = "Select Planar Loop"
    bl_description = "Traverses edges sharing the same plane normal."
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    edge_id: int = -1

    extend: bpy.props.BoolProperty(
        name="Extend Selection",
        description="Extend the selection instead of replacing it",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        context.tool_settings.mesh_select_mode = (False, True, False)
        mouse = (event.mouse_region_x, event.mouse_region_y)
        bpy.ops.view3d.select(location=(mouse[0], mouse[1]), extend=self.extend)

        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        edge = bm.select_history.active
        self.edge_id = edge.index if edge else -1

        self.finish(context)
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Select Planar Loop|Extend: {self.extend}", position=(50, 2))
        analytics.stats("nSuite: Select Planar Loop")
        return {'FINISHED'}

    def finish(self, context):
        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        if self.edge_id >= 0:
            bm.edges.ensure_lookup_table()
            starting_edge = bm.edges[self.edge_id]
            starting_edge.select = True
        else:
            selected_edges = [e for e in bm.edges if e.select]
            if not selected_edges:
                self.report({'WARNING'}, "No edge selected")
                return {'CANCELLED'}

            starting_edge = selected_edges[0]

        traverse_and_select_edges(starting_edge)

        bmesh.update_edit_mesh(me)


class NSOLVE_OT_SelectMultiPlanarLoop(bpy.types.Operator):
    bl_idname = "nsolve.select_multi_planarloop"
    bl_label = "Select Planar Loop"
    bl_description = "Traverses edges sharing the same plane normal."
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text="Select Planar Loop|Extend: True", position=(50, 2))
        analytics.stats("nSuite: Select Planar Loop")
        return self.execute(context)

    def execute(self, context):
        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        selected_edges = [e for e in bm.edges if e.select]
        if not selected_edges:
            self.report({'WARNING'}, "No edge selected")
            return {'CANCELLED'}

        for edge in selected_edges:
            traverse_and_select_edges(edge)

        bmesh.update_edit_mesh(me)
        return {'FINISHED'}
