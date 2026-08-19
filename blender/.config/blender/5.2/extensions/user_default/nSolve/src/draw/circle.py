from math import cos, sin

import gpu

from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from ...utils import view3d


class DrawCircle:
    def __init__(self, points, radius, width, color, hide, region, region_data):
        self._hide = hide
        self.region = region
        self.region_data = region_data
        # Project 3D points to 2D screen space
        self.points = [view3d.location_3d_to_region_2d(region, region_data, point) for point in points]
        self.radius = radius
        self.width = width
        self.color = color

        # Filter out None points (not visible on the screen)
        self.points = [point for point in self.points if point is not None]

        # Create a shader and batch
        self.shader = gpu.shader.from_builtin('POLYLINE_FLAT_COLOR')
        self.batches = self.create_batches()

    def create_batches(self):
        circle_verts = self.get_circle_verts()

        # Create a batch for each point with the circle vertices
        batches = [batch_for_shader(self.shader, 'LINE_LOOP', {"pos": verts, "color": colors}) for verts, colors in circle_verts]

        return batches

    def get_circle_verts(self):
        circle_verts = []

        # For each point, create circle vertices
        for point in self.points:
            circle_verts.append(self.create_circle_verts(point, self.radius))

        return circle_verts

    def create_circle_verts(self, center, radius):
        vertices = []
        colors = []

        if radius < 10:
            segs = 8
        elif radius < 50:
            segs = 16
        elif radius < 100:
            segs = 32
        else:
            segs = 64

        for i in range(segs):
            angle = 2.0 * 3.1416 * i / segs
            vec = Vector((radius * cos(angle) + center[0], radius * sin(angle) + center[1], 0))
            vertices.append(vec)
            colors.append(self.color)

        return vertices, colors

    def hide(self, index, hide_value):
        # Updated to hide specific circle
        self._hide[index] = hide_value

    def update_batch(self, points, radius=None):

        if radius:
            self.radius = radius
        self.points = [view3d.location_3d_to_region_2d(self.region, self.region_data, point) for point in points]
        self.points = [point for point in self.points if point is not None]

        circle_verts = self.get_circle_verts()

        # Update the hide list to match the number of points
        num_points = len(points)
        num_hide = len(self._hide)
        if num_hide < num_points:
            self._hide.extend([False] * (num_points - num_hide))
        elif num_hide > num_points:
            self._hide = self._hide[:num_points]

        # Create a batch for each point with the circle vertices
        self.batches = [batch_for_shader(self.shader, 'LINE_LOOP', {"pos": verts, "color": colors}) for verts, colors in circle_verts]

    def draw(self, context):
        # Updated to draw only if not hidden

        width = context.area.width
        height = context.area.height

        quad_view = context.space_data.region_quadviews
        if quad_view:
            width /= 2
            height /= 2

        self.shader.bind()
        self.shader.uniform_float('viewportSize', (width, height))
        self.shader.uniform_float('lineWidth', self.width)

        gpu.state.blend_set('ALPHA')

        for i, batch in enumerate(self.batches):
            if not self._hide[i]:  # draw each circle individually if not hidden
                batch.draw(self.shader)
