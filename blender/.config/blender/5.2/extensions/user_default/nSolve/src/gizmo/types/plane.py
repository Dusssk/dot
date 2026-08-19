from mathutils import Matrix


class Draw:
    def __init__(self, gm, matrix_basis, color, alpha, scale_basis, offset=(0, 0, 0), hide_select=False):

        self.color = color
        self.alpha = alpha
        self.scale_basis = scale_basis

        # Create gizmo
        self.gizmo = self.create(gm, matrix_basis, offset, hide_select)

    def create(self, gm, matrix_basis, offset, hide_select):
        # Define gizmos for X arrow (Red)
        gz = gm.gizmos.new("GIZMO_GT_primitive_3d")
        gz.color = self.color
        gz.color_highlight = self.color
        gz.alpha = self.alpha
        gz.scale_basis = self.scale_basis
        gz.matrix_basis = matrix_basis
        gz.draw_style = 'PLANE'
        gz.line_width = 1
        gz.select_bias = -3.0
        gz.use_draw_modal = True
        gz.hide_select = hide_select

        gz.use_draw_offset_scale = True
        x, y, z = offset
        local_offset = Matrix.Translation((x, y, z))
        gz.matrix_offset = local_offset

        return gz

    def is_modal(self):
        return self.gizmo.is_modal

    def hide(self, set=False):
        if set:
            self.gizmo.hide = True
        else:
            self.gizmo.hide = False

    def operator(self, operator, properties=None):

        op_props = self.gizmo.target_set_operator(operator)
        if properties:
            for prop, value in properties.items():
                setattr(op_props, prop, value)

    def update(self, context, matrix_basis, align_to_view=False):

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

        # Set the matrix_basis and matrix_offset of the gizmo
        self.gizmo.matrix_basis = location_matrix @ aligned_rotation
