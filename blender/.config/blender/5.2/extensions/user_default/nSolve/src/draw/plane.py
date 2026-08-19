import gpu

from gpu_extras.batch import batch_for_shader
from mathutils import Vector


class DrawPlane:
    def __init__(self, point, normal, length, color):
        self.point = Vector(point)
        self.normal = Vector(normal)
        self.length = length
        self.color = color

        # Create a shader and batch
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.batch = self.create_batch()

    def create_batch(self):
        vertices = self.calculate_quad_vertices(self.point, self.normal)
        indices = [(0, 1, 2), (0, 2, 3)]
        attributes = {"pos": vertices}

        # Create a batch for the shader
        return batch_for_shader(self.shader, 'TRIS', attributes, indices=indices)

    def update_batch(self, point, normal):
        vertices = self.calculate_quad_vertices(point, normal)
        indices = [(0, 1, 2), (0, 2, 3)]
        attributes = {"pos": vertices}

        # Update batch for the shader
        self.batch = batch_for_shader(self.shader, 'TRIS', attributes, indices=indices)

    def calculate_quad_vertices(self, point, normal):
        length = self.length

        ortho1 = normal.cross(Vector([-normal.y, normal.x, 0]))
        if ortho1.length < 1e-8:
            ortho1 = normal.cross(Vector([0, -normal.z, normal.y]))

        ortho2 = normal.cross(ortho1)

        ortho1.normalize()
        ortho2.normalize()

        half_length = length / 2

        v1 = point + (ortho1 + ortho2) * half_length
        v2 = point + (-ortho1 + ortho2) * half_length
        v3 = point + (-ortho1 - ortho2) * half_length
        v4 = point + (ortho1 - ortho2) * half_length

        return [tuple(v1), tuple(v2), tuple(v3), tuple(v4)]

    def draw(self, _context):
        # Draw the batch
        self.shader.bind()
        self.shader.uniform_float('color', self.color)

        gpu.state.blend_set('ALPHA')

        self.batch.draw(self.shader)
