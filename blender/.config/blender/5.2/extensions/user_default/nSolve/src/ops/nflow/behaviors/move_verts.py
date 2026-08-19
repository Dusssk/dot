import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *


class Move_Verts(NFlowBehavior):
    undo_message = 'Move Elements'

    capabilities = {'SHRINKWRAP', 'SNAP', 'MIRROR'}

    use_auto_shrinkwrap = True

    def invoke(self, context, event):
        # Initialize editor at the start (raycaster can temporarily hide
        # objects, and hidden ones aren't listed in context's objects)
        editor = self.editors.get(self.obj)
        
        matrix = editor.world_matrix_p
        
        self.verts = list(MeshUtil.gather_verts(self.elements))
        self.points_src = [Vector(v.co) for v in self.verts]
        self.normals_src = [Vector(v.normal) for v in self.verts]
        self.directions = list(self.normals_src)
        self.points_dst = list(self.points_src)
        self.directions_abs = [None] * len(self.verts)
        self.points_abs = [None] * len(self.verts)
        self.points_src_abs = [matrix @ p for p in self.points_src]
        
        self.gather_snap_verts(exclude=self.verts)
        
        if not self.initialize_data(self.invoke_mouse_pos):
            return 'CANCELLED'
        
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        if (event.type == 'MOUSEMOVE') or (event.value == 'PRESS'):
            mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            self.on_mousemove(mouse_pos, event)
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            self.on_finish()
            return 'FINISHED'
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.on_cancel()
            return 'CANCELLED'

    def on_mousemove(self, mouse_pos, event):
        self.update_data(mouse_pos, event)
        self.snap_points_dst()
        
        editor = self.editor
        editor.move(self.verts, self.points_dst)
        self.editors.update_meshes()
        
        NFlow.update_display_data(self.obj, self.elem_type, self.elements)

    def on_finish(self):
        if self.use_post_select_elements:
            MeshUtil.select_elements({self.bm: self.elements},
                mode=self.post_select_mode, sanitize='INCLUDE')
        
        MeshUtil.merge_nearby_verts(self.bm, self.verts)
        
        self.editors.apply()

    def on_cancel(self):
        self.editors.revert()
        
        NFlow.update_display_data(self.obj, self.elem_type, self.elements)

    def snap_points_dst(self):
        editor = self.editor
        matrix = editor.world_matrix_p
        matrix_3x3 = editor.world_matrix_v
        matrix_inv = editor.local_matrix_p
        
        for i in range(len(self.verts)):
            self.points_abs[i] = matrix @ self.points_dst[i]
            self.directions_abs[i] = matrix_3x3 @ self.directions[i]
        
        snap_options = {'EDIT_VERTS'} | self.snap_options_mirror
        if self.use_auto_shrinkwrap:
            snap_options.add('SURFACE')
        if self.use_snap:
            snap_options.update(self.snap_options)
        radius_scene = NFlowPrefs.get('snap_radius')
        radius_edit = NFlowPrefs.get('vert_radius_base')
        MeshUtil.snap(self.points_abs, snap_options, output=self.points_abs,
            raycaster=self.raycaster, directions=self.directions_abs, radius_scene=radius_scene,
            obj=self.obj, original_points=self.points_src_abs,
            kdtree=self.snap_kdtree, radius_edit=radius_edit, hide_elements=self.verts)
        
        for i in range(len(self.verts)):
            self.points_dst[i] = matrix_inv @ self.points_abs[i]

    def initialize_data(self, mouse_pos):
        element_sets = [(self.obj, self.elements)]
        self.origin = self.raycaster.nearest_along_ray(mouse_pos, element_sets, use_raycast=True)[0]
        
        if self.origin is None:
            return False
        
        editor = self.editor
        matrix_inv = editor.local_matrix_p
        
        self.origin_local = matrix_inv @ self.origin
        self.offsets = [(p - self.origin_local) for p in self.points_src]
        
        return True

    def update_data(self, mouse_pos, event):
        origin, direction = self.raycaster.ray(mouse_pos)
        result = self.raycaster.query(origin, direction)
        
        if result[0]:
            new_origin = result[1]
        else:
            new_origin = self.raycaster.unproject(mouse_pos, self.origin)
        
        editor = self.editor
        matrix_inv = editor.local_matrix_p
        
        new_origin = matrix_inv @ new_origin
        
        for i, offset in enumerate(self.offsets):
            self.points_dst[i] = new_origin + offset


NFlow.behaviors['nFlow: Move Geometry'] = dict(
    type=Move_Verts,
    description='Move the highlighted mesh elements',
    cursor='COPY',
    elements={'VERTEX', 'EDGE', 'EDGE_LOOP', 'BOUNDARY', 'PERIMETER', 'FACE'},
    options=[],
)
