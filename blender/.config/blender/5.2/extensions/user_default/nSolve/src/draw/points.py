import gpu

from gpu_extras.batch import batch_for_shader
from ...shaders import POINT_UNIFORM



class DrawPoints:
    def __init__(self, points, size, color):
        self.points = points
        self.size = size
        self.color = color

        # Create a shader and batch
        self.shader = POINT_UNIFORM.compile()
        self.batch = self.create_batch()

    def create_batch(self):
        vertices = self.points
        attributes = {"pos": vertices}

        # Create a batch for the shader
        return batch_for_shader(self.shader, 'POINTS', attributes)

    def update_batch(self, points):
        vertices = points
        attributes = {"pos": vertices}

        self.batch = batch_for_shader(self.shader, 'POINTS', attributes)

    def draw(self, _context):
        # Draw the batch

        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        self.shader.uniform_float('size', self.size)

        gpu.state.program_point_size_set(True)
        gpu.state.blend_set('ALPHA')

        self.batch.draw(self.shader)

        # Reset point size and settings
        gpu.state.program_point_size_set(False)
