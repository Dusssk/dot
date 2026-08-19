from math import sqrt, pi, cos, sin

import gpu
from mathutils import Vector
from gpu_extras.batch import batch_for_shader


class DrawSphere:
    def __init__(self, center, radius, color, hide, num_verts=128):
        self._hide = [hide]
        self.center = center
        self.radius = radius
        self.color = color
        self.num_verts = max(4, num_verts)

        # Create a shader and batch
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.batch = self.create_batch()

    def create_batch(self):
        vertices, indices = self.create_sphere_verts()
        
        # Convert indices to list of integer tuples for triangles
        tris = [(indices[i], indices[i+1], indices[i+2]) for i in range(0, len(indices), 3)]
        batch = batch_for_shader(
            self.shader, 'TRIS',
            {"pos": vertices},
            indices=tris
        )
        return batch

    def create_sphere_verts(self):
        vertices = []
        indices = []
        
        # Calculate rings based on num_verts/4
        rings = max(4, round(self.num_verts/4))
        segments = rings * 4  # 4x segments for smooth circumference
        
        # Create vertices
        # Add top vertex
        top = Vector((
            self.center[0],
            self.center[1],
            self.center[2] + self.radius
        ))
        vertices.append(top)
        
        # Create ring vertices
        for i in range(rings - 1):
            phi = pi * (i + 1) / rings
            for j in range(segments):
                theta = 2.0 * pi * j / segments
                
                # Calculate vertex position
                x = sin(phi) * cos(theta)
                y = sin(phi) * sin(theta)
                z = cos(phi)
                
                # Scale by radius and offset by center
                vert = Vector((
                    self.center[0] + self.radius * x,
                    self.center[1] + self.radius * y,
                    self.center[2] + self.radius * z
                ))
                vertices.append(vert)
        
        # Add bottom vertex
        bottom = Vector((
            self.center[0],
            self.center[1],
            self.center[2] - self.radius
        ))
        vertices.append(bottom)
        
        # Create indices
        # Top cap
        for i in range(segments):
            next_i = (i + 1) % segments
            indices.extend([0, i + 1, next_i + 1])
        
        # Middle rings
        for ring in range(rings - 2):
            ring_start = 1 + ring * segments
            next_ring = ring_start + segments
            for i in range(segments):
                next_i = (i + 1) % segments
                indices.extend([
                    ring_start + i, next_ring + i, ring_start + next_i,
                    next_ring + i, next_ring + next_i, ring_start + next_i
                ])
        
        # Bottom cap
        bottom_idx = len(vertices) - 1
        last_ring = bottom_idx - segments
        for i in range(segments):
            next_i = (i + 1) % segments
            indices.extend([bottom_idx, last_ring + next_i, last_ring + i])
        
        return vertices, indices

    def hide(self, index, hide_value):
        self._hide[index] = hide_value

    def update_batch(self, center=None, radius=None):
        if center is not None:
            self.center = center
        if radius is not None:
            self.radius = radius

        # Recreate the batch with new parameters
        self.batch = self.create_batch()

    def draw(self, context):
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.face_culling_set('BACK')  # Only show front faces
        
        if not self._hide[0]:
            self.shader.bind()
            self.shader.uniform_float("color", self.color)
            self.batch.draw(self.shader)

        gpu.state.face_culling_set('NONE')
        gpu.state.depth_test_set('NONE')
        gpu.state.blend_set('NONE')
