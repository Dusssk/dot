from math import pi, degrees
import bpy
import bmesh

from ... import analytics


def traverse_and_select_edges(operator, bm, current_edge, start_vert):
    '''Traverse and select edges based on angle'''

    def angle_between_edges(edge1, edge2, shared_vert):
        vec1 = (edge1.other_vert(shared_vert).co - shared_vert.co).normalized()
        vec2 = (edge2.other_vert(shared_vert).co - shared_vert.co).normalized()
        if vec1.length == 0 or vec2.length == 0:
            return None  # Stop if any vector has zero length
        return vec1.angle(vec2)

    def find_next_edge(current_edge, start_vert):
        if any(edge.select for edge in start_vert.link_edges if edge != current_edge):
            return None  # Stop if any connected edge is already selected

        eligible_edges = []
        for edge in start_vert.link_edges:
            if edge == current_edge or edge.select:
                continue
            angle = angle_between_edges(current_edge, edge, start_vert)
            if angle is None:
                return None  # Stop traversal if zero-length vector is found
            if operator.start_angle <= angle <= operator.end_angle:
                eligible_edges.append((edge, angle))

        if not eligible_edges:
            return None

        # Find the edge with the largest angle
        next_edge, _ = max(eligible_edges, key=lambda item: item[1])

        # Check if the edge's faces are tris or ngons
        for face in next_edge.link_faces:
            if operator.stop_at_tris and len(face.verts) == 3:
                return None  # Stop at tris
            if operator.stop_at_ngon and len(face.verts) > 4:
                return None  # Stop at ngons

        return next_edge

    while current_edge:
        next_edge = find_next_edge(current_edge, start_vert)
        if next_edge:
            next_edge.select = True
            bm.edges.ensure_lookup_table()
            start_vert = next_edge.other_vert(start_vert)
            current_edge = next_edge
        else:
            break


class NSOLVE_OT_SelectSmartLoop(bpy.types.Operator):
    bl_idname = "nsolve.select_smartloop"
    bl_label = "Select Loop"
    bl_description = "Traverses edges based on angle, stopping if a connected edge is selected or if the vertex is part of a tris/ngon based on user settings."
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    edge_id: int = -1

    extend: bpy.props.BoolProperty(
        name="Extend Selection",
        description="Extend the selection instead of replacing it",
        default=True
    )

    start_angle: bpy.props.FloatProperty(
        name="Above Angle",
        description="Minimum angle for edge selection",
        default=0.0,
        min=0.0,
        max=pi,
        unit='ROTATION',
        subtype='ANGLE',
        step=10
    )

    end_angle: bpy.props.FloatProperty(
        name="Below Angle",
        description="Maximum angle for edge selection",
        default=pi,
        min=0.0,
        max=pi,
        unit='ROTATION',
        subtype='ANGLE',
        step=10
    )

    stop_at_tris: bpy.props.BoolProperty(
        name="Stop at Tris",
        description="Stop traversing when the vertex is part of a triangle",
        default=False
    )

    stop_at_ngon: bpy.props.BoolProperty(
        name="Stop at Ngons",
        description="Stop traversing when the vertex is part of an ngon",
        default=False
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "This operator only works in the 3D Viewport")
            return {'CANCELLED'}

        context.tool_settings.mesh_select_mode = (False, True, False)
        mouse = (event.mouse_region_x, event.mouse_region_y)
        bpy.ops.view3d.select(location=(mouse[0], mouse[1]), extend=self.extend)

        obj = bpy.context.edit_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        edge = bm.select_history.active
        self.edge_id = edge.index if edge else -1

        self.finish()
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Select Loop|Extend: {self.extend}|Angle Above: {round(degrees(self.start_angle), 1)}|Angle Below: {round(degrees(self.end_angle), 1)}|Stop at Tris: {self.stop_at_tris}|Stop at Ngons: {self.stop_at_ngon}", position=(50, 2))
        analytics.stats("nSuite: Select Loop")
        return {'FINISHED'}

    def finish(self):
        obj = bpy.context.edit_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        if self.edge_id >= 0:
            bm.edges.ensure_lookup_table()
            starting_edge = bm.edges[self.edge_id]
            starting_edge.select = True
            if not starting_edge:
                self.report({'WARNING'}, "Invalid edge index")
                return {'CANCELLED'}
        else:
            selected_edges = [e for e in bm.edges if e.select]
            if not selected_edges:
                self.report({'WARNING'}, "No edge selected")
                return {'CANCELLED'}

            starting_edge = selected_edges[0]

        # First traversal from the first vertex of the starting edge
        first_vert = starting_edge.verts[0]
        traverse_and_select_edges(self, bm, starting_edge, first_vert)

        # Second traversal from the opposite vertex of the starting edge
        second_vert = starting_edge.verts[1]
        traverse_and_select_edges(self, bm, starting_edge, second_vert)

        bmesh.update_edit_mesh(me)


class NSOLVE_OT_SelectMultiSmartLoop(bpy.types.Operator):
    bl_idname = "nsolve.select_multi_smartloop"
    bl_label = "Select Loop"
    bl_description = "Traverses edges based on angle, stopping if a connected edge is selected or if the vertex is part of a tris/ngon based on user settings."
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    start_angle: bpy.props.FloatProperty(
        name="Above Angle",
        description="Minimum angle for edge selection",
        default=0.0,
        min=0.0,
        max=pi,
        unit='ROTATION',
        subtype='ANGLE',
        step=10
    )

    end_angle: bpy.props.FloatProperty(
        name="Below Angle",
        description="Maximum angle for edge selection",
        default=pi,
        min=0.0,
        max=pi,
        unit='ROTATION',
        subtype='ANGLE',
        step=10
    )

    stop_at_tris: bpy.props.BoolProperty(
        name="Stop at Tris",
        description="Stop traversing when the vertex is part of a triangle",
        default=False
    )

    stop_at_ngon: bpy.props.BoolProperty(
        name="Stop at Ngons",
        description="Stop traversing when the vertex is part of an ngon",
        default=False
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Select Loop|Angle Above: {round(degrees(self.start_angle), 1)}|Angle Below: {round(degrees(self.end_angle), 1)}|Stop at Tris: {self.stop_at_tris}|Stop at Ngons: {self.stop_at_ngon}", position=(50, 2))
        exetute = self.execute(context)
        analytics.stats("nSuite: Select Loop")
        return exetute

    def execute(self, _context):
        obj = bpy.context.edit_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        selected_edges = [e for e in bm.edges if e.select]

        if not selected_edges:
            self.report({'WARNING'}, "No edge selected")
            return {'CANCELLED'}

        for edge in selected_edges:
            # First traversal from the first vertex of the starting edge
            first_vert = edge.verts[0]
            traverse_and_select_edges(self, bm, edge, first_vert)

            # Second traversal from the opposite vertex of the starting edge
            second_vert = edge.verts[1]
            traverse_and_select_edges(self, bm, edge, second_vert)

        bmesh.update_edit_mesh(me)
        return {'FINISHED'}
