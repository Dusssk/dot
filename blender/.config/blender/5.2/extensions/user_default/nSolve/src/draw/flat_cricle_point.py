import gpu

from gpu_extras.batch import batch_for_shader
from ...shaders import FLAT_CIRCLE_POINT_3D


class DrawCirclePoint:
    def __init__(self, points, colors, sizes):
        '''
        points - list of 3d float vectors; location in 3d space\n
        colors - list of 4d float vectors; a matching list of colors\n
        colors - list of float; a matching list of sizes\n
        '''

        self.points = points
        self.colors = colors
        self.sizes = sizes

        # Create a shader and batch
        self.shader = FLAT_CIRCLE_POINT_3D.compile()
        self.batch = self.create_batch()

    def create_batch(self):
        '''Create batch from stored data'''
        attr = {'pos':self.points, 'color': self.colors, 'size':self.sizes}
        self.batch = batch_for_shader(self.shader, 'POINTS', attr)


    def update_batch(self, points, colors, sizes):
        '''Update stored data and create new batch'''
        self.points = points
        self.colors = colors
        self.sizes = sizes

        self.batch = self.create_batch()

    def draw(self, context):

        self.shader.bind()
        self.shader.uniform_float('ViewProjectionMatrix', context.region_data.perspective_matrix)

        gpu.state.program_point_size_set(True)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(self.shader)

        gpu.state.blend_set('NONE')
        gpu.state.program_point_size_set(False)
