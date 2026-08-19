import gpu
from gpu_extras.batch import batch_for_shader


class DrawPolyline:
    def __init__(self, edge_points, width, color, indices=None, flat=False):
        self.edge_points = edge_points  # This will be a list of tuples/lists with 2 Vector elements each or a flat list of vectors if flat
        self.width = width
        self.color = color
        self.shader = gpu.shader.from_builtin('POLYLINE_FLAT_COLOR')
        self.flat = flat
        self.indices = indices
        self.batch = self.create_batch()

    def create_batch(self):
        if self.flat:
            vertices = self.edge_points
            indices = self.indices

        else:
            # Flatten the list of tuples/lists into a sequential list of Vector points
            vertices = [point for edge in self.edge_points for point in edge]
            indices = None

        vertices_color = [self.color for _ in range(len(vertices))]
        attributes = {"pos": vertices, "color": vertices_color}

        # Create a batch for the shader
        return batch_for_shader(self.shader, 'LINES', attributes, indices=indices)

    def update_batch(self, edge_points, color=None, width=None, indices=None, flat=False):
        self.edge_points = edge_points  # Update with new edge points
        self.indices = indices
        self.flat = flat

        if self.flat:
            vertices = self.edge_points
            indices = self.indices

        else:
            # Flatten the list of tuples/lists into a sequential list of Vector points
            vertices = [point for edge in self.edge_points for point in edge]
            indices = None

        if color:
            self.color = color
        else:
            color = self.color
        vertices_color = [color for _ in range(len(vertices))]

        if width:
            self.width = width

        attributes = {"pos": vertices, "color": vertices_color}

        self.batch = batch_for_shader(self.shader, 'LINES', attributes, indices=indices)

    def draw(self, context):
        width = context.area.width
        height = context.area.height

        # Adjust for quad view if necessary
        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        self.shader.bind()
        self.shader.uniform_float('viewportSize', (width, height))
        self.shader.uniform_float('lineWidth', self.width)

        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)
