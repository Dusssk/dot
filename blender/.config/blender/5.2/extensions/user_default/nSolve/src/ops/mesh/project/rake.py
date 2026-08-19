import math
import bpy
import bmesh
import numpy as np

from mathutils import Vector, Matrix, geometry

from .utils import project_polyline_indexed
from ...utils import infobar
from ....draw.polyline import DrawPolyline
from ....draw.flat_cricle_point import DrawCirclePoint
from .....utils import view3d, addon

# states
NONE = 0
EXTRUDE = 1
MOVE = 2
TWEAK = 3

STATE_NAMES = [
    'NONE',
    'EXTRUDE',
    'MOVE',
    'TWEAK'
]

# extrusion type
WORLD = 0
VIEW = 1

EXRTUSION_NAMES = [
    'WORLD',
    'VIEW'
]

# select states
# NONE = 0 already defined
NEW = 1
ALL = 2

SELECTION_NAMES = [
    'NONE',
    'NEW',
    'ALL'
]

# pivot
MEDIAN = 0
CURSOR = 1

PIVOT_NAMES = [
    'MEDIAN',
    'CURSOR',
]

# alignment
WORLD_X = 0
WORLD_Y = 1
WORLD_Z = 2
LOCAL_X = 3
LOCAL_Y = 4
LOCAL_Z = 5
NO_ALIGNMENT = 6

ALIGMNET_NAMES = [
    'GLOBAL_X',
    'GLOBAL_Y',
    'GLOBAL_Z',
    'LOCAL_X',
    'LOCAL_Y',
    'LOCAL_Z',
    'NONE',
]


# selection states
NOT = 0
SELECTED = 1
CANDIDATE = 2

