import math

from mathutils import Matrix


class Draw:
    def __init__(self, gm, matrix_basis, color, line_width, alpha, scale_basis):

        self.color = color
        self.alpha = alpha
        self.scale_basis = scale_basis

        # Create gizmo
        self.gizmo = self.create(gm, matrix_basis, line_width)

    def create(self, gm, matrix_basis, line_width):
        # Define gizmos for X arrow (Red)
        gz = gm.gizmos.new("GIZMO_GT_dial_3d")
        gz.color = self.color
        gz.color_highlight = self.color
        gz.alpha = self.alpha
        gz.scale_basis = self.scale_basis
        gz.matrix_basis = matrix_basis
        gz.draw_options = {'CLIP'}
        # gz.click_value = math.radians(90)
        gz.incremental_angle = math.radians(15)
        # gz.arc_partial_angle = math.radians(90)
        # gz.arc_inner_factor = 0.9
        gz.wrap_angle = False
        gz.line_width = line_width
        gz.select_bias = -1
        gz.use_draw_modal = True

        return gz

    def is_modal(self):
        return self.gizmo.is_modal

    def hide(self, set=False):
        if set:
            self.gizmo.hide = True
        else:
            self.gizmo.hide = False

    def operator(self, context, operator, properties=None):

        self.gizmo.target_set_prop("offset", context.scene.boxcutter.gizmo, "rotation")

        op_props = self.gizmo.target_set_operator(operator)
        if properties:
            for prop, value in properties.items():
                setattr(op_props, prop, value)

    def update(self, context, matrix_basis, align_to_view=False):
        if self.gizmo.is_modal:
            self.gizmo.draw_options = {'ANGLE_VALUE'}
        else:
            self.gizmo.draw_options = {'CLIP'}

        if align_to_view:
            self.align_to_view(context, matrix_basis)
        else:
            self.gizmo.matrix_basis = matrix_basis

    def align_to_view(self, context, matrix_basis):
        """Align the gizmo to face the current view while maintaining its world location."""
        # Getting the current view rotation matrix
        view_matrix = context.space_data.region_3d.view_matrix
        view_rotation = view_matrix.to_quaternion().to_matrix().to_4x4()

        # Reverse the rotation to make the gizmo face the viewer
        aligned_rotation = view_rotation.inverted()

        # Extract location from the passed matrix_basis
        location_matrix = Matrix.Translation(matrix_basis.to_translation())

        # Combine the reversed rotation with the passed location
        self.gizmo.matrix_basis = location_matrix @ aligned_rotation
