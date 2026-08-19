import bpy
import gpu
from gpu_extras.batch import batch_for_shader


class DrawFace:
    '''Draw a face in the 3D view.'''

    def __init__(self, tris_points, color, culling=False, culling_method='BACK'):
        self.tris_points = tris_points  # This should be a list of triangles, each containing 3 vertices
        self.color = color
        self.culling = culling
        self.culling_method = culling_method
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.batch = self.create_batch()
        self.handler = None  # Store handler reference

    def create_batch(self):
        '''Create a batch for the shader.'''

        vertices = [v for tri in self.tris_points for v in tri]
        return batch_for_shader(self.shader, 'TRIS', {"pos": vertices})

    def update_batch(self, tris_points):
        '''Update the batch with new triangles.'''

        self.tris_points = tris_points
        self.batch = self.create_batch()

    def draw(self, context):
        '''Draw the batch.'''

        if self.culling:
            culling_method = self.culling_method
            gpu.state.face_culling_set(culling_method)

        gpu.state.depth_test_set('NONE')

        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        gpu.state.blend_set('ALPHA_PREMULT')
        self.batch.draw(self.shader)

        if self.culling:
            gpu.state.face_culling_set('NONE')
