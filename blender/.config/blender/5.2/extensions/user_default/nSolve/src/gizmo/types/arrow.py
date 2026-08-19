import math

from mathutils import Matrix


class Draw:
    def __init__(self, gm, matrix_basis, color, alpha, scale_basis, offset=True, hide=False, hide_select=False, draw_options={'STEM'}):

        self.color = color
        self.alpha = alpha
        self.scale_basis = scale_basis

        # Create gizmo
        self.gizmo = self.create(gm, matrix_basis, offset, hide, hide_select, draw_options)

    def create(self, gm, matrix_basis, offset, hide, hide_select, draw_options):

        gz = gm.gizmos.new("GIZMO_GT_arrow_3d")
        gz.color = self.color
        gz.color_highlight = self.color
        gz.alpha = self.alpha
        gz.scale_basis = self.scale_basis
        gz.matrix_basis = matrix_basis
        gz.hide = hide
        gz.hide_select = hide_select

        if offset:
            gz.use_draw_offset_scale = True
            gz.matrix_offset = Matrix.Translation((0, 0, 0.2))
            gz.length = 1.22
        else:
            gz.length = 1.42

        gz.line_width = 2
        gz.use_draw_value = False

        gz.draw_options = draw_options

        return gz

    def hide_stem(self, get=False):
        if get:
            self.gizmo.draw_options = set()
        else:
            self.gizmo.draw_options = {'STEM', 'ORIGIN'}

    def is_modal(self):
        return self.gizmo.is_modal

    def hide(self, get=False):
        if get:
            self.gizmo.hide = True
        else:
            self.gizmo.hide = False

    def operator(self, operator, properties=None):

        op_props = self.gizmo.target_set_operator(operator)
        if properties:
            for prop, value in properties.items():
                setattr(op_props, prop, value)

    def update(self, matrix_basis, view_direction, arrow_direction):

        gz = self.gizmo

        gz.matrix_basis = matrix_basis
        gz.alpha = adjust_alpha_by_view_direction(view_direction, arrow_direction, self.alpha)


def adjust_alpha_by_view_direction(view_direction, arrow_direction, alpha=0.6):
    '''
    Adjust the alpha of the arrow based on the view direction and the arrow direction.

    :param view_direction: The direction the user is looking at the arrow from.
    :type view_direction: mathutils.Vector
    :param arrow_direction: The direction the arrow is pointing.
    :type arrow_direction: mathutils.Vector
    :param alpha: The alpha value to be adjusted.
    :type alpha: float
    :return: The adjusted alpha value.
    :rtype: float
    '''

    # Take the minimum angle between the arrow_direction and its negative
    angle_to_positive = float(view_direction.angle(arrow_direction))
    angle_to_negative = float(view_direction.angle(-arrow_direction))
    angle = min(angle_to_positive, angle_to_negative)

    # Convert the desired degrees to radians for comparison
    deg_a = math.radians(45)
    deg_b = math.radians(15)

    if angle > deg_a:
        return alpha
    elif angle < deg_b:
        return 0
    else:
        return alpha * (angle - deg_b) / (deg_a - deg_b)
