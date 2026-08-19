import bpy
import bmesh

from ... import analytics


class NSOLVE_OT_SelectSimilarStrip(bpy.types.Operator):
    bl_idname = "nsolve.select_similar_strip"
    bl_label = "Select Similar Strip"
    bl_description = "Select a strip of similar quads along both directions of the specified axis."
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        name="Direction",
        description="Select the direction of strip expansion",
        items=[
            ('X', "X Axis", "Expand along the X axis (longer horizontal edges)"),
            ('Y', "Y Axis", "Expand along the Y axis (longer vertical edges)")
        ],
        default='X'
    )

    area_variation: bpy.props.FloatProperty(
        name="Area Variation",
        description="Percentage by which the area of the face can differ from the selected face",
        default=0.2,  # 2% variation by default
        min=0.0,       # 0% means exactly the same area
        max=2.0,       # 100% variation
        subtype='PERCENTAGE'
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Select Similar Strip|Direction: {self.direction}|Area Variation: {self.area_variation}", position=(50, 2))
        analytics.stats("nSuite: Select Similar Strip")
        return self.execute(context)

    def find_opposite_edges(self, face, start_edges):
        '''Find edges opposite to the start_edges in a quad.'''
        if len(face.edges) != 4:
            return None
        edges_list = list(face.edges)
        return [edges_list[(edges_list.index(e) + 2) % 4] for e in start_edges]

    def traverse_strip(self, start_face, start_edges, max_variation):
        '''Traverse along a strip of similar faces starting from start_face along both directions of start_edges.'''
        face_queue = [(start_face, edge) for edge in start_edges]
        selected_faces = {start_face}
        start_face.select = True
        start_area = start_face.calc_area()

        while face_queue:
            current_face, current_edge = face_queue.pop(0)
            opposite_edges = self.find_opposite_edges(current_face, [current_edge])
            if opposite_edges is None:
                continue

            for opp_edge in opposite_edges:
                for linked_face in opp_edge.link_faces:
                    if linked_face not in selected_faces and len(linked_face.verts) == 4:
                        linked_area = linked_face.calc_area()
                        area_diff = abs(linked_area - start_area) / start_area
                        if area_diff <= max_variation:
                            linked_face.select = True
                            selected_faces.add(linked_face)
                            face_queue.append((linked_face, opp_edge))

    def execute(self, context):
        obj = bpy.context.edit_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        initial_selected_faces = [f for f in bm.faces if f.select and len(f.verts) == 4]
        if not initial_selected_faces:
            self.report({'WARNING'}, "No suitable quad face selected")
            return {'CANCELLED'}

        # Determine start_edges based on the chosen direction

        last_selected_face = -1
        if hasattr(bm, 'select_history') and bm.select_history:
            last_selected_face = bm.select_history[-1]
        if last_selected_face in initial_selected_faces:
            initial_face = last_selected_face
        else:
            initial_face = initial_selected_faces[0]

        edges_list = list(initial_face.edges)
        sorted_edges = sorted(edges_list, key=lambda e: (e.verts[0].co - e.verts[1].co).length)
        start_edges = sorted_edges[:2] if self.direction == 'X' else sorted_edges[2:]

        self.traverse_strip(initial_face, start_edges, self.area_variation)

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}
