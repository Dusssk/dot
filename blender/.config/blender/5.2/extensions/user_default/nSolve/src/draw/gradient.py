import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector


class DrawGradient:
    def __init__(self, points, colors):
        self.points = [Vector(pt) for pt in points]  # Ensure points are Vector objects
        self.colors = colors
        # Use the built-in shader for 2D smooth color drawing
        self.shader = gpu.shader.from_builtin('SMOOTH_COLOR')
        self.batch = self.create_batch()

    def create_batch(self):
        vertices = [point.to_2d() for point in self.points]
        colors = self.colors

        # Create the batch using the built-in shader
        return batch_for_shader(
            self.shader, 'TRIS',
            {
                "pos": vertices,
                "color": colors
            },
            indices=[(0, 1, 2), (2, 3, 0)]  # Two triangles to form a quad
        )

    def update_batch(self, points=None, colors=None):
        if points:
            self.points = [Vector(pt) for pt in points]
        if colors:
            self.colors = colors

        self.batch = self.create_batch()

    def draw(self, context):

        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)