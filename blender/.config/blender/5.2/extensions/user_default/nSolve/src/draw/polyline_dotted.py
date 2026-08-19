import gpu

from mathutils import Vector
from gpu_extras.batch import batch_for_shader

from ...shaders.POLYLINE_DOTTED_COLOR import shader_info


class DrawPolylineDotted:
    def __init__(self, points, width, color):
        self.points = points
        self.width = width
        self.color = color

        # Create a shader and batch
        self.shader = gpu.shader.create_from_info(shader_info)
        self.batch = self.create_batch()

    def create_batch(self):
        vertices = self.points
        indices = [(i, i + 1) for i in range(len(vertices) - 1)]
        color = [self.color for _ in range(len(vertices))]
        segment_lengths = self.compute_segment_lengths(vertices)
        cumulative_lengths = self.compute_cumulative_lengths(segment_lengths)
        attributes = {"pos": vertices, "color": color, "lineLength": cumulative_lengths}

        # Create a batch for the shader
        return batch_for_shader(self.shader, 'LINES', attributes, indices=indices)

    def compute_segment_lengths(self, points):
        lengths = []
        for i in range(1, len(points)):
            segment_length = (Vector(points[i]) - Vector(points[i-1])).length
            lengths.append(segment_length)
        return lengths

    def compute_cumulative_lengths(self, segment_lengths):
        cumulative_lengths = [0.0]  # Start with zero for the first point
        total_length = 0.0
        for length in segment_lengths:
            total_length += length
            cumulative_lengths.append(total_length)
        return cumulative_lengths

    def update_batch(self, points, color=None):
        vertices = points
        indices = [(i, i + 1) for i in range(len(vertices) - 1)]
        segment_lengths = self.compute_segment_lengths(vertices)
        cumulative_lengths = self.compute_cumulative_lengths(segment_lengths)
        if color:
            color = [color for _ in range(len(vertices))]
        else:
            color = [self.color for _ in range(len(vertices))]
        attributes = {"pos": vertices, "color": color, "lineLength": cumulative_lengths}

        self.batch = batch_for_shader(self.shader, 'LINES', attributes, indices=indices)

    def draw(self, context):
        # Draw the batch
        width = context.area.width
        height = context.area.height

        # Get the region quad view
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        self.shader.bind()
        self.shader.uniform_float('viewportSize', (width, height))
        self.shader.uniform_float('lineSize', 4.0)  # Set dot length

        gpu.state.line_width_set(self.width)
        gpu.state.blend_set('ALPHA')

        self.batch.draw(self.shader)

        # Reset line width
        gpu.state.line_width_set(1)
