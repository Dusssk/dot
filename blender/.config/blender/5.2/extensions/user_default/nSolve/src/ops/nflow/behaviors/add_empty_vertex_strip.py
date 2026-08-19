import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *


class Add_Empty_VertexStrip(NFlowBehavior):
    undo_message = 'Draw Vertices'

    capabilities = {'SHRINKWRAP', 'SNAP', 'MIRROR'}

    auto_enable_overlay = True

    mode = 'SELECTION'
    single_vertex = False
    min_distance_pixels = 32

    original_point = None

    resampling_count = -1

    def init(self, context, event):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        self.min_distance_pixels = nflow_config_workspace.draw_verts_min_distance_pixels
        self.min_distance_pixels = max(self.min_distance_pixels, 1)
        self.draw_verts_resampling = max(nflow_config_workspace.draw_verts_resampling, 0)
        self.dead_zone = NFlowPrefs.scale(2.0, 'DPI') # Blender's default vertex size

    def invoke(self, context, event):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        # It was requested that auto_enable_overlay should enable
        # the overlay regardless of whether vertices are visible
        auto_enable_overlay = self.auto_enable_overlay
        # auto_enable_overlay &= not context.tool_settings.mesh_select_mode[0]
        if auto_enable_overlay:
            nflow_config_workspace.show_vertex_overlay = True
        
        self.single_vertex = (self.mode == 'VERTEX')
        
        self.gather_snap_verts()
        self.points = []
        self.add_point(event.mouse_region_x, event.mouse_region_y)
        self.realize_points(context)
        
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.add_point(event.mouse_region_x, event.mouse_region_y)
            self.realize_points(context)
        elif event.value == 'PRESS':
            if event.type in ('UP_ARROW', 'WHEELUPMOUSE'):
                self.resampling_count = self.resampling_count + 1
            elif event.type in ('DOWN_ARROW', 'WHEELDOWNMOUSE'):
                self.resampling_count = max(self.resampling_count - 1, 0)
            self.realize_points(context)
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            self.realize_points(context, True)
            return 'FINISHED'
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.editors.revert()
            return 'CANCELLED'

    def cleanup(self, context):
        NFlow.display_curve.clear()

    def realize_points(self, context, final=False):
        self.editors.revert_last()
        
        if not self.points:
            return
        
        editor = self.editor
        
        self.calc_resampling_count()
        
        matrix = editor.world_matrix_p
        matrix_inv = editor.local_matrix_p
        
        ray_points = self.calc_ray_points(matrix)
        
        points = [(origin + direction * t) for origin, direction, t in ray_points]
        
        points = self.resample_points(points, self.resampling_count)
        
        if (self.original_point is None) and points:
            self.original_point = points[0]
        
        original_points = [self.original_point] * len(points)
        
        snap_options = {'EDIT_VERTS'} | self.snap_options_mirror
        if self.use_snap:
            snap_options.update(self.snap_options)
        radius_scene = NFlowPrefs.get('snap_radius')
        radius_edit = NFlowPrefs.get('vert_radius_base')
        MeshUtil.snap(points, snap_options, output=points,
            raycaster=self.raycaster, radius_scene=radius_scene,
            obj=editor.obj, original_points=original_points, clamp_bisected=True,
            kdtree=self.snap_kdtree, radius_edit=radius_edit)
        
        points = (matrix_inv @ p for p in points)
        new_elements = MeshUtil.create_polyline(editor.bm, points)
        editor.add(new_elements)
        
        if final:
            if self.use_post_select_elements:
                bm_elements = {editor.bm: new_elements}
                MeshUtil.select_elements(bm_elements, mode=self.post_select_mode)
            
            verts = [elem for elem in new_elements if isinstance(elem, BMVert)]
            MeshUtil.merge_nearby_verts(editor.bm, verts)
        
        if len(ray_points) == 1:
            self.undo_message = 'Draw Vertex'
        
        self.editors.update_meshes()

    def calc_resampling_count(self):
        if self.resampling_count >= 0:
            return
        
        editor = self.editor
        bm = editor.bm
        
        edge_count = sum(e.select for e in bm.edges)
        vert_count = sum((v.select and (len(v.link_edges) == 0)) for v in bm.verts)
        
        if (edge_count == 0) and (vert_count == 1):
            vert_count = 0
        
        self.resampling_count = math.ceil((edge_count + vert_count) * self.draw_verts_resampling)
        
        if self.resampling_count == 0:
            if self.mode == 'SELECTION':
                self.resampling_count = 0
                self.single_vertex = True
            elif self.draw_verts_resampling >= 1:
                self.resampling_count = int(self.draw_verts_resampling)

    def resample_points(self, points, segment_count):
        n = len(points)
        
        if (n <= 1) or (segment_count <= 0):
            return points
        
        distances = [0.0] * n
        for i in range(1, n):
            distances[i] = distances[i-1] + (points[i] - points[i-1]).magnitude
        
        total_length = distances[-1]
        if total_length == 0:
            return points[:1]
        
        result = []
        for j in range(segment_count+1):
            dist = total_length * j / segment_count
            i = min(max(bisect.bisect_left(distances, dist), 1), n-1)
            t = (dist - distances[i-1]) / (distances[i] - distances[i-1])
            p = points[i-1].lerp(points[i], t)
            result.append(p)
        return result

    def calc_ray_points(self, matrix):
        ray_points = []
        
        view_origin = self.view_info['origin']
        view_direction = self.view_info['axis_z']
        
        with self.raycaster.batch():
            for p in self.points:
                origin, direction = self.raycaster.ray(p)
                result = self.raycaster.query(origin, direction)
                t = (view_direction.dot(result[1] - origin) if result[0] else None)
                direction /= view_direction.dot(direction)
                ray_points.append([origin, direction, t])
        
        def propagate(i0, i1, t0, t1):
            step = (1 if i1 > i0 else -1)
            i = i0
            offset = step * 0.5 - i0
            scale = 1.0 / (i1 - i0)
            while i != i1:
                factor = (i + offset) * scale
                ray_points[i][-1] = t0*(1.0 - factor) + t1*factor
                i += step
        
        count = len(ray_points)
        
        last_i = -1
        last_t = None
        for i in range(count):
            t = ray_points[i][-1]
            if t is None:
                continue
            if i > last_i+1:
                last_t = (t if last_t is None else last_t)
                propagate(i-1, last_i, t, last_t)
            last_i, last_t = i, t
        
        if last_i < 0:
            t = view_direction.dot(matrix.translation - view_origin)
            propagate(0, count, t, t)
        elif last_i < count-1:
            propagate(last_i+1, count, last_t, last_t)
        
        return ray_points

    def add_point(self, x, y):
        if self.single_vertex:
            self.points.clear()
        
        p = Vector((x, y, 0)) # shader expects a 3D point
        
        count = len(self.points)
        should_append = False
        should_move = False
        
        if count == 0:
            should_append = True
        elif count == 1:
            should_append = ((self.points[-1] - p).magnitude > self.dead_zone)
        elif (self.points[-2] - p).magnitude > self.min_distance_pixels:
            should_append = True
        else:
            should_move = True
        
        if should_append:
            self.points.append(p)
        elif should_move:
            self.points[-1] = p


def settings_draw(option_infos):
    show_min_distance_pixels = False
    
    for option_info in option_infos:
        idname = option_info['idname']
        if (idname == 'mode') and (option_info['value'] != 'VERTEX'):
            show_min_distance_pixels = True
    
    if not show_min_distance_pixels:
        return None
    
    def draw(layout, context):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        layout.prop(nflow_config_workspace, 'draw_verts_min_distance_pixels')
        layout.prop(nflow_config_workspace, 'draw_verts_resampling')
    
    return draw


NFlow.behaviors['nFlow: Draw Vertices'] = dict(
    type=Add_Empty_VertexStrip,
    description='Add a single vertex or a draw a curve that will turn into a polyline',
    cursor='PAINT_BRUSH',
    elements={'NONE'},
    options=[
        dict(idname='mode', name='Mode', default='SELECTION', items=[
            ('VERTEX', 'Single vertex'),
            ('STRIP', 'Vertex strip'),
            ('SELECTION', 'Like selection'),
        ]),
        dict(idname='auto_enable_overlay', name='Auto enable overlay', default=True),
    ],
    context_modes={'EDIT_MESH', 'OBJECT'},
    settings_label='Draw Vertices',
    settings_draw=settings_draw,
)
