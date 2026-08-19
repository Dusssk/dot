import gpu

from gpu_extras.batch import batch_for_shader
from mathutils import Vector


class DrawLine:
    def __init__(self, points, width, color, depth=False):
        self.points = [Vector(p) for p in points]  # Ensure points are Vector objects
        self.width = width
        self.color = color
        self.depth = depth

        self.shader = gpu.shader.from_builtin('POLYLINE_FLAT_COLOR')
        self.batch = self.create_batch()

    def create_batch(self):
        return self.setup_batch(self.points, self.color)

    def update_batch(self, points, color=None):
        self.points = [Vector(p) for p in points]  # Update points
        if color is not None:
            self.color = color  # Update color only if a new one is provided
        self.batch = self.setup_batch(self.points, self.color)

    def setup_batch(self, points, color):
        # Compute direction of the line
        direction = (points[1] - points[0]).normalized()

        # Extend the line by a large factor to make it appear "infinite"
        extension_factor = 1e4
        point_a_far = points[0] - direction * extension_factor
        point_b_far = points[1] + direction * extension_factor

        # Prepare the vertices and indices
        vertices = [point_a_far[:], point_b_far[:]]
        indices = [(0, 1)]

        # Prepare the color for each vertex (required for POLYLINE_FLAT_COLOR)
        vertex_colors = [color for _ in vertices]

        # Create or update the batch for the shader
        return batch_for_shader(self.shader, 'LINES', {"pos": vertices, "color": vertex_colors}, indices=indices)

    def draw(self, context):
        width = context.area.width
        height = context.area.height

        # Adjust for quad view if necessary
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        if self.depth:
            gpu.state.depth_test_set('GREATER_EQUAL')
        else:
            gpu.state.depth_test_set('NONE')
        self.shader.bind()
        self.shader.uniform_float('viewportSize', (width, height))
        self.shader.uniform_float('lineWidth', self.width)

        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)