class NSOLVE_OT_ProjectRake(bpy.types.Operator):
    bl_idname = "nsolve.project_rake"
    bl_label = "Project Rake"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = f"{bl_label}\n\nExtrude selected geometery and project it onto mesh"

    angle_increment: bpy.props.FloatProperty(name='Angle Snape', description='Screen Space angle for alignment', default=math.radians(15.0), min=0.0, max=math.pi/2.0, subtype='ANGLE')

    _state:int = NONE

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val:int):

        if val != NONE:
            self.input_ref_2d = self.mouse.copy()
            bpy.context.window.cursor_set('SCROLL_XY')

        if val == MOVE:
            self.vert_co_base = np.array(self.vert_co)
            self.selectable_verts_co_base = self.vert_co_base[:self.selectable_end]

            median = np.sum(self.vert_co[self.selection_id], axis=0) / len(self.selection_id)
            self.median_vec[0] = median[0]
            self.median_vec[1] = median[1]
            self.median_vec[2] = median[2]

        if val == EXTRUDE:
            self.vert_co_base = np.array(self.vert_co)
            self.selectable_verts_co_base = self.vert_co_base[:self.selectable_end]


        self._state = val
        self.update_header()

    _extrusion_type = WORLD

    @property
    def extrusion_type(self):
        return self._extrusion_type

    @extrusion_type.setter
    def extrusion_type(self, val):

        if val == WORLD:
            self.extrude_mat = self.world_space

        elif val == VIEW:
            self.extrude_mat = self.view_space

        self._extrusion_type = val

        self.update_header()

    _selection_type = NONE

    @property
    def selection_type(self):
        return self._selection_type

    @selection_type.setter
    def selection_type(self, val):

        if val == NONE:
            self.selectable_end = 0

        elif val == NEW:
            self.selectable_end = self.new_vert_start

        elif val == ALL:
            self.selectable_end = len(self.vert_co_base)

        ln = self.selectable_end

        if len(self.selectable_verts_co) != ln:
            theme = addon.pref().theme.ops.mesh.project.rake
            color = theme.vert_color[:]
            size = theme.vert_size
            self.selectable_colors = np.tile(np.array(color, dtype='f'), (ln, 1))
            self.selectable_sizes = np.tile(np.array(size, dtype='f'), ln)
            self.selectable_state = np.tile(np.array(size, dtype='i'), ln)

        self.selectable_verts_co = self.vert_co[:self.selectable_end]
        self.selectable_verts_co_base = self.vert_co_base[:self.selectable_end]

        self._selection_type = val

    _pivot = MEDIAN

    @property
    def pivot(self):
        return self._pivot

    @pivot.setter
    def pivot(self, val):

        self._pivot = val
        self.update_header()

    _alignment = NO_ALIGNMENT

    @property
    def alignment(self):
        return self._alignment

    @alignment.setter
    def alignment(self, val):
        self._alignment = val
        self.update_header()

    world_space: Matrix
    view_space: Matrix
    extrude_mat: Matrix
    median_vec: Vector
    mouse = Vector((0.0, 0.0))
    input_ref_2d = Vector((0.0, 0.0))
    cursor_3d: Vector

    vert_co_base: np.ndarray
    vert_co: np.ndarray
    edges:np.ndarray
    all_edges:np.ndarray
    rake_edges:np.ndarray
    loop_edges:np.ndarray
    selectable_verts_co: np.ndarray = []
    selectable_verts_co_base: np.ndarray = []
    selectable_colors: np.ndarray = []
    selectable_sizes: np.ndarray = []
    selectable_state: np.ndarray = []
    new_vert_start:int
    extrude_id:np.ndarray

    axis_vecs: list[Vector]

    selection_id: list[int]
    selection_candidate: list[int]
    deselection_candidate: list[int]
    selectable_end = 0
    over_selected = False

    region = None
    region_3d = None

    lmb_release_confirm = True
    angle_snap = False

    polyline: DrawPolyline
    _poly_draw_callback = None

    guideline: DrawPolyline
    _guideline_callback = None

    vert_draw: DrawCirclePoint
    _vert_draw_callback = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):

        if not self.create_geomtery(context):
            self.report({"INFO"}, 'No geometry is selected')
            return {'CANCELLED'}

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.selection_id = []
        self.selection_candidate = []
        self.deselection_candidate = []
        self.cursor_3d = Vector(context.scene.cursor.location)

        self.extrusion_type = self.extrusion_type

        if len(self.vert_co) == 2:
            self.selection_id.append(0)
            self.state = MOVE
            self.selection_type = NEW
            self.select_set(0, SELECTED)
        else:
            self.state = EXTRUDE
            self.extrusion_type = self.extrusion_type

        self.selectable_end = self.new_vert_start
        self.extrude_id = np.arange(self.selectable_end, dtype='i')


        self.axis_vecs = [
            Vector((1.0, 0.0, 0.0)),
            Vector((0.0, 1.0, 0.0)),
            Vector((0.0, 0.0, 1.0)),
        ]

        normal_mat = context.object.matrix_world.inverted()
        normal_mat.transpose()

        for vec in self.axis_vecs[:]:
            v = normal_mat @ vec
            v.normalize()
            self.axis_vecs.append(v)


        self.setup_drawing(context)
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Project Rake", position=(50, 2))
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        if event.type == 'MOUSEMOVE':
            if self.state == EXTRUDE:
                self.extrude(context, event)
                self.update_drawing()

            elif self.state == MOVE:
                self.move(context, event, self.selectable_verts_co, self.selectable_verts_co_base, self.selection_id)
                self.update_drawing()

            elif self.state == TWEAK:
                self.over_selected = False
                self.select_set(self.selection_candidate, NOT)
                self.selection_candidate.clear()
                self.deselection_candidate.clear()
                mouse = self.mouse_normalized(self.mouse)

                radius = addon.pref().theme.ops.mesh.project.rake.vert_size / 2

                for i, co in enumerate(self.selectable_verts_co):

                    co_2d, _ = view3d.location_3d_to_region_2d_unclipped(self.region, self.region_3d, co)

                    if (mouse - co_2d).length < radius:
                        if self.selectable_state[i] == SELECTED:
                            self.over_selected = True
                            self.deselection_candidate.append(i)
                            continue

                        self.selection_candidate.append(i)

                if self.selection_candidate:
                    self.select_set(self.selection_candidate, CANDIDATE)
                self.update_drawing()

        elif event.type == 'LEFTMOUSE':
            if self.state == NONE:
                if event.value == 'PRESS':
                    self.state = EXTRUDE

            elif self.state == EXTRUDE:
                if event.value == 'RELEASE' and self.lmb_release_confirm:
                    project_polyline_indexed(self.vert_co, self.all_edges)
                    bpy.ops.mesh.select_all(action='DESELECT')
                    self.end(context)
                    return {'FINISHED'}

            elif self.state == MOVE:
                if event.value == 'RELEASE':
                    if self.lmb_release_confirm:
                        project_polyline_indexed(self.vert_co, self.all_edges)
                        bpy.ops.mesh.select_all(action='DESELECT')
                        self.end(context)
                        return {'FINISHED'}

                    else:
                        self.state = TWEAK

            elif self.state == TWEAK:
                if event.value == 'PRESS':
                    if event.shift:
                        if self.deselection_candidate:
                            self.select_set(self.deselection_candidate, NOT)
                            self.selection_id = [i for i in self.selection_id if i not in self.deselection_candidate]
                            self.selection_candidate.clear()
                            self.selection_candidate.extend(self.deselection_candidate)
                            self.deselection_candidate.clear()
                            self.select_set(self.selection_candidate, CANDIDATE)

                        elif self.selection_candidate:
                            self.select_set(self.selection_candidate, SELECTED)
                            self.selection_id.extend(self.selection_candidate)
                            self.deselection_candidate.clear()
                            self.deselection_candidate.extend(self.selection_candidate)
                            self.selection_candidate.clear()
                    else:
                        if self.over_selected:
                            self.state = MOVE

                        elif self.selection_candidate:
                            self.select_set_all(NOT)
                            self.selection_id.clear()
                            self.selection_id.extend(self.selection_candidate)
                            self.selection_candidate.clear()
                            self.state = MOVE
                            self.select_set(self.selection_id, SELECTED)

                        else:
                            self.select_set(self.selection_id, NOT)
                            self.selection_id.clear()

                    self.update_drawing()

        elif event.type == 'A':
            if self.state == MOVE:
                if event.value == 'RELEASE':
                    self.angle_snap = not self.angle_snap

        elif event.type == 'E':
            if self.state == EXTRUDE:
                if event.value == 'RELEASE':
                    v = self.extrusion_type + 1
                    v %= len(EXRTUSION_NAMES)
                    self.extrusion_type = v
                    self.extrude(context, event)
                    self.update_drawing()

        elif event.type == 'G':
            if self.state != MOVE:
                if event.value == 'RELEASE':
                    if self.selection_type == NONE:
                        self.selection_type = NEW

                    if not self.selection_id:
                        self.selection_id = list(range(len(self.selectable_verts_co)))
                        self.select_set_all(SELECTED)
                    self.state = MOVE

                    self.update_drawing()

        elif event.type in {'X', 'Y', 'Z'}:
            if self.state in (MOVE, EXTRUDE):
                if event.value == "RELEASE":
                    index = 'XYZ'.index(event.type)

                    if self.alignment == NO_ALIGNMENT:
                        self.alignment = index

                    # world
                    elif self.alignment < LOCAL_X:
                        if self.alignment == index:
                            self.alignment = index + 3

                        else:
                            self.alignment = index

                    # local
                    else:
                        if self.alignment == index + 3:
                            self.alignment = NO_ALIGNMENT

                        else:
                            self.alignment = index

                    if self.state == MOVE:
                        self.move(context, event, self.selectable_verts_co, self.selectable_verts_co_base, self.selection_id)

                    else:
                        self.extrude(context, event)

                    self.update_drawing()

        elif event.type == 'W':
            if self.state == EXTRUDE:
                if event.value == 'RELEASE':
                    v = self.pivot + 1
                    v %= len(PIVOT_NAMES)
                    self.pivot = v
                    self.extrude(context, event)
                    self.update_drawing()

        elif event.type == 'TAB':
            if event.value == 'RELEASE':
                if self.state != TWEAK:
                    self.state = TWEAK
                    self.lmb_release_confirm = False
                    self.alignment = NO_ALIGNMENT

                    if self.selection_type == NONE:
                        self.selection_type = NEW
                        self.update_drawing()

        elif event.type in {'SPACE', 'RET'}:
                project_polyline_indexed(self.vert_co, self.all_edges)
                bpy.ops.mesh.select_all(action='DESELECT')
                self.end(context)
                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.end(context)
            return {'CANCELLED'}

        context.area.tag_redraw()
        infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        return {'RUNNING_MODAL'}

    def move(self, context, event, verts, verts_back, index):
        snap_vec_3d = None
        mouse_ref = self.mouse_normalized(self.input_ref_2d)
        mouse_input = mouse_ref + self.mouse - self.input_ref_2d
        input_ref_3d = view3d.region_2d_to_location_3d(self.region, self.region_3d, mouse_ref, self.median_vec)


        if event.ctrl:
            origin = view3d.region_2d_to_origin_3d(self.region, self.region_3d, mouse_input)
            direction = view3d.region_2d_to_vector_3d(self.region, self.region_3d, mouse_input)

            depshraph = context.evaluated_depsgraph_get()

            hit, loc, normal, id, obj, matrix = context.scene.ray_cast(depshraph, origin, direction)

            if hit:
                obj_eval = obj.evaluated_get(depshraph)

                face = obj_eval.to_mesh().polygons[id]

                radius = addon.pref().theme.ops.mesh.project.rake.snap

                for i in face.vertices:
                    co = matrix @ obj_eval.data.vertices[i].co
                    co_2d, _ = view3d.location_3d_to_region_2d_unclipped(self.region, self.region_3d, co)

                    if (co_2d - mouse_input).length < radius:
                        snap_vec_3d = co
                        break

                obj_eval.to_mesh_clear()


        if self.alignment == NO_ALIGNMENT:
            if snap_vec_3d:
                dvec = snap_vec_3d - self.median_vec
                verts[index] = verts_back[index] + dvec
                return

        else:
            axis = self.axis_vecs[self.alignment]

            if snap_vec_3d:
                devc = snap_vec_3d - self.median_vec
                dvec = devc.project(axis)
                verts[index] = verts_back[index] + dvec
                return

            input_vec_3d = view3d.region_2d_to_location_3d(self.region, self.region_3d, mouse_input, self.median_vec)
            dvec = input_vec_3d - input_ref_3d
            dvec = dvec.project(axis)
            verts[index] = verts_back[index] + dvec
            return


        if self.angle_snap:
            ref_vec = Vector((1.0, 0.0))
            dmouse = mouse_input - mouse_ref
            angle = dmouse.angle_signed(ref_vec, 0.0)
            snapped = round((angle / self.angle_increment)) * self.angle_increment
            ref_vec.rotate(Matrix.Rotation(snapped, 2))
            mouse_input = mouse_ref + dmouse.project(ref_vec)

        input_vec_3d = view3d.region_2d_to_location_3d(self.region, self.region_3d, mouse_input, self.median_vec)
        dvec = input_vec_3d - input_ref_3d
        verts[index] = verts_back[index] + dvec

    def extrude(self, context, event):
        if self.alignment < NO_ALIGNMENT:
            self.move(context, event, self.vert_co, self.vert_co_base, self.extrude_id)
            return

        trans_mat = self.extrude_mat.copy()

        pivot = self.pivot_vec()

        trans_mat.translation = pivot

        trans_mat_inv = trans_mat.inverted()
        median_2d, _ = view3d.location_3d_to_region_2d_unclipped(self.region, self.region_3d, pivot)

        scale_vec = self.mouse - median_2d
        unit_vec = self.input_ref_2d - median_2d
        scale = scale_vec.length / unit_vec.length
        scale = math.copysign(scale, scale_vec.dot(unit_vec))

        vec = [scale, scale, scale, 1.0]

        if self.extrusion_type == VIEW:
            vec[2] = 1.0

        scale_mat = Matrix.Diagonal(vec)

        transfrom = trans_mat @ scale_mat @ trans_mat_inv
        transfrom_np = np.array(transfrom.transposed().to_3x3())

        slc_base = self.vert_co_base[:self.new_vert_start]
        slc_co = self.vert_co[:self.new_vert_start]

        np.matmul(slc_base, transfrom_np, out=slc_co)
        slc_co += transfrom.translation

    def pivot_vec(self):
        if self.pivot == MEDIAN:
            pivot = self.median_vec

        elif self.pivot == CURSOR:
            pivot = self.cursor_3d
        return pivot

    def select_set(self, index, val:int):
        color = self.state_color_get(val)

        self.selectable_state[index] = val
        self.selectable_colors[index] = color

    def select_set_all(self, val:int):
        color = self.state_color_get(val)

        self.selectable_state[:] = val
        self.selectable_colors[:] = color

    def state_color_get(self, val):
        theme = addon.pref().theme.ops.mesh.project.rake

        if val == NOT:
            color = theme.vert_color[:]
        elif val == CANDIDATE:
            color = theme.vert_color_high[:]
        elif val == SELECTED:
            color = theme.vert_color_select[:]

        return color

    def create_geomtery(self, context) -> bool:
        """Create projeciton geometry. Set associated state"""
        obj = context.edit_object
        source = bmesh.from_edit_mesh(obj.data)

        selected_verts = [v for v in source.verts if v.select and not v.hide]

        if not selected_verts: return False

        self.region = context.region
        self.region_3d = context.space_data.region_3d

        selected_edges = [e for e in source.edges if e.select and not e.hide]
        bm = bmesh.new()
        vmap = {}
        transform_loc = Vector()

        # copy selection into new bmesh
        for i, v in enumerate(selected_verts):
            co = obj.matrix_world @ v.co
            transform_loc += co

            bm.verts.new(co)
            vmap[v.index] = i

        bm.verts.ensure_lookup_table()

        for e in selected_edges:
            vi1 = vmap[e.verts[0].index]
            vi2 = vmap[e.verts[1].index]
            bm.edges.new((bm.verts[vi1], bm.verts[vi2]))

        # transform planes
        transform_loc /= len(selected_verts)
        self.median_vec = transform_loc
        self.view_space = self.region_3d.view_matrix.inverted()
        self.world_space = Matrix()
        self.world_space.translation = self.view_space.translation = self.median_vec

        res = bmesh.ops.extrude_face_region(bm, geom=bm.verts[:] + bm.edges[:])
        # loop_edges = {elem for elem in res['geom'] if type(elem) == bmesh.types.BMEdge}
        self.edges = self.all_edges = np.empty((len(bm.edges), 2), dtype='i')

        for i, edge in enumerate(bm.edges):

            self.all_edges[i][0] = edge.verts[0].index
            self.all_edges[i][1] = edge.verts[1].index

        loop_end = len(selected_edges)
        self.rake_edges = self.all_edges[loop_end:]
        self.loop_edges = self.all_edges[:loop_end]

        self.vert_co = np.empty((len(bm.verts), 3), dtype='f')
        self.new_vert_start = len(selected_verts)

        for v, co in zip(bm.verts, self.vert_co):
            co[0] = v.co[0]
            co[1] = v.co[1]
            co[2] = v.co[2]

        return True

    def mouse_normalized(self, mouse)-> Vector:
        """Rturn region relative mouse cooridnates that are within the region"""
        return Vector((int(mouse[0]) % self.region.width, int(mouse[1]) % self.region.height))

    def end(self, context):
        '''Cleanup and finish the operator'''

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')
        self.region = None
        self.region_3d = None

        if self._poly_draw_callback: self._poly_draw_callback = bpy.types.SpaceView3D.draw_handler_remove(self._poly_draw_callback, 'WINDOW')
        if self._vert_draw_callback: self._vert_draw_callback = bpy.types.SpaceView3D.draw_handler_remove(self._vert_draw_callback, 'WINDOW')
        if self._guideline_callback: self._guideline_callback = bpy.types.SpaceView3D.draw_handler_remove(self._guideline_callback, 'WINDOW')

        context.area.tag_redraw()

    def update_drawing(self):
        '''Update the drawing'''
        theme = addon.pref().theme.ops.mesh.project.rake
        wdith = theme.line_thickness
        color = theme.line_color[:]

        # edges
        self.polyline.update_batch(self.vert_co, width=wdith, color=color, flat=True, indices=self.edges)


        # guideline
        verts = []
        color = []

        if self.state in (EXTRUDE, MOVE) and self.alignment < NO_ALIGNMENT:
            pivot = self.pivot_vec()
            v1 = view3d.location_3d_to_region_2d(self.region, self.region_3d, pivot).to_3d()
            v2 = view3d.location_3d_to_region_2d(self.region, self.region_3d, pivot + self.axis_vecs[self.alignment]).to_3d()

            normal = v2 - v1
            normal.normalize()
            normal *= self.region.width

            verts = [v1 + normal, v1 - normal]
            colors = [
                bpy.context.preferences.themes[0].user_interface.axis_x,
                bpy.context.preferences.themes[0].user_interface.axis_y,
                bpy.context.preferences.themes[0].user_interface.axis_z,
            ]
            color = colors[self.alignment % 3]

        self.guideline.update_batch(verts, width=wdith, color=color, flat=True)

        # verts
        self.vert_draw.points = self.selectable_verts_co
        self.vert_draw.colors = self.selectable_colors
        self.vert_draw.sizes = self.selectable_sizes
        self.vert_draw.create_batch()

    def setup_drawing(self, context):
        '''Setup the drawing'''

        # # edges
        theme = addon.pref().theme.ops.mesh.project.rake
        width = theme.line_thickness
        color = theme.line_color[:]

        self.polyline = DrawPolyline(self.vert_co, width, color=color, flat=True, indices=self.edges)
        self._poly_draw_callback = bpy.types.SpaceView3D.draw_handler_add(self.polyline.draw, (context,), 'WINDOW', 'POST_VIEW')

        # verts
        self.vert_draw = DrawCirclePoint(self.selectable_verts_co, self.selectable_colors, self.selectable_sizes)
        self._vert_draw_callback = bpy.types.SpaceView3D.draw_handler_add(self.vert_draw.draw, (context,), 'WINDOW', 'POST_VIEW')


        # verts
        self.guideline = DrawPolyline([], width, color=[], flat=True)
        self._guideline_callback = bpy.types.SpaceView3D.draw_handler_add(self.guideline.draw, (context,), 'WINDOW', 'POST_PIXEL')


    def update_header(self):
        s = f'Mode: {STATE_NAMES[self.state]} {EXRTUSION_NAMES[self.extrusion_type]} Pivot: {PIVOT_NAMES[self.pivot]} Alignment: {ALIGMNET_NAMES[self.alignment]}'
        bpy.context.area.header_text_set(s)


    def infobar_hotkeys(self, layout, _context, event):
        '''Draw the infobar hotkeys'''
        factor = 12.0

        row = layout.row(align=True)
        if self.state == NONE:
            row.label(text='', icon='MOUSE_LMB')
            row.label(text='Extrude')
            return

        elif self.state == TWEAK:
            row.label(text='', icon='MOUSE_LMB')
            row.label(text='Select' if not event.shift else 'Toggle Select')
            return

        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust')
        row.separator(factor=factor)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=factor)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=factor)
        row.label(text='', icon='EVENT_TAB')
        row.label(text='TWEAK')
        row.separator(factor=factor)

        if self.state == EXTRUDE:
            row.label(text='', icon='EVENT_E')
            row.label(text='Extrude Modes')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_W')
            row.label(text='Pivot Modes')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_X')
            row.label(text='', icon='EVENT_Y')
            row.label(text='', icon='EVENT_Z')
            row.label(text='Alignment')
            row.separator(factor=factor)

        if self.state != MOVE:
            row.label(text='', icon='EVENT_G')
            row.label(text='GRAB')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_CTRL')
            row.label(text='SNAP')
            row.separator(factor=factor)

        else:
            row.label(text='', icon='EVENT_A')
            row.label(text=f'Angle Snap {"OFF" if not self.angle_snap else math.degrees(self.angle_increment)}')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_X')
            row.label(text='', icon='EVENT_Y')
            row.label(text='', icon='EVENT_Z')
            row.label(text='Alignment')
            row.separator(factor=factor)



class types():
    class theme(bpy.types.PropertyGroup):
        line_color: bpy.props.FloatVectorProperty(name="Line", description="Edge color", default=(0.5, 0.4, 0.8, 1.0), subtype='COLOR', size=4, min=0.0, max=1.0)
        line_thickness: bpy.props.FloatProperty(name="Line Thickness", description="Line Thickness", default=1.8, min=1.0)
        vert_color: bpy.props.FloatVectorProperty(name="Vertex", description="Vertex color", default=(0.8, 0.4, 0.25, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
        vert_color_high: bpy.props.FloatVectorProperty(name="Vertex Highlight", description="Highlight Vertex color", default=(0.2, 0.8, 0.25, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
        vert_color_select: bpy.props.FloatVectorProperty(name="Vertex Selected", description="Selected Vertex color", default=(0.4, 0.4, 0.9, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
        vert_size: bpy.props.FloatProperty(name="Vertex Size", description="Vertex Diameter", default=20.0, min=1.0, step=100)
        snap: bpy.props.FloatProperty(name="Snap Distance", description="Distance in pixels for snap to trigger", default=20.0, min=1.0, step=100)


types_classes = (
    types.theme,
)
