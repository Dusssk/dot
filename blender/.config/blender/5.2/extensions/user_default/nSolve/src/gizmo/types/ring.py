import bpy
from mathutils import Matrix, Vector
from math import cos, sin, pi


class NSOLVE_GT_Ring(bpy.types.Gizmo):
    bl_idname = "NSOLVE_GT_Ring"

    custom_shape = None

    def draw(self, context):
        if not hasattr(self, 'custom_shape'):
            self.build()
        self.draw_custom_shape(self.custom_shape)

    def test_select(self, context, location):
        # Add selection logic here if necessary
        return -1

    def build(self):
        num_verts = 32
        radius = 100.0
        verts = [(cos(2 * pi / num_verts * i) * radius, sin(2 * pi / num_verts * i) * radius, 0) for i in range(num_verts)]

        # Here we close the loop by connecting the last vertex to the first
        verts.append(verts[0])
        self.custom_shape = self.new_custom_shape('LINE_STRIP', verts)


class Draw:
    def __init__(self, gm, matrix_basis, color=(1, 1, 1), alpha=1.0):
        self.gm = gm
        self.matrix_basis = matrix_basis
        self.color = color
        self.alpha = alpha

        self.gizmo = self.create()

    def create(self):
        # Instantiate the custom ring gizmo
        gz = self.gm.gizmos.new("NSOLVE_GT_Ring")
        gz.color = self.color
        gz.alpha = self.alpha
        gz.matrix_basis = self.matrix_basis
        gz.build()  # This builds the custom geometry

        return gz

    def update(self, matrix_basis):
        self.gizmo.matrix_basis = matrix_basis

    def operator(self, operator, properties=None):
        op_props = self.gizmo.target_set_operator(operator)
        if properties:
            for prop, value in properties.items():
                setattr(op_props, prop, value)

    def hide(self, set=False):
        self.gizmo.hide = set

    def is_modal(self):
        return self.gizmo.is_modal
