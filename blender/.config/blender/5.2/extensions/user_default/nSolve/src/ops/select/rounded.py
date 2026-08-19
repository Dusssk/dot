import bpy
import bmesh
from math import pi, degrees


from ... import analytics


class NSOLVE_OT_SelectRoundedArea(bpy.types.Operator):
    bl_idname = "nsolve.select_rounded_area"
    bl_label = "Select Rounded Area"
    bl_description = "Select all faces contributing to a rounded area based on angle threshold and relative size."
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    angle_threshold: bpy.props.FloatProperty(
        name="Angle Threshold",
        description="Maximum angle (in radians) between adjacent face normals to consider them part of the same rounded area",
        default=pi/6,  # Default threshold angle in radians
        min=0.0,
        max=2*pi,  # Max angle in radians
        subtype='ANGLE'
    )

    size_ratio_threshold: bpy.props.FloatProperty(
        name="Size Ratio Threshold",
        description="Maximum size ratio relative to the initially selected faces to consider for selection",
        default=2.0,  # Default size ratio threshold
        min=1.0,  # Minimum size ratio (equal size to the selected face)
        max=10.0,  # Arbitrary upper limit for the size ratio
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Select Rounded Area|Angle Threshold: {round(degrees(self.angle_threshold), 1)}|Size Ratio Threshold: {self.size_ratio_threshold}", position=(50, 2))
        return self.execute(context)

    def find_adjacent_faces(self, bm, face):
        '''Find adjacent faces to the given face.'''
        adjacent_faces = set()
        for edge in face.edges:
            for linked_face in edge.link_faces:
                if linked_face != face:
                    adjacent_faces.add(linked_face)
        return adjacent_faces

    def select_rounded_area(self, bm, initial_face, max_area):
        faces_to_check = {initial_face}
        selected_faces = {initial_face}
        angle_limit = self.angle_threshold  # Already in radians, no need to convert

        while faces_to_check:
            current_face = faces_to_check.pop()
            for adjacent_face in self.find_adjacent_faces(bm, current_face):
                if adjacent_face not in selected_faces:
                    angle_between_faces = current_face.normal.angle(adjacent_face.normal)
                    if angle_between_faces <= angle_limit and adjacent_face.calc_area() <= max_area:
                        adjacent_face.select = True
                        selected_faces.add(adjacent_face)
                        faces_to_check.add(adjacent_face)

    def execute(self, _context):
        obj = bpy.context.edit_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        initial_selected_faces = [f for f in bm.faces if f.select]

        if not initial_selected_faces:
            self.report({'WARNING'}, "No face selected")
            return {'CANCELLED'}

        # Calculate the maximum face area based on the selected faces and the size ratio threshold
        max_initial_area = max(f.calc_area() for f in initial_selected_faces)
        max_area = max_initial_area * self.size_ratio_threshold

        for initial_face in initial_selected_faces:
            self.select_rounded_area(bm, initial_face, max_area)

        bmesh.update_edit_mesh(mesh)
        analytics.stats("nSuite: Offset Edges")
        return {'FINISHED'}
