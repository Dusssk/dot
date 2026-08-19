import time
import math
import bisect
import itertools
import collections
import ast

import bpy
import bmesh
from bpy_extras.view3d_utils import (
    region_2d_to_origin_3d,
    region_2d_to_vector_3d,
    region_2d_to_location_3d,
    location_3d_to_region_2d,
)
from mathutils import Vector, Matrix
from mathutils.geometry import (
    tessellate_polygon,
    intersect_line_line,
    intersect_ray_tri,
    closest_point_on_tri,
    area_tri,
)
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

import blf
import gpu
from gpu_extras.batch import batch_for_shader

from .... import utils

BMesh = bmesh.types.BMesh
BMVert = bmesh.types.BMVert
BMEdge = bmesh.types.BMEdge
BMFace = bmesh.types.BMFace
BMElements = (BMVert, BMEdge, BMFace)


def get_addon_version():
    from .... import bl_info
    return '.'.join(str(item) for item in bl_info['version'])


class NFlowPrefs:
    use_dpi_scale = {'vert_radius_base', 'edge_radius_base', 'vertex_overlay_radius'}
    use_ui_scale = {'text_size'}
    relative_to = {'edge_radius_ext': 'edge_radius_base'}

    @classmethod
    def prefs(cls):
        return utils.addon.pref().nflow

    @classmethod
    def scale(cls, value, mode):
        if mode == 'DPI':
            value *= bpy.context.preferences.system.dpi / 72
        elif name == 'UI':
            value *= bpy.context.preferences.view.ui_scale
        return value

    @classmethod
    def get(cls, name, default=Exception):
        if default is Exception:
            value = getattr(cls.prefs(), name)
        else:
            value = getattr(cls.prefs(), name, default)

        if name in cls.use_dpi_scale:
            value *= bpy.context.preferences.system.dpi / 72
        if name in cls.use_ui_scale:
            value *= bpy.context.preferences.view.ui_scale

        relative_to = cls.relative_to.get(name)
        if relative_to:
            value *= cls.get(relative_to)

        return value

    @classmethod
    def set(cls, name, value):
        if name in cls.use_dpi_scale:
            value /= bpy.context.preferences.system.dpi / 72
        if name in cls.use_ui_scale:
            value /= bpy.context.preferences.view.ui_scale

        relative_to = cls.relative_to.get(name)
        if relative_to:
            value /= cls.get(relative_to)

        setattr(cls.prefs(), name, value)


class PresetOverride:
    @classmethod
    def get(cls, name, default=Exception):
        context = bpy.context
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        behavior_presets_config = nflow_config_workspace.behavior_presets_config
        behavior_preset = behavior_presets_config.get_active_preset()
        if behavior_preset is not None:
            if behavior_preset.use_override_color:
                color = behavior_preset.override_color
                alpha = NFlowPrefs.get(name, default)[3]
                return (color[0], color[1], color[2], alpha)
            # element_name = name[len('color_'):].upper()
            # color_overrides = behavior_preset.color_overrides
            # if ('ENABLE' in color_overrides) and (element_name in color_overrides):
            #     if default is Exception:
            #         return getattr(behavior_preset, name)
            #     return getattr(behavior_preset, name, default)
        return NFlowPrefs.get(name, default)


class DictTransformer(ast.NodeTransformer):
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == 'dict':
            if len(node.args) != 0:
                raise ValueError('Invalid dict call')
            keys = [ast.Str(s=keyword.arg) for keyword in node.keywords]
            values = [keyword.value for keyword in node.keywords]
            return ast.Dict(keys=keys, values=values)
        return self.generic_visit(node)


def parse_operator_command(command, remap_special=False):
    bracket_index = command.find('(')
    if bracket_index >= 0:
        command, args = command[:bracket_index].strip(), command[bracket_index:].strip()
    else:
        command, args = command.strip(), ''

    if command.startswith('bpy.'):
        command = command[len('bpy.'):]

    if command.startswith('ops.'):
        command = command[len('ops.'):]

    if remap_special:
        if NFlow.special_operators is None:
            NFlow.update_special_operators()
        command = NFlow.special_operators.get(command) or command

    return command, args


def eval_operator_args(args):
    kwargs = None

    try:
        tree = ast.parse('dict'+args, mode='eval')
        tree = DictTransformer().visit(tree)
        ast.fix_missing_locations(tree)
        kwargs = ast.literal_eval(tree)
    except Exception:
        pass

    if not isinstance(kwargs, dict):
        kwargs = None

    return kwargs


def get_operator(command, poll=False):
    command, args = parse_operator_command(command, True)

    parts = command.split('.')
    parts_count = len(parts)

    if parts_count != 2:
        return None

    try:
        # we may get a wrapper around a nonexistent operator,
        # but at least getting its properties seems to fail
        op = getattr(getattr(bpy.ops, parts[-2]), parts[-1])
        op.get_rna_type()
    except Exception as exc:
        # Commented out, because this spams the console if e.g.
        # the operator comes from addon that isn't installed
        # print(exc)
        return None

    if not poll:
        return op

    try:
        return (op if op.poll() else None)
    except Exception as error:
        return None


class UIMetadata:
    _counter = 0

    @classmethod
    def set(cls, layout, metadata, prefix='$'):
        cls._counter += 1
        version = f'{cls._counter:0>16x}' # 16-char 0-padded hex value

        for key, value in metadata.items():
            entry = (f'{key}:{version}' if value is None else f'{key}:{version}={value}')
            layout.context_pointer_set(prefix+entry, None)

    @classmethod
    def get(cls, context, prefix='$'):
        # Since dir() returns sorted values, we can ensure that only the latest
        # assigned values are returned by including a version/counter in the key

        start = len(prefix)
        metadata = {}
        for key in dir(context):
            if not key.startswith(prefix): continue

            i = key.find('=', start)
            if i < 0:
                value = None
                key = key[start:]
            else:
                value = key[i+1:]
                key = key[start:i]

            i = key.rfind(':')
            if i >= 0: key = key[:i]

            metadata[key] = value

        return metadata


event_key_items = [(item.identifier, item.name, item.description, item.icon, item.value)
                for item in bpy.types.KeyMapItem.bl_rna.properties["type"].enum_items]


event_key_map = dict([
    *((item[0], item[-1]) for item in event_key_items),
    *((item[-1], item[0]) for item in event_key_items),
])


event_key_map_names = dict((item[0], item[1]) for item in event_key_items)


def ui_row(layout, **kwargs):
    align = kwargs.pop('align', True)
    row = layout.row(align=align)
    for key, value in kwargs.items():
        setattr(row, key, value)
    return row


def ui_prop(layout, data, property, **kwargs):
    if bpy.app.version < (4, 1, 0):
        kwargs.pop('placeholder', None)
    layout.prop(data, property, **kwargs)


def draw_enum_items(layout, container, prop_name, text=None):
    for item in container.bl_rna.properties[prop_name].enum_items:
        if text is None:
            layout.prop_enum(container, prop_name, item.identifier)
        else:
            layout.prop_enum(container, prop_name, item.identifier, text=text)


def draw_vector_items(layout, container, prop_name, text='', **kwargs):
    for i in range(len(getattr(container, prop_name))):
        if isinstance(text, str):
            text_i = text
        else:
            text_i = text[i] if (i < len(text)) else ''
        layout.prop(container, prop_name, index=i, text=text_i, **kwargs)


def draw_vector_items_row(layout, container, prop_name, text='', **kwargs):
    row = layout.row(align=True)
    draw_vector_items(row, container, prop_name, text=text, **kwargs)


def foldable_layout(layout, container, prefix, text, align=True, fold=False, box=False):
    if box:
        box = layout.box()
    else:
        box = layout.column()
    col = box.column(align=True)
    row = col.row()
    row.alignment = 'LEFT'

    # In Blender 3.3, there was no support for boolean custom properties
    if isinstance(fold, bool) and (bpy.app.version >= (3, 6, 0)):
        key = f'{prefix}/{text}'
        if key not in container:
            container[key] = not fold
            container.id_properties_ui(key).update(description='Fold/Unfold')
        icon = ('DISCLOSURE_TRI_DOWN' if container[key] else 'DISCLOSURE_TRI_RIGHT')
        row.prop(container, f'["{key}"]', text=text, icon=icon, toggle=True, emboss=False)
        is_visible = container[key]
    else:
        row.label(text=text, icon='DOT')
        is_visible = True

    return (col.column(align=align) if is_visible else None)


def calc_region_rect(area, region, overlap=True, convert=None):
    x0, y0 = region.x, region.y
    x1, y1 = x0 + region.width, y0 + region.height

    # Note: there may be more than one region of the same type (e.g. in quadview)
    if overlap or (region.type != 'WINDOW'):
        return Vector((x0, y0)), Vector((x1-x0, y1-y0))

    for region in area.regions:
        if (region.width <= 0) or (region.height <= 0): continue

        # A HUD-specific hack. At least in Blender 2.80, HUD in 3d view
        # in some cases does not become 1x1 when it's "hidden",
        # but we may still attempt to detect it by its (x,y) being zero
        if (region.alignment == 'FLOAT') and (region.x == 0) and (region.y == 0): continue

        alignment = region.alignment
        if convert: alignment = convert.get(alignment, alignment)

        if alignment == 'TOP':
            y1 = min(y1, region.y)
        elif alignment == 'BOTTOM':
            y0 = max(y0, region.y + region.height)
        elif alignment == 'LEFT':
            x0 = max(x0, region.x + region.width)
        elif alignment == 'RIGHT':
            x1 = min(x1, region.x)

    return Vector((x0, y0)), Vector((x1-x0, y1-y0))


def is_valid(obj):
    if not obj: return False
    try:
        id_data = obj.id_data
        return True
    except (ReferenceError, AttributeError):
        return False


class Cursor3DHelper:
    @classmethod
    def snap(cls, context, mouse_pos, obj, elements, snap_to_elements=True):
        ray_origin, ray_direction = Raycaster.ray(context, mouse_pos)
        raycast_result = Raycaster.query(context, ray_origin, ray_direction)
        if raycast_result[0]:
            location = raycast_result[1]
            normal = raycast_result[2]
        else:
            location = None
            normal = None

        ref_axis = None

        if elements:
            matrix = obj.matrix_world
            matrix_3x3 = matrix.to_3x3()

            elem = next(iter(elements))
            edges = []

            # Use index as tie-breaker (to avoid 'comparison not supported' errors)
            if isinstance(elem, BMVert):
                if snap_to_elements or (location is None):
                    location = matrix @ elem.co
                    normal = (matrix_3x3 @ elem.normal).normalized()
                edges.extend((-e.calc_length(), i, e) for i, e in enumerate(elem.link_edges))
            elif isinstance(elem, BMEdge):
                if snap_to_elements or (location is None):
                    origin, endpoint = Raycaster.ray_line(context, mouse_pos)
                    location, _ = Raycaster.edge(elem, matrix, origin, endpoint)
                    normal = (matrix_3x3 @ calc_edge_normal(elem)).normalized()
                edges.append((0, 0, elem))
            elif isinstance(elem, BMFace):
                if snap_to_elements or (location is None):
                    origin, direction = Raycaster.ray(context, mouse_pos)
                    location2, normal2 = Raycaster.face(elem, matrix, origin, direction)
                    if (location2 is None) and (location is None):
                        return
                    location, normal = location2, normal2
                for i, e in enumerate(elem.edges):
                    p, t = Raycaster.edge(e, matrix, location)
                    edges.append(((p - location).length_squared, i, e))

            edge = None
            if edges:
                edges.sort()
                edge = edges[0][-1]

            if edge and (edge.calc_length() > 0):
                v0, v1 = edge.verts
                ref_axis = (matrix.to_3x3() @ (v1.co - v0.co)).normalized()
                if abs(normal.dot(ref_axis)) > 0.9999:
                    ref_axis = None

        if location is None:
            return

        if ref_axis is None:
            ref_axis = Vector((0, 0, 1)) if abs(normal.z) < 0.9999 else Vector((1, 0, 0))

        axis_x = normal.cross(ref_axis).normalized()
        axis_y = axis_x.cross(normal).normalized()
        axis_z = normal

        matrix = Matrix()
        matrix.col[0][:3] = axis_x
        matrix.col[1][:3] = axis_y
        matrix.col[2][:3] = axis_z
        matrix.translation = location

        cls.set_matrix(context.scene.cursor, matrix)

    @classmethod
    def set_matrix(cls, cursor, matrix):
        # Assigning a matrix doesn't seem to work for rotation
        cursor.location = matrix.translation
        if cursor.rotation_mode == 'QUATERNION':
            cursor.rotation_quaternion = matrix.to_quaternion()
        elif cursor.rotation_mode == 'AXIS_ANGLE':
            axis, angle = matrix.to_quaternion().to_axis_angle()
            cursor.rotation_axis_angle = (*axis, angle)
        else:
            cursor.rotation_euler = matrix.to_quaternion().to_euler(cursor.rotation_mode)


class SelectionHelper:
    def __init__(self, options={}):
        self.selection_mode = options.get('selection_mode', 'OVERRIDE')
        self.select_lock_element_type = options.get('select_lock_element_type', True)
        self.select_first_vertex = options.get('select_first_vertex', False)
        self.select_last_vertex = options.get('select_last_vertex', False)
        self.elem_types = options.get('elem_types', ())
        self.selection_dilation = 0
        self.use_update_highlight = True
        self.selection_state_original = None
        self.select_value = True

    def cleanup(self, original=True):
        # Under some rare circumstances (e.g. using the Extrude Manifold operator
        # on a particular mesh), bmesh can get invalidated in such a way that it
        # would lead to a crash when python garbage-collects the dictionaries that
        # contain this bmesh as key. But it seems that manually clearing those
        # dictionaries before the garbage collection allows to avoid the crash.

        # Note: it's best to clear before actually invoking the potentially
        # bmesh-invalidating operation, though in practice it can even be done
        # immediately afterwards. However, clearing selection_state_original
        # afterwards still leads to a crash (but clearing everything except
        # selection_state_original doesn't lead to a crash, somehow).

        if hasattr(self, 'all_bms'):
            self.all_bms.clear()
            self.all_elements.clear()
            self.selection_history['elements'].clear()
            if self.selection_state_original and original:
                cleanup_mesh_selection(self.selection_state_original)
        else:
            if self.selection_state_original:
                cleanup_object_selection(self.selection_state_original)

    def init_object(self, context, mouse_pos):
        if self.selection_mode == 'KEEP':
            return

        self.selection_state_original = store_object_selection()

        mouse_pos = (int(mouse_pos[0]), int(mouse_pos[1]))

        def is_currently_selected():
            bpy.ops.view3d.select('EXEC_DEFAULT', location=mouse_pos, extend=False)
            obj = context.object
            restore_object_selection(self.selection_state_original)
            return bool(obj) and obj.select_get()

        extend = False

        if self.selection_mode == 'ADD':
            extend = True
        elif self.selection_mode == 'SEMI_OVERRIDE':
            extend = is_currently_selected()
        elif self.selection_mode == 'TOGGLE':
            self.select_value = not is_currently_selected()
            extend = self.select_value
        elif self.selection_mode == 'REMOVE':
            self.select_value = False

        if self.select_value and not extend:
            self.deselect_all()

        deselect = not self.select_value
        bpy.ops.view3d.select('EXEC_DEFAULT', location=mouse_pos, extend=extend, deselect=deselect)

        context.area.tag_redraw()

    def init_mesh(self, context, mouse_pos, obj, bm, elem_type, elements):
        if self.selection_mode == 'KEEP':
            return

        self.selection_state_original = store_mesh_selection()

        self.all_bms = {}
        self.all_elements = set()
        self.selection_history = {
            'raycaster': Raycaster(context),
            'start_pos': mouse_pos,
            'end_pos': mouse_pos,
            'first': self.select_first_vertex,
            'last': self.select_last_vertex,
            'elements': {},
        }
        self.elem_type_start = elem_type

        def is_currently_selected():
            return (len(elements) > 0) and all(elem.select for elem in elements)

        extend = False

        if self.selection_mode == 'ADD':
            extend = True
        elif self.selection_mode == 'SEMI_OVERRIDE':
            extend = is_currently_selected()
        elif self.selection_mode == 'TOGGLE':
            self.select_value = not is_currently_selected()
            extend = True
        elif self.selection_mode == 'REMOVE':
            self.select_value = False
            extend = True

        if extend:
            def add(bm, elements):
                for elem in elements:
                    if elem.select:
                        self.all_elements.add(elem)

            for selection_state in self.selection_state_original.values():
                bm = selection_state.bm

                add(bm, bm.verts)
                add(bm, bm.edges)
                add(bm, bm.faces)

                # Note: do NOT add all selected elements to history, this may cause
                # crashes in some cases (e.g. TOGGLE + mesh.vert_connect_path())
                # If we only add those that were in actual history, it doesn't crash
                bm_history = self.selection_history['elements'].setdefault(bm, [])
                bm_history.extend(elem for elem in bm.select_history if elem.select)

        self.add_selection_elements(obj, bm, elem_type, elements)

    def on_mousemove(self, context, event):
        if self.selection_mode == 'KEEP':
            return

        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        if context.mode == 'OBJECT':
            # We can't use bpy.ops.view3d.select, because it crashes during a modal operator
            ray_origin, ray_direction = Raycaster.ray(context, mouse_pos)
            raycast_result = Raycaster.query(context, ray_origin, ray_direction)
            hit, location, normal, index, obj, matrix = raycast_result
            if obj:
                obj.select_set(self.select_value)
        elif context.mode == 'EDIT_MESH':
            elem_types = ({self.elem_type_start} if self.select_lock_element_type else self.elem_types)
            self.selection_history['end_pos'] = mouse_pos
            result = find_closest_mesh_element(context, mouse_pos, elem_types)
            obj, bm, elem_type, elements = result
            self.add_selection_elements(obj, bm, elem_type, elements)

    def on_wheel(self, context, event):
        if self.selection_mode == 'KEEP':
            return

        if context.mode == 'OBJECT':
            return

        if event.type == 'WHEELUPMOUSE':
            self.selection_dilation += 1
            self.update_selection()
        elif event.type == 'WHEELDOWNMOUSE':
            self.selection_dilation -= 1
            self.update_selection()

    def on_cancel(self, context):
        if self.selection_mode == 'KEEP':
            return

        if context.mode == 'OBJECT':
            restore_object_selection(self.selection_state_original)
        elif context.mode == 'EDIT_MESH':
            restore_mesh_selection(self.selection_state_original)

    def add_selection_elements(self, obj, bm, elem_type, elements):
        if self.use_update_highlight:
            NFlow.update_scene_ref()
            NFlow.show_highlight = True

        if (self.elem_type_start == 'NONE') and ('OVERRIDE' in self.selection_mode):
            self.update_selection()
            return

        if not (obj and bm and elements):
            return

        if self.select_lock_element_type and (elem_type != self.elem_type_start):
            return

        self.all_bms[bm] = obj

        if self.select_value:
            new_elements = []
            bm_history = self.selection_history['elements'].setdefault(bm, [])
            for elem in elements:
                if elem not in self.all_elements:
                    bm_history.append(elem)
                    new_elements.append(elem)

            self.all_elements.update(new_elements)
        else:
            bm_history = self.selection_history['elements'].get(bm)

            def discard_element(elem):
                if bm_history:
                    try:
                        bm_history.remove(elem)
                    except ValueError:
                        pass
                self.all_elements.discard(elem)

            def discard_elements(elems):
                for elem in elems:
                    discard_element(elem)

            for elem in elements:
                discard_element(elem)
                if isinstance(elem, BMVert):
                    discard_elements(elem.link_edges)
                    discard_elements(elem.link_faces)
                elif isinstance(elem, BMEdge):
                    discard_elements(elem.verts)
                    discard_elements(elem.link_faces)
                elif isinstance(elem, BMFace):
                    discard_elements(elem.verts)
                    discard_elements(elem.edges)

            new_elements = elements

        self.update_selection()

        if self.use_update_highlight:
            if not self.select_value:
                NFlow.display_verts.clear()
                NFlow.display_edges.clear()
                NFlow.display_faces.clear()

            elem_color = None
            if elem_type:
                elem_color = PresetOverride.get(f'color_{elem_type.lower()}', (1,1,1,1))
                elem_color = (*elem_color[:3], min(elem_color[3], 0.5))

            NFlow.add_elements(obj.matrix_world, new_elements, elem_color)

    def update_selection(self):
        self.select_elements(self.all_bms, self.all_elements, self.selection_history,
            self.selection_dilation)

    @classmethod
    def deselect_all(cls):
        # A built-in operator is faster, but it gets recorded in the Info log
        context = bpy.context
        if context.mode == 'OBJECT':
            for obj in context.scene.objects:
                try:
                    obj.select_set(False)
                except Exception:
                    pass
        elif context.mode == 'EDIT_MESH':
            for obj, mesh, bm in EditableMeshes.all():
                for v in bm.verts:
                    v.select = False
                bm.select_flush(False)

    @classmethod
    def select_elements(cls, bms, elements, history, dilation=0):
        cls.deselect_all()

        for elem in elements:
            elem.select = True

        if history:
            def find_nearest_vertex(bm, verts, mouse_pos):
                with history['raycaster'] as raycaster:
                    obj = bms[bm]
                    element_sets = [(obj, verts)]
                    p, _, v = raycaster.nearest_along_ray(mouse_pos, element_sets,
                        use_raycast=True, use_depth=False)
                    if p is None:
                        return next(iter(verts))
                    if v is None:
                        matrix = obj.matrix_world
                        v = sorted((((matrix @ v.co) - p).length_squared, i, v)
                            for i, v in enumerate(verts))[0][-1]
                    return v

            def prepend_vert(bm_history, v):
                try:
                    i = bm_history.index(v)
                    bm_history[i], bm_history[0] = bm_history[0], bm_history[i]
                except ValueError:
                    bm_history.insert(0, v)

            def append_vert(bm_history, v):
                try:
                    i = bm_history.index(v)
                    bm_history[i], bm_history[-1] = bm_history[-1], bm_history[i]
                except ValueError:
                    bm_history.append(v)

            add_first_vertex = history['first']
            add_last_vertex = history['last']

            for bm, bm_history in history['elements'].items():
                if bm_history:
                    # This is needed for operators such as mesh.merge at first / last vertex
                    if add_first_vertex:
                        if not isinstance(bm_history[0], BMVert):
                            verts = bm_history[0].verts
                            v = find_nearest_vertex(bm, verts, history['start_pos'])
                            prepend_vert(bm_history, v)
                    if add_last_vertex:
                        verts = {v for elem in bm_history for v in getattr(elem, 'verts', (elem,))}
                        v = find_nearest_vertex(bm, verts, history['end_pos'])
                        was_first = (v == bm_history[0])
                        append_vert(bm_history, v)
                        if was_first and (len(bm_history) > 1):
                            if not isinstance(bm_history[0], BMVert):
                                verts = [v2 for v2 in bm_history[0].verts if v2 != v]
                                v = find_nearest_vertex(bm, verts, history['start_pos'])
                                prepend_vert(bm_history, v)

                bm.select_history.clear()
                for elem in bm_history:
                    bm.select_history.add(elem)

        for bm in bms:
            bm.select_flush(False)

        if dilation != 0:
            op = (bpy.ops.mesh.select_less if dilation < 0 else bpy.ops.mesh.select_more)
            for i in range(abs(dilation)):
                op(use_face_step=True)


class Raycaster:
    obj_types = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}

    @classmethod
    def project(cls, context, position):
        region = context.region
        rv3d = context.region_data
        return location_3d_to_region_2d(region, rv3d, position)

    @classmethod
    def project_occluded(cls, context, position):
        """
        smae as bpy_extras.view3d_utils.location_3d_to_region_2d but returns 2d vector even if point is behind the view
        """
        from mathutils import Vector
        region = context.region
        rv3d = context.region_data
        coord = position

        prj = rv3d.perspective_matrix @ Vector((coord[0], coord[1], coord[2], 1.0))
        width_half = region.width / 2.0
        height_half = region.height / 2.0

        return Vector((
            width_half + width_half * (prj.x / prj.w),
            height_half + height_half * (prj.y / prj.w),
        ))

    @classmethod
    def unproject(cls, context, coord, depth_location):
        region = context.region
        rv3d = context.region_data
        return region_2d_to_location_3d(region, rv3d, coord, depth_location)

    @classmethod
    def ray(cls, context, position):
        region = context.region
        rv3d = context.region_data
        origin = region_2d_to_origin_3d(region, rv3d, position)
        direction = region_2d_to_vector_3d(region, rv3d, position)
        return origin, direction

    @classmethod
    def ray_line(cls, context, position):
        region = context.region
        is_perspective, near, far = get_view_frustum_info(context)
        view_center = Vector((region.width*0.5, region.height*0.5))
        view_origin, view_direction = cls.ray(context, view_center)
        origin, direction = cls.ray(context, position)
        endpoint_scale = (far - near) / view_direction.dot(direction)
        endpoint = origin + direction * endpoint_scale
        return origin, endpoint

    @classmethod
    def query(cls, context, origin, direction=None, distance=math.inf, use_target=True):
        raycaster = Raycaster(context, use_target)
        result = raycaster.query(origin, direction, distance)
        raycaster.cleanup()
        return result

    @classmethod
    def face(cls, face, matrix, origin, direction=None):
        best_p, best_n, best_dist = None, None, math.inf
        verts = [(matrix @ v.co) for v in face.verts]

        for i0, i1, i2 in tessellate_polygon([verts]):
            v0 = verts[i0]
            v1 = verts[i1]
            v2 = verts[i2]

            if direction is None:
                p = closest_point_on_tri(origin, v0, v1, v2)
                dist = (p - origin).length_squared
            else:
                p = intersect_ray_tri(v0, v1, v2, direction, origin)
                if p is None:
                    continue
                dist = direction.dot(p - origin)

            if dist < best_dist:
                normal = (v1 - v0).cross(v2 - v0)
                best_p, best_n, best_dist = p, normal, dist

        if best_n is not None:
            best_n.normalize()

        return best_p, best_n

    @classmethod
    def edge(cls, edge, matrix, origin, endpoint=None, clamp=False):
        v0, v1 = edge.verts
        p0, p1 = (matrix @ v0.co), (matrix @ v1.co)

        delta = p1 - p0
        mag2 = delta.length_squared
        if mag2 <= 0:
            return ((p0, 0.0) if (endpoint is None) or clamp else (None, None))

        if endpoint is None:
            t = min(max(delta.dot(origin - p0) / mag2, 0), 1)
            return (p0 + delta * t, t)

        result = intersect_line_line(p0, p1, origin, endpoint)
        if result is None:
            return (p0 + delta * 0.5, 0.5)

        pos3d, _ = result

        t = (0 if pos3d is None else delta.dot(pos3d - p0) / mag2)

        if clamp:
            t = min(1, max(0, t))

        return ((p0 + delta * t, t) if (t >= 0) and (t <= 1) else (None, None))

    def __init__(self, context, use_target=True):
        def update(context, use_target=True):
            self.__update(context, use_target)
        self.objs = None
        self.hidden = []
        self.update = update
        update(context, use_target)

    def __update(self, context, use_target=True):
        region = context.region
        rv3d = context.region_data
        depsgraph = context.view_layer.depsgraph
        scene = context.scene
        nflow_config_scene = scene.nsolve.ops.nflow
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        target = (nflow_config_scene.projection_target if use_target else None)
        exclude = {obj for obj in context.editable_objects if obj.mode == 'EDIT'}

        self.auto_shrinkwrap_mode = 'NONE'
        if nflow_config_workspace.use_auto_shrinkwrap:
            self.auto_shrinkwrap_mode = nflow_config_workspace.auto_shrinkwrap_mode

        self.is_perspective, self.near, self.far = get_view_frustum_info(context)
        self.view_center = Vector((region.width*0.5, region.height*0.5))
        self.view_origin, self.view_direction = Raycaster.ray(context, self.view_center)

        # In local view, visible_in_viewport_get returns False for both hidden and not-hidden objects

        def project(position):
            return location_3d_to_region_2d(region, rv3d, position)

        def unproject(coord, depth_location):
            return region_2d_to_location_3d(region, rv3d, coord, depth_location)

        def ray(position):
            origin = region_2d_to_origin_3d(region, rv3d, position)
            direction = region_2d_to_vector_3d(region, rv3d, position)
            return origin, direction

        def ray_line(position):
            origin, direction = self.ray(position)
            endpoint_scale = (self.far - self.near) / self.view_direction.dot(direction)
            endpoint = origin + direction * endpoint_scale
            return origin, endpoint

        def hide_hidden():
            for obj, is_selected in self.hidden:
                obj.hide_viewport = True

        def unhide_hidden():
            for obj, is_selected in self.hidden:
                obj.hide_viewport = False
                obj.select_set(is_selected)

        display_types = ('SOLID', 'TEXTURED')
        def is_queryable(obj):
            return ((obj.type in self.obj_types) and obj.visible_get() and
                (obj not in exclude) and (obj.display_type in display_types))

        def query_nearest(origin, distance):
            if self.objs is None:
                self.objs = ([target] if target else context.visible_objects)
                self.objs = [obj for obj in self.objs if is_queryable(obj)]

            best_dist = math.inf
            best_result = None

            for obj in self.objs:
                matrix = obj.matrix_world
                matrix_inv = matrix.inverted_safe()

                o = matrix_inv @ origin

                try:
                    result = obj.closest_point_on_mesh(o, distance=distance, depsgraph=depsgraph)
                except Exception:
                    continue # could not create BVH tree (e.g. if mesh is too big)

                hit, location, hormal, index = result

                if hit:
                    location = matrix @ location
                    dist = (location - origin).length_squared
                    if dist < best_dist:
                        best_dist = dist
                        best_result = (hit, location, hormal, index, obj, matrix)

            if not best_result:
                return False, Vector(), Vector(), -1, None, Matrix()

            return best_result

        def query_ray(origin, direction, distance):
            if target:
                obj = target
                matrix = obj.matrix_world
                matrix_inv = matrix.inverted_safe()
                o = matrix_inv @ origin
                d = matrix_inv.to_3x3() @ direction

                try:
                    result = obj.ray_cast(o, d, distance=distance, depsgraph=depsgraph)
                except Exception:
                    return (False, Vector(), Vector(), -1, None, Matrix())

                hit, location, hormal, index = result
                if not hit:
                    return (hit, location, hormal, index, None, Matrix())

                location = matrix @ location
                return (hit, location, hormal, index, obj, matrix)

            # The list of hidden objects is primarily intended as a way to reduce
            # the number of unnecessary raycasts. To avoid the potential errors
            # due to objects remaining hidden, we always unhide them afterwards.

            if not self.is_batch_mode:
                hide_hidden()

            while True:
                result = scene.ray_cast(depsgraph, origin, direction, distance=distance)
                obj = result[-2]
                if (not obj) or is_queryable(obj):
                    break

                is_selected = obj.select_get() # do this *before* hiding
                obj.hide_viewport = True
                self.hidden.append((obj, is_selected))

            if not self.is_batch_mode:
                unhide_hidden()

            return result

        def query(origin, direction=None, distance=math.inf):
            if target and ((not target.visible_get()) or (target in exclude)):
                # hit, location, normal, index, obj, matrix
                return False, Vector(), Vector(), -1, None, Matrix()

            if direction is None:
                return query_nearest(origin, distance)
            else:
                return query_ray(origin, direction, distance)

        def cleanup():
            unhide_hidden()
            self.hidden.clear()
            self.is_batch_mode = False

        def batch():
            self.is_batch_mode = True
            return self

        self.project = project
        self.unproject = unproject
        self.ray = ray
        self.ray_line = ray_line
        self.query = query
        self.cleanup = cleanup
        self.batch = batch
        self.is_batch_mode = False

    def __call__(self, origin, direction=None, distance=math.inf):
        return self.query(origin, direction, distance)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.cleanup()

    def nearest_along_ray(self, mouse_pos, element_sets, use_raycast, use_depth=False, clamp=False):
        mouse_pos = Vector(mouse_pos)
        origin, direction = self.ray(mouse_pos)
        endpoint_scale = (self.far - self.near) / self.view_direction.dot(direction)
        endpoint = origin + direction * endpoint_scale

        if use_raycast:
            result = self.query(origin, direction)
            if result[0]:
                return result[1], None, None

        candidate_key = (lambda item: item[0])

        best_dist = math.inf
        best_p = None
        best_obj = None
        best_elem = None

        for obj, elements in element_sets:
            matrix = obj.matrix_world

            candidates = []

            for elem in elements:
                if isinstance(elem, BMVert):
                    pos3d = matrix @ elem.co
                elif isinstance(elem, BMEdge):
                    pos3d, t = Raycaster.edge(elem, matrix, origin, endpoint, clamp=clamp)
                elif isinstance(elem, BMFace):
                    pos3d, normal = Raycaster.face(elem, matrix, origin, direction)
                else:
                    continue

                if pos3d is None:
                    continue

                if use_depth:
                    distance3d = direction.dot(pos3d - origin)
                    candidates.append((distance3d, pos3d, None, obj, elem))
                else:
                    pos2d = self.project(pos3d)
                    if pos2d is not None:
                        distance2d = (pos2d - mouse_pos).magnitude
                        if clamp and isinstance(elem, BMEdge):
                            # For edges, adjust the distance slightly (within 1 pixel)
                            # to select the closest edge when they share a nearest point
                            v0, v1 = elem.verts
                            edge_proj = self.project_edge(matrix, v0, v1)
                            if edge_proj:
                                dp0 = edge_proj[0][1] - pos2d
                                dp1 = edge_proj[1][1] - pos2d
                                dp = (dp0 if dp0.length_squared > dp1.length_squared else dp1)
                                dpn = dp.normalized()
                                dn = (pos2d - mouse_pos).normalized()
                                distance2d += dn.dot(dpn)
                        candidates.append((distance2d, pos3d, pos2d, obj, elem))

            candidates.sort(key=candidate_key)

            ignore_visibility = (not use_raycast) or use_depth

            for distance, pos3d, pos2d, obj, elem in candidates:
                if ignore_visibility or self.is_visible(pos3d, pos2d):
                    if distance < best_dist:
                        best_dist = distance
                        best_p = pos3d
                        best_obj = obj
                        best_elem = elem
                    break

        if best_p is not None:
            return origin + direction * direction.dot(best_p - origin), best_obj, best_elem

        return None, None, None

    def nearest_to_point(self, origin, element_sets):
        candidate_key = (lambda item: item[0])

        best_dist = math.inf
        best_p = None
        best_obj = None
        best_elem = None

        for obj, elements in element_sets:
            matrix = obj.matrix_world

            candidates = []

            for elem in elements:
                if isinstance(elem, BMVert):
                    pos3d = matrix @ elem.co
                elif isinstance(elem, BMEdge):
                    pos3d, t = Raycaster.edge(elem, matrix, origin)
                elif isinstance(elem, BMFace):
                    pos3d, normal = Raycaster.face(elem, matrix, origin)
                else:
                    pos3d = None

                if pos3d is not None:
                    distance3d = (pos3d - origin).length_squared
                    candidates.append((distance3d, pos3d, obj, elem))

            candidates.sort(key=candidate_key)

            for distance3d, pos3d, obj, elem in candidates:
                if distance3d < best_dist:
                    best_dist = distance3d
                    best_p = pos3d
                    best_obj = obj
                    best_elem = elem
                break

        if best_p is not None:
            return best_p, best_obj, best_elem

        return None, None, None

    def project_edge(self, matrix, v0, v1):
        v0_3d = matrix @ v0.co
        v1_3d = matrix @ v1.co
        v0_2d = self.project(v0_3d)
        v1_2d = self.project(v1_3d)

        is_reverse = False
        if v0_2d is None:
            if v1_2d is None:
                return None
            v0_3d, v1_3d = v1_3d, v0_3d
            v0_2d, v1_2d = v1_2d, v0_2d
            is_reverse = True

        count = 0
        while v1_2d is None:
            v1_3d = v0_3d.lerp(v1_3d, 0.01)
            v1_2d = self.project(v1_3d)
            count += 1
            if count > 50:
                return None

        if is_reverse:
            return (v1_3d, v1_2d), (v0_3d, v0_2d)
        else:
            return (v0_3d, v0_2d), (v1_3d, v1_2d)

    def is_visible(self, pos3d, pos2d=None, distance_scale=0.999):
        # NOTE: raycaster cleanup is expected to be done by the caller
        if pos2d is None:
            pos2d = self.project(pos3d)
            if pos2d is None:
                return False

        origin, direction = self.ray(pos2d)
        distance = distance_scale * direction.dot(pos3d - origin)
        result = self.query(origin, direction, distance)
        return not result[0]

    def snap_verts_to_surface(self, obj, verts, epsilon=1e-4):
        matrix = obj.matrix_world
        matrix_inv = matrix.inverted_safe()
        matrix_3x3 = matrix.to_3x3()

        with self.batch():
            for v in verts:
                if v is None:
                    continue
                v.normal_update()
                v.co = self._snap_point_to_surface(matrix, matrix_3x3, matrix_inv,
                    v.co, v.normal, epsilon)

    def snap_points_to_surface(self, matrix, points, directions, output=None, epsilon=1e-4):
        matrix_inv = matrix.inverted_safe()
        matrix_3x3 = matrix.to_3x3()

        if output is None:
            output = [None] * len(points)

        with self.batch():
            for i in range(len(points)):
                output[i] = self._snap_point_to_surface(matrix, matrix_3x3, matrix_inv,
                    points[i], (directions[i] if directions else None), epsilon)

        return output

    def _snap_query(self, origin, direction, offset):
        offset = direction * offset
        result_fwd = self.query(origin - offset, direction)
        result_bwd = self.query(origin + offset, -direction)

        if not result_fwd[0]:
            result_fwd = result_bwd
        elif result_bwd[0]:
            mag2_fwd = (result_fwd[1] - origin).length_squared
            mag2_bwd = (result_bwd[1] - origin).length_squared
            if mag2_fwd > mag2_bwd:
                result_fwd = result_bwd

        return result_fwd

    def _snap_point_to_surface(self, matrix, matrix_3x3, matrix_inv, point, direction, epsilon=1e-4):
        if self.auto_shrinkwrap_mode == 'NONE':
            return point

        origin = matrix @ point
        offset = None

        if self.auto_shrinkwrap_mode == 'PROJECT_VIEW':
            pos2d = self.project(origin)
            if pos2d is None:
                t = max(self.view_direction.dot(origin - self.view_origin), 0)
                pos2d = self.project(self.view_origin + self.view_direction * t)
            direction = self.ray(pos2d)[1]
            offset = epsilon / math.sqrt(direction.length_squared)
        else:
            if self.auto_shrinkwrap_mode == 'PROJECT':
                dir_mag2 = (0 if direction is None else direction.length_squared)
                if dir_mag2 > 0:
                    direction = matrix_3x3 @ direction
                    offset = epsilon / math.sqrt(dir_mag2)
                else:
                    direction = None
            else:
                direction = None

        if offset is None:
            result = self.query(origin, direction)
        else:
            result = self._snap_query(origin, direction, offset)

        return (matrix_inv @ result[1] if result[0] else point)

    def snap_point_to_surface(self, point, direction, epsilon=1e-4):
        dir_mag2 = (0 if direction is None else direction.length_squared)

        if dir_mag2 > 0:
            result = self._snap_query(origin, direction, epsilon / math.sqrt(dir_mag2))
        else:
            result = self.query(point)

        return (result[1] if result[0] else point)

# Apparently, Blender's convex_hull_2d may crash on some inputs
# This implementation is adapted from
# https://en.wikibooks.org/wiki/Algorithm_Implementation/Geometry/Convex_hull/Monotone_chain
class ConvexHull2D:
    def __init__(self, source=None):
        if isinstance(source, ConvexHull2D):
            self.counter = source.counter
            self.lower = list(source.lower)
            self.upper = list(source.upper)
        else:
            self.counter = 0
            self.lower = []
            self.upper = []

    def add(self, p):
        p = ((p[0], p[1]), self.counter)
        self.counter += 1

        self.update(self.lower, p, -1)
        self.update(self.upper, p, +1)

    def count(self):
        return len(self.upper) + len(self.lower) - 2

    def indices(self):
        for i in range(len(self.upper)-1):
            yield self.upper[i][-1]

        for i in range(len(self.lower)-1, 0, -1):
            yield self.lower[i][-1]

    def points(self):
        for i in range(len(self.upper)-1):
            yield self.upper[i][0]

        for i in range(len(self.lower)-1, 0, -1):
            yield self.lower[i][0]

    key = (lambda p: p[0])
    cross = (lambda o, a, b: (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0]))

    def update(self, hull, p, sign):
        key = ConvexHull2D.key
        cross = ConvexHull2D.cross
        bisect_left = bisect.bisect_left

        i = bisect_left(hull, p[0], key=key)

        if (i > 0) and (i < len(hull)):
            if cross(hull[i-1][0], hull[i][0], p[0])*sign <= 0:
                return

        hull.insert(i, p)

        i1, i2 = i+1, i+2
        while (i2 < len(hull)) and (cross(p[0], hull[i2][0], hull[i1][0])*sign <= 0):
            hull.pop(i1)

        i1, i2 = i-1, i-2
        while (i2 >= 0) and (cross(hull[i2][0], p[0], hull[i1][0])*sign <= 0):
            hull.pop(i1)
            i, i1, i2 = i1, i2, i2-1

# Winding number test for a point in a polygon
# Adapted from http://geomalgorithms.com/a03-_inclusion.html
def winding_number(point, polygon):
    wn = 0

    # Points may be 3D
    px = point[0]
    py = point[1]

    for index in range(len(polygon)):
        vertex0 = polygon[index-1]
        vertex1 = polygon[index]

        v0x = vertex0[0]
        v0y = vertex0[1]
        v1x = vertex1[0]
        v1y = vertex1[1]

        if v0y <= py:
            if v1y > py:
                if (v1x - v0x) * (py - v0y) - (px - v0x) * (v1y - v0y) > 0:
                    wn += 1
        else:
            if v1y <= py:
                if (v1x - v0x) * (py - v0y) - (px - v0x) * (v1y - v0y) < 0:
                    wn -= 1

    return wn


def polygon_2d_area(points, signed=False):
    area = 0.0

    if len(points) >= 3:
        p0 = points[-1]
        for p1 in points:
            area += (p0[0]+p1[0])*(p0[0]-p1[0])
            p0 = p1

    if not signed:
        area = abs(area)

    return area * 0.5


def polygon_3d_area(points, signed=False):
    if len(points) < 3:
        return 0.0

    area = 0.0
    for i in range(len(points)):
        area += area_tri(points[i-2], points[i-1], points[i])
    return area


def calc_edge_normal(e):
    n = None
    for f in e.link_faces:
        fn = f.normal
        n = (fn if n is None else (n + fn if n.dot(fn) > 0 else n - fn))
    if n is None:
        v0, v1 = e.verts
        n = (v1.co - v0.co).orthogonal()
    return n.normalized()


def closest_point_on_line(p, a, b):
    delta = b - a
    mag2 = delta.length_squared
    if not (mag2 > 0):
        return a
    t = min(max(delta.dot(p-a) / mag2, 0), 1)
    return a + delta * t


def point_line_distance(p, a, b):
    return (closest_point_on_line(p, a, b) - p).magnitude


def transform_normal(matrix, normal, normalize=True):
    if len(matrix) != 3:
        matrix = matrix.to_3x3()
    tangent1 = normal.orthogonal()
    tangent2 = normal.cross(tangent2)
    normal = (matrix @ tangent1).cross(matrix @ tangent2)
    if normalize:
        normal.normalize()
    return normal


# This is mainly necessary because bmesh.from_edit_mesh(mesh)
# may return a different BMesh instance if the previous one
# was modified. So here we try to centralize them in one place.
class EditableMeshes:
    Item = collections.namedtuple('Item', ['obj', 'mesh', 'bm'])

    __items = {}

    keep = False

    @classmethod
    def clear(cls):
        cls.__items = {}

    @classmethod
    def objs(cls, context=None, force=False):
        return cls.get(context, force).keys()

    @classmethod
    def all(cls, context=None, force=False):
        return cls.get(context, force).values()

    @classmethod
    def get_bm(cls, key):
        items = cls.get()

        if isinstance(key, bpy.types.Mesh):
            for obj, mesh, bm in items.values():
                if key == mesh:
                    return bm
            return None

        item = items.get(key)
        return (None if item is None else item.bm)

    @classmethod
    def get(cls, context=None, force=False):
        if context is None:
            context = bpy.context

        if (not cls.keep) or force:
            cls.__items = {}
        else:
            # Make sure we don't try comparing with a no longer valid object
            cls.__items = {obj: item for obj, item in cls.__items.items() if is_valid(obj)}

        items = {}

        for obj in context.editable_objects:
            if (obj.type != 'MESH') or (obj.mode != 'EDIT'):
                continue

            mesh = obj.data

            item = cls.__items.get(obj)

            if (item is None) or (mesh != item.mesh) or (not item.bm.is_valid):
                bm = bmesh.from_edit_mesh(mesh)
            else:
                bm = item.bm

            items[obj] = cls.Item(obj, mesh, bm)

        if cls.keep:
            cls.__items = items

        return items


def store_object_selection():
    return dict(selected=set(bpy.context.selected_objects), active=bpy.context.object)


def restore_object_selection(infos):
    view_layer = bpy.context.view_layer

    active = infos['active']
    selected = infos['selected']

    try:
        view_layer.objects.active = active
    except Exception: # happens when obj is not in view layer
        pass

    for obj in view_layer.objects:
        obj.select_set(obj in selected)


def cleanup_object_selection(infos):
    infos['selected'].clear()
    infos['active'] = None


class MeshSelectionState:
    def __init__(self, bm):
        self.bm = bm
        self.active_face = bm.faces.active
        elements = itertools.chain(bm.faces, bm.edges, bm.verts)
        self.selection = {elem: elem.select for elem in elements}
        self.history = list(bm.select_history)

    def cleanup(self):
        self.selection.clear()
        self.history.clear()
        self.active_face = None
        self.bm = None

    def restore(self):
        bm = self.bm

        bm.select_history.clear()
        select_history_add = bm.select_history.add
        for elem in self.history:
            if elem and elem.is_valid:
                select_history_add(elem)

        active_face = self.active_face
        if active_face and active_face.is_valid:
            bm.faces.active = active_face

        # IMPORTANT: we need to set the selection state
        # of faces, then edges, then verts, because
        # faces affect edges, and edges affect verts
        selection = self.selection
        for elem in itertools.chain(bm.faces, bm.edges, bm.verts):
            elem.select = selection.get(elem, False)


def store_mesh_selection():
    return {mesh: MeshSelectionState(bm) for obj, mesh, bm in EditableMeshes.all()}


def restore_mesh_selection(selection_states):
    for obj, mesh, bm in EditableMeshes.all():
        selection_state = selection_states.get(mesh)

        if selection_state and selection_state.bm.is_valid:
            selection_state.restore()
        else:
            bm.select_history.clear()
            for v in bm.verts:
                v.select_set(False)
            bm.select_flush(False)


def cleanup_mesh_selection(selection_states):
    for selection_state in selection_states.values():
        selection_state.cleanup()

    selection_states.clear()


def mesh_selection_cast(context, location):
    # If we want to preserve the original selection, we can't
    # avoid the brute-force loop over vertices in python.
    # However, for moderate polycounts it's not a big issue.

    location = tuple(int(value) for value in location)

    active_obj = context.view_layer.objects.active

    editable_meshes = EditableMeshes.get()

    selection_state_original = store_mesh_selection()

    prev_select_mode = tuple(context.tool_settings.mesh_select_mode)

    context.tool_settings.mesh_select_mode = (True, True, False)
    bpy.ops.view3d.select('EXEC_DEFAULT', location=location)

    result_nonfaces = {}
    for obj, mesh, bm in editable_meshes.values():
        if bm.select_history.active:
            result_nonfaces = dict(obj=obj, mesh=mesh, bm=bm, elem=bm.select_history.active)

    context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.view3d.select('EXEC_DEFAULT', location=location)

    result_faces = {}
    for obj, mesh, bm in editable_meshes.values():
        if bm.select_history.active:
            result_faces = dict(obj=obj, mesh=mesh, bm=bm, elem=bm.select_history.active)

    restore_mesh_selection(selection_state_original)

    context.view_layer.objects.active = active_obj

    context.tool_settings.mesh_select_mode = prev_select_mode

    return result_nonfaces, result_faces


def linked_neighborhood(elem):
    if elem is None:
        return

    yield elem

    if isinstance(elem, BMVert):
        yield from elem.link_edges
        yield from elem.link_faces
    elif isinstance(elem, BMEdge):
        yield from elem.verts
        yield from elem.link_faces
    elif isinstance(elem, BMFace):
        yield from elem.verts
        yield from elem.edges


def expand_edge_selection(candidates, vert_filter, edge_filter):
    processed = set(candidates)
    wavefront = {(v, e) for e in candidates for v in e.verts}

    def propagate(v, e_prev):
        while True:
            if not vert_filter(v):
                return

            e_next = None
            for e in v.link_edges:
                if (e == e_prev) or e.hide or (not edge_filter(e, e_prev)):
                    continue
                if e_next:
                    return # non-manifold/ambiguous
                e_next = e

            if (e_next is None) or (e_next.hide):
                return

            if e_next in processed:
                wavefront.discard((v, e_next))
                return

            candidates.append(e_next)
            processed.add(e_next)

            v = e_next.other_vert(v)
            e_prev = e_next

    while wavefront:
        propagate(*wavefront.pop())


def count_visible_edges(vert):
    return sum(1 for e in vert.link_edges if not e.hide)


def count_visible_faces(edge):
    return sum(1 for f in edge.link_faces if not f.hide)


def find_edge_loop(edge, t=0.5):
    face_count = count_visible_faces(edge)

    v0, v1 = edge.verts
    edge_count = count_visible_edges(v0 if t < 0.5 else v1)

    def vert_filter(v):
        return count_visible_edges(v) == edge_count

    def edge_filter(e, e_prev):
        if count_visible_faces(e) != face_count:
            return False
        if face_count == 0:
            return True
        if edge_count < 3:
            return True
        if edge_count == 3:
            common_faces = set(e.link_faces).intersection(e_prev.link_faces)
            return all((len(f.verts) > 4) for f in common_faces)
        return set(e.link_faces).isdisjoint(e_prev.link_faces)

    candidates = [edge]
    expand_edge_selection(candidates, vert_filter, edge_filter)
    return candidates


def find_boundary_loop(edge):
    def vert_filter(v):
        return True

    def edge_filter(e, e_prev):
        return (count_visible_faces(e) < 2)

    if not edge_filter(edge, None):
        return []

    candidates = [edge]
    expand_edge_selection(candidates, vert_filter, edge_filter)
    return candidates


def get_view_frustum_info(context):
    rv3d = context.region_data
    space_data = context.space_data
    camera = space_data.camera

    is_camera = (rv3d.view_perspective == 'CAMERA') and bool(camera)

    if is_camera and (camera.type == 'CAMERA'):
        near, far = camera.data.clip_start, camera.data.clip_end
    else:
        near, far = space_data.clip_start, space_data.clip_end

    if not rv3d.is_perspective:
        near, far = -far*0.5, far*0.5

    return rv3d.is_perspective, near, far


def get_view_transform_info(context):
    region = context.region
    rv3d = context.region_data

    is_perspective, near, far = get_view_frustum_info(context)

    view_center = Vector((region.width*0.5, region.height*0.5))
    view_matrix = rv3d.view_matrix.to_3x3().inverted_safe()
    axis_x = view_matrix.col[0].normalized()
    axis_y = view_matrix.col[1].normalized()
    axis_z = -view_matrix.col[2].normalized()
    origin = region_2d_to_origin_3d(region, rv3d, view_center)

    # Use a rage some distance away from the perspective viewpoint
    z0, z1 = 1, 2
    p0 = origin + axis_z * z0
    p1 = origin + axis_z * z1

    def calc_linear_coefs(pixel_offset, ref_axis):
        offset = axis_x * pixel_offset[0] + axis_y * pixel_offset[1]
        v0 = 1 / (location_3d_to_region_2d(region, rv3d, p0 + offset) - view_center).magnitude
        v1 = 1 / (location_3d_to_region_2d(region, rv3d, p1 + offset) - view_center).magnitude
        s = (v1 - v0) / (z1 - z0)
        c = ((v0+v1) - (z0+z1) * s) * 0.5
        return c, s

        # This does not work properly when viewing from a camera
        # coord = view_center + Vector(pixel_offset)
        # dp0 = region_2d_to_location_3d(region, rv3d, coord, p0) - p0
        # dp1 = region_2d_to_location_3d(region, rv3d, coord, p1) - p1
        # v0 = ref_axis.dot(dp0)
        # v1 = ref_axis.dot(dp1)
        # return v0, abs(v1 - v0)

    cx, sx = calc_linear_coefs((1, 0), axis_x)
    cy, sy = calc_linear_coefs((0, 1), axis_y)
    if not is_perspective:
        sx, sy = 0.0, 0.0 # to avoid floating point errors
    cm, sm = (cx+cy)*0.5, (sx+sy)*0.5

    offset = Vector((cx, cy, cm))
    scale_z = Vector((sx, sy, sm))

    def get_scale_xy(p):
        z = axis_z.dot(p - origin)
        return (cx + sx * z, cy + sy * z)

    def get_scale(p):
        return cm + sm * axis_z.dot(p - origin)

    return {
        'region': region,
        'rv3d': rv3d,
        'center': view_center,
        'axis_x': axis_x,
        'axis_y': axis_y,
        'axis_z': axis_z,
        'origin': origin,
        'is_perspective': is_perspective,
        'near': near,
        'far': far,
        'scaling_coefs': (offset, scale_z),
        'get_scale_xy': get_scale_xy,
        'get_scale': get_scale,
    }


def find_closest_screenspace_element(context, elements, screen_pos, hit_plane=None, elem_type=None):
    region = context.region
    rv3d = context.region_data

    is_perspective, near, far = get_view_frustum_info(context)

    screen_pos = Vector(screen_pos)
    ray_origin, ray_direction = Raycaster.ray(context, screen_pos)
    ray_endpoint = ray_origin + ray_direction * (far - near)

    hit_plane_threshold = -1e-3
    hit_pos = None
    hit_normal = None
    if hit_plane:
        hit_pos, hit_normal = hit_plane
        if hit_normal.dot(ray_direction) > 0:
            hit_normal = -hit_normal

    def calc_dist(pos3d, radius=math.inf):
        if pos3d is None:
            return math.inf, math.inf

        if hit_pos is not None:
            if hit_normal.dot(pos3d - hit_pos) < hit_plane_threshold:
                return math.inf, math.inf

        pos2d = location_3d_to_region_2d(region, rv3d, pos3d)

        if pos2d is not None:
            dist2d = (pos2d - screen_pos).magnitude
            if dist2d <= radius:
                return dist2d, ray_direction.dot(pos3d - ray_origin)

        return math.inf, math.inf

    best_vert = None, None, None, 0.5, 0, math.inf
    best_edge = None, None, None, 0.5, 0, math.inf
    best_face = None, None, None, 0.5, 0, math.inf

    vert_radius_base = NFlowPrefs.get('vert_radius_base')
    edge_radius_base = NFlowPrefs.get('edge_radius_base')
    edge_radius_ext = NFlowPrefs.get('edge_radius_ext')
    edge_loop_fraction = NFlowPrefs.get('edge_loop_fraction')

    for obj, bm, elem in elements:
        matrix = obj.matrix_world
        if isinstance(elem, BMVert):
            dist2d, dist3d = calc_dist(matrix @ elem.co, vert_radius_base)
            if dist3d < best_vert[-1]:
                best_vert = obj, bm, elem, 0.5, dist2d/vert_radius_base, dist3d
        elif isinstance(elem, BMEdge):
            point, t = Raycaster.edge(elem, matrix, ray_origin, ray_endpoint)
            dist2d, dist3d = calc_dist(point, edge_radius_ext)
            if dist3d < best_edge[-1]:
                best_edge = obj, bm, elem, t, dist2d/edge_radius_base, dist3d
        elif isinstance(elem, BMFace):
            # At most one (raycasted) face is expected
            point, normal = Raycaster.face(elem, matrix, ray_origin, ray_direction)
            dist2d, dist3d = calc_dist(point)
            if dist3d < best_face[-1]:
                best_face = obj, bm, elem, 0.5, 0, dist3d

    def sort_perimeter_edges(elem):
        edges = list(elem.edges)
        best_index = 0
        best_edge = None, None, None, 0.5, 0, math.inf
        for i, elem in enumerate(edges):
            point, t = Raycaster.edge(elem, matrix, ray_origin, ray_endpoint)
            dist2d, dist3d = calc_dist(point, edge_radius_ext)
            if dist3d < best_edge[-1]:
                best_edge = obj, bm, elem, t, dist2d/edge_radius_base, dist3d
                best_index = i
        if best_index > 0:
            edges = edges[best_index:] + edges[:best_index]
        return edges

    if not isinstance(elem_type, str):
        elem_types_edges_inner = {'EDGE', 'EDGE_LOOP'}
        elem_types_edges_outer = {'PERIMETER', 'BOUNDARY'}
        elem_types_verts = {'VERTEX'}
        elem_types_edges = elem_types_edges_inner | elem_types_edges_outer
        elem_types_faces = {'FACE'}

        if elem_type is None:
            elem_type = elem_types_verts | elem_types_edges | elem_types_faces

        if best_vert[0] and not elem_type.isdisjoint(elem_types_verts):
            elem_type = 'VERTEX'
        elif best_edge[0] and not elem_type.isdisjoint(elem_types_edges):
            use_outer = not elem_type.isdisjoint(elem_types_edges_outer)
            use_inner = not elem_type.isdisjoint(elem_types_edges_inner)
            obj, bm, elem, t, rel_dist, _ = best_edge
            if use_outer and ((rel_dist > 1) or (not use_inner)):
                is_perimeter = (best_face[2] in elem.link_faces)
                is_perimeter &= ('PERIMETER' in elem_type)
                elem_type = ('PERIMETER' if is_perimeter else 'BOUNDARY')
            elif use_inner:
                is_loop = (abs(t*2 - 1) > edge_loop_fraction) or ('EDGE' not in elem_type)
                is_loop &= ('EDGE_LOOP' in elem_type)
                elem_type = ('EDGE_LOOP' if is_loop else 'EDGE')
        elif best_face[0] and not elem_type.isdisjoint(elem_types_faces):
            elem_type = 'FACE'
        else:
            elem_type = 'NONE'

    if best_vert[0] and (elem_type == 'VERTEX'):
        obj, bm, elem, t, rel_dist, _ = best_vert
        return obj, bm, elem_type, [elem]
    elif best_edge[0] and (elem_type == 'EDGE'):
        obj, bm, elem, t, rel_dist, _ = best_edge
        return obj, bm, elem_type, [elem]
    elif best_edge[0] and (elem_type == 'EDGE_LOOP'):
        obj, bm, elem, t, rel_dist, _ = best_edge
        return obj, bm, elem_type, find_edge_loop(elem, t)
    elif best_edge[0] and (elem_type == 'BOUNDARY'):
        obj, bm, elem, t, rel_dist, _ = best_edge
        return obj, bm, elem_type, find_boundary_loop(elem)
    elif best_face[0] and (elem_type == 'PERIMETER'):
        obj, bm, elem, t, rel_dist, _ = best_face
        return obj, bm, elem_type, sort_perimeter_edges(elem)
    elif best_face[0] and (elem_type == 'FACE'):
        obj, bm, elem, t, rel_dist, _ = best_face
        return obj, bm, elem_type, [elem]
    else:
        return None, None, 'NONE', []


def find_closest_mesh_element(context, screen_pos, elem_type=None):
    if context.mode != 'EDIT_MESH':
        return None, None, 'NONE', []

    elements = []

    result_nonfaces, result_faces = mesh_selection_cast(context, screen_pos)
    obj = result_nonfaces.get('obj')
    bm = result_nonfaces.get('bm')
    elem = result_nonfaces.get('elem')

    # Only the raycasted face can be the closest, but edges/verts may still be in front
    elements.extend((obj, bm, elem) for elem in linked_neighborhood(elem)
        if not (elem.hide or isinstance(elem, BMFace)))

    hit_plane = None

    def is_in_front(obj):
        return (bool(obj) and obj.show_in_front) or get_view3d_xray() or get_view3d_retopo_overlay()

    if not (is_in_front(obj) or is_in_front(result_faces.get('obj'))):
        ray_origin, ray_direction = Raycaster.ray(context, screen_pos)
        raycast_result = Raycaster.query(context, ray_origin, ray_direction)
        hit, location, normal, index, obj, matrix = raycast_result

        if hit:
            hit_plane = location, normal

    obj = result_faces.get('obj')
    bm = result_faces.get('bm')
    elem = result_faces.get('elem')

    nflow_config_workspace = context.workspace.nsolve.ops.nflow
    detect_under_scene_geometry = not nflow_config_workspace.use_hover_occlusion

    if elem is not None:
        if elem.hide or not isinstance(elem, BMFace):
            elem = None
        else:
            ray_origin, ray_direction = Raycaster.ray(context, screen_pos)
            hit_plane_face = Raycaster.face(elem, obj.matrix_world, ray_origin, ray_direction)

            if detect_under_scene_geometry or (hit_plane is None):
                hit_plane = hit_plane_face
                if hit_plane[0] is None:
                    hit_plane = None
            else:
                if hit_plane_face[0] is not None:
                    scene_ray_t = ray_direction.dot(hit_plane[0] - ray_direction)
                    face_ray_t = ray_direction.dot(hit_plane_face[0] - ray_direction)
                    if face_ray_t <= scene_ray_t:
                        hit_plane = hit_plane_face

    elements.extend((obj, bm, elem) for elem in linked_neighborhood(elem) if not elem.hide)

    return find_closest_screenspace_element(context, elements, screen_pos, hit_plane, elem_type)


def get_view3d_xray():
    space_data = getattr(bpy.context, 'space_data', None)
    shading = getattr(space_data, 'shading', None)
    return getattr(shading, 'show_xray', False)


def get_view3d_retopo_overlay():
    space_data = getattr(bpy.context, 'space_data', None)
    overlay = getattr(space_data, 'overlay', None)
    return getattr(overlay, 'show_retopology', False)


def blf_size(font, font_size):
    # The dpi argument became optional in Blender 3.4, and was removed in 4.0
    if bpy.app.version >= (3, 4, 0):
        blf.size(font, int(font_size))
    else:
        blf.size(font, int(font_size), 72)


def gpu_shader_from_builtin(name):
    if bpy.app.version >= (3, 4, 0):
        return gpu.shader.from_builtin(name)
    else:
        return gpu.shader.from_builtin('3D_'+name)


def get_cancel_event_types(event):
    return {('RIGHTMOUSE' if event.type != 'RIGHTMOUSE' else 'LEFTMOUSE'), 'ESC'}


class NFlow:
    behaviors = {}

    special_categories = {
        'nsolve': 'nSolve',
    }

    special_operators = None
    special_operators_items = None

    display_region = None
    display_mouse_pos = None
    hover_text = ''
    help_text = ''
    show_highlight = True

    ui_cheatsheet = None

    display_scene = None
    display_verts = []
    display_edges = []
    display_faces = []

    display_curve = []

    default_context_modes = {'EDIT_MESH'}

    @classmethod
    def update_special_operators(cls, force=True):
        if (not force) and (cls.special_operators is not None):
            return

        cls.special_operators = {}
        cls.special_operators_items = []

        for category_name, category_label in cls.special_categories.items():
            category = getattr(bpy.ops, category_name, None)
            if category is None:
                continue

            for op_name in dir(category):
                op = getattr(category, op_name)

                if 'INTERNAL' in op.bl_options:
                    continue

                op_rna = op.get_rna_type()

                prefixed_name = f'{category_label}: {op_rna.name}'
                if prefixed_name in cls.special_operators:
                    continue # some operator's labels may be the same

                item = (prefixed_name, op_rna.name, op_rna.description)
                cls.special_operators[prefixed_name] = op.idname_py()
                cls.special_operators_items.append((category_label, item))

    @classmethod
    def iterate_behaviors(cls, behavior_preset, elem_type, elements, context, event):
        if behavior_preset is None:
            return

        if isinstance(event, dict):
            modifiers = (('SHIFT', event['shift']), ('CTRL', event['ctrl']), ('ALT', event['alt']))
            modifiers = {key for key, value in modifiers if value}
            event_type = event['type']
        elif event is not None:
            modifiers = (('SHIFT', event.shift), ('CTRL', event.ctrl), ('ALT', event.alt))
            modifiers = {key for key, value in modifiers if value}
            event_type = event.type
        else:
            modifiers = None
            event_type = None

        cls.update_special_operators(force=False)

        use_context = (context is not None)

        for entry in behavior_preset.entries:
            if not entry.enable:
                continue

            if elem_type and (elem_type not in entry.elements):
                continue

            if event_type and (entry.event != event_type):
                continue

            if (modifiers is not None) and (entry.modifiers != modifiers):
                continue

            command, args = parse_operator_command(entry.behavior, True)

            behavior_info = cls.behaviors.get(command, None)
            if not behavior_info:
                op = get_operator(command, poll=use_context)
                if op:
                    yield entry, op, args
                continue

            if elem_type and (elem_type not in behavior_info.get('elements', ())):
                continue

            if (elements is not None) and (not behavior_info['type'].validate_elements(elements)):
                continue

            if use_context:
                context_modes = behavior_info.get('context_modes', cls.default_context_modes)
                if context.mode not in context_modes:
                    continue

            yield entry, behavior_info, args

    @classmethod
    def gather_element_types(cls, behavior_preset, context, event):
        elem_types = set()
        for entry, info, args in cls.iterate_behaviors(behavior_preset, None, None, context, event):
            if isinstance(info, dict):
                elem_types.update(entry.elements.intersection(info.get('elements', ())))
            else:
                elem_types.update(entry.elements)
        return elem_types

    @classmethod
    def gather_event_types(cls, behavior_preset, elem_type, elements, context, event, full_name=True):
        result = []
        for entry, info, args in cls.iterate_behaviors(behavior_preset, elem_type, elements, context, event):
            if elem_type and (event is not None):
                if any((entry.event == result_item['event']) for result_item in result):
                    continue
            name = cls.get_behavior_name(entry, info, full_name)
            result.append(dict(event=entry.event, modifiers=entry.modifiers, name=name,
                entry=entry, info=info, args=args))
        return result

    @classmethod
    def gather_capabilities(cls, behavior_preset):
        capabilities = set()
        for entry, info, args in cls.iterate_behaviors(behavior_preset, None, None, None, None):
            if isinstance(info, dict):
                capabilities.update(getattr(info['type'], 'capabilities', ()))
        return capabilities

    @classmethod
    def get_behavior(cls, behavior_preset, elem_type, elements, context, event, full_name=True):
        for entry, info, args in cls.iterate_behaviors(behavior_preset, elem_type, elements, context, event):
            name = cls.get_behavior_name(entry, info, full_name)
            if isinstance(info, dict):
                behavior_info = dict(info)
                behavior_info['name'] = name
                behavior_info['elem_types'] = entry.elements.intersection(info.get('elements', ()))
                behavior_info['options'] = cls.parse_behavior_options(behavior_info, entry)
            else:
                op = info
                behavior_info = {
                    'operator': op,
                    'name': name,
                    'elem_types': entry.elements,
                }

            for option_name in entry.option_names:
                behavior_info[option_name] = getattr(entry, option_name)

            behavior_info['kwargs'] = eval_operator_args(args)

            behavior_info['entry'] = entry

            return behavior_info

        return None

    @classmethod
    def get_behavior_name(cls, entry, info, full_name=True):
        if isinstance(info, dict):
            if entry.name:
                return entry.name
            if not full_name:
                return entry.behavior.split(':')[-1].strip()
            name = entry.behavior
            # The list of options can quickly get too verbose,
            # so we decided to omit them altogether for now
            # options = cls.parse_behavior_options(info, entry, use_visible=True)
            # if options:
            #     options = sorted(options.items())
            #     options = ', '.join(f'{name}: {value}' for name, value in options)
            #     name = f'{name} ({options})'
            return name
        else:
            op = info
            if entry.name:
                return entry.name
            elif op:
                return op.get_rna_type().name
            else:
                return ''

    @classmethod
    def parse_behavior_options(cls, behavior_info, entry, use_visible=False):
        options = behavior_info.get('options')
        if not isinstance(options, list):
            return (None if use_visible else options)

        new_options = {}

        for option_info in options:
            idname = option_info['idname']
            value = option_info['default']
            option_items = option_info.get('items')
            option = entry.find_option(idname)
            if option is not None:
                value = option.get_value(value, option_items)
            if use_visible and option_items:
                value = next(iter(item[1] for item in option_items if item[0] == value), value)
            key = (option_info['name'] if use_visible else idname)
            new_options[key] = value

        return new_options

    @classmethod
    def detect_closest_element(cls, context, mouse_pos, elem_type=None):
        obj, bm, elem_type, elements = find_closest_mesh_element(context, mouse_pos, elem_type)
        cls.update_display_data(obj, elem_type, elements)
        return obj, bm, elem_type, elements

    @classmethod
    def update_display_data(cls, obj, elem_type, elements):
        cls.cleanup()

        if (not elements) or (obj is None):
            return

        elem_color = PresetOverride.get(f'color_{elem_type.lower()}', (1,1,1,1))
        cls.update_scene_ref()
        cls.add_elements(obj.matrix_world, elements, elem_color)

    @classmethod
    def validate_display_data(cls, context):
        if cls.display_scene is None:
            return False

        if is_valid(cls.display_scene):
            return cls.show_highlight

        cls.cleanup()

        return False

    @classmethod
    def cleanup(cls):
        cls.display_scene = None
        cls.display_verts.clear()
        cls.display_edges.clear()
        cls.display_faces.clear()

        cls.display_curve.clear()

    @classmethod
    def update_scene_ref(cls):
        scene = bpy.context.scene
        if is_valid(cls.display_scene) and (cls.display_scene == scene):
            return

        cls.cleanup()
        cls.display_scene = scene

    @classmethod
    def add_elements(cls, matrix, elements, color=None, radius=None):
        if not radius:
            radius = NFlowPrefs.get('vert_radius_base')

        color_vert = PresetOverride.get('color_vertex')
        color_edge = PresetOverride.get('color_edge')
        color_face = PresetOverride.get('color_face')

        for elem in elements:
            if isinstance(elem, BMVert):
                cls.add_vert(matrix @ elem.co, color or color_vert, radius)
            elif isinstance(elem, BMEdge):
                cls.add_edge([(matrix @ v.co) for v in elem.verts], color or color_edge)
            elif isinstance(elem, BMFace):
                cls.add_face([(matrix @ v.co) for v in elem.verts], color or color_face)

    @classmethod
    def add_vert(cls, pos, color, radius):
        pos = tuple(pos)
        color = tuple(color)
        cls.display_verts.append({'pos': pos, 'color': color, 'radius': radius})

    @classmethod
    def add_edge(cls, verts, color):
        line_verts = []
        for i in range(len(verts)-1):
            line_verts.append(tuple(verts[i]))
            line_verts.append(tuple(verts[i+1]))
        color = tuple(color)
        cls.display_edges.append({'verts': line_verts, 'color': color})

    @classmethod
    def add_face(cls, verts, color):
        tri_verts = [tuple(verts[i]) for tri in tessellate_polygon([verts]) for i in tri]
        color = tuple(color)
        cls.display_faces.append({'verts': tri_verts, 'color': color})

    @classmethod
    def is_active_tool(cls, context):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        tool_idnames = ('nsolve.nflow_object_mode', 'nsolve.nflow_edit_mode')
        tool = context.workspace.tools.from_space_view3d_mode(context.mode)
        result = bool(tool) and (tool.idname in tool_idnames)
        result &= nflow_config_workspace.enable
        if not result:
            cls.display_region = None
            cls.display_mouse_pos = None
            cls.hover_text = ''
            cls.help_text = ''
            cls.cleanup()
        return result

    @classmethod
    def override_retopology_color(cls, context):
        if not NFlowPrefs.get('use_color_retopology'):
            return

        if cls.is_active_tool(context):
            color_retopology = PresetOverride.get('color_retopology')
        else:
            color_retopology = NFlowPrefs.get('color_retopology')

        def max_difference(a, b):
            return max(abs(v_a - v_b) for v_a, v_b in zip(a, b))

        themes = context.preferences.themes
        theme = themes.get("Default") or themes[0]

        # Blender stores colors as RGBA8, so we need some
        # tolerance to avoid triggering endless updates
        if max_difference(theme.view_3d.face_retopology, color_retopology) > 1/255:
            theme.view_3d.face_retopology = color_retopology

    @classmethod
    def store_color_retopology(cls, context):
        if context.scene.nsolve.ops.nflow.store_data:
            themes = context.preferences.themes
            theme = themes.get("Default") or themes[0]
            NFlowPrefs.set('default_color_retopology', theme.view_3d.face_retopology)
            context.scene.nsolve.ops.nflow.store_data = False

    @classmethod
    def restore_color_retopology(cls, context):
        if not context.scene.nsolve.ops.nflow.store_data:
            color_retopology = NFlowPrefs.get('default_color_retopology')
            themes = context.preferences.themes
            theme = themes.get("Default") or themes[0]
            theme.view_3d.face_retopology = color_retopology
            context.scene.nsolve.ops.nflow.store_data = True

    @classmethod
    def draw_2d(cls):
        context = bpy.context
        area = context.area
        region = context.region
        rv3d = context.region_data

        if cls.is_active_tool(context):
            cls.store_color_retopology(context)

        if not cls.is_active_tool(context):
            cls.restore_color_retopology(context)
            return

        if region != cls.display_region:
            return

        cls.override_retopology_color(context)

        nflow_config_workspace = context.workspace.nsolve.ops.nflow

        gpu.state.blend_set('ALPHA')

        cls.draw_display_elements_2d(context)

        cls.draw_display_curve(context)

        if NFlowPrefs.get('hover_text_enabled') and cls.hover_text:
            font_size = NFlowPrefs.get('hover_text_size')
            anchor = Vector(NFlowPrefs.get('hover_text_anchor'))
            cls.draw_text(cls.hover_text, font_size, cls.display_mouse_pos, anchor=anchor, alignment=0.5)

        if NFlowPrefs.get('help_text_enabled') and cls.help_text:
            font_size = NFlowPrefs.get('help_text_size')
            anchor = Vector(NFlowPrefs.get('help_text_anchor'))
            spacing = NFlowPrefs.get('help_text_spacing')
            rect = calc_region_rect(area, region, overlap=False)
            text_pos = rect[1] * anchor
            cls.draw_text(cls.help_text, font_size, text_pos, anchor=anchor, alignment=0.0, spacing=spacing)

    @classmethod
    def draw_display_elements_2d(cls, context):
        region = context.region
        rv3d = context.region_data

        if not cls.validate_display_data(context):
            return

        outline_width = NFlowPrefs.get('vert_outline_width')

        is_solid = (outline_width == 0)

        if is_solid:
            shader = gpu_shader_from_builtin('SMOOTH_COLOR')
        else:
            shader = gpu_shader_from_builtin('POLYLINE_SMOOTH_COLOR')

        points = []
        segments = 12
        for i in range(segments+1):
            angle = 2*math.pi * i / segments
            points.append(Vector((math.sin(angle), math.cos(angle))))

        coords = []
        colors = []
        for info in cls.display_verts:
            pos = location_3d_to_region_2d(region, rv3d, info['pos'])
            if pos is None:
                continue

            radius = info['radius']
            color = info['color']

            if is_solid:
                for i in range(len(points)-2):
                    coords.append(pos + points[0]*radius)
                    coords.append(pos + points[i+1]*radius)
                    coords.append(pos + points[i+2]*radius)
                    colors.append(color)
                    colors.append(color)
                    colors.append(color)
            else:
                for i in range(len(points)):
                    coords.append(pos + points[i-1]*radius)
                    coords.append(pos + points[i-0]*radius)
                    colors.append(color)
                    colors.append(color)

        if is_solid:
            batch = batch_for_shader(shader, 'TRIS', {'pos': coords, 'color': colors})
        else:
            batch = batch_for_shader(shader, 'LINES', {'pos': coords, 'color': colors})
            shader.uniform_float('viewportSize', (region.width, region.height))
            shader.uniform_float('lineWidth', outline_width)
        batch.draw(shader)

    @classmethod
    def draw_display_curve(cls, context):
        if not cls.display_curve:
            return

        region = context.region

        shader = gpu_shader_from_builtin('POLYLINE_UNIFORM_COLOR')

        color = (0.75,1,0,1)
        line_width = 3

        coords = []
        for i in range(len(cls.display_curve)-1):
            coords.append(cls.display_curve[i])
            coords.append(cls.display_curve[i+1])

        batch = batch_for_shader(shader, 'LINES', {'pos': coords})
        shader.uniform_float('color', color)
        shader.uniform_float('viewportSize', (region.width, region.height))
        shader.uniform_float('lineWidth', line_width)
        batch.draw(shader)

    @classmethod
    def draw_text(cls, text, font_size, pos, anchor, alignment=0.5, spacing=0):
        if (text is None) or (pos is None) or (anchor is None):
            return

        lines = text.split('\n')
        lines.reverse() # draw from top to bottom

        text_color = NFlowPrefs.get('text_color')
        background_color = NFlowPrefs.get('text_background')

        font = 0
        blf_size(font, font_size)

        line_height = blf.dimensions(font, 'Ig')[1]
        topline = blf.dimensions(font, 'I')[1]
        text_dy = line_height - topline

        sizes = [(blf.dimensions(font, line)[0], line_height) for line in lines]
        tw_total = max(size[0] for size in sizes)
        th_total = sum(size[1] for size in sizes) + spacing * (len(sizes) - 1)

        margin = 8
        w = tw_total + margin*2
        h = th_total + margin*2

        x0, y0 = pos[0] - anchor[0]*w, pos[1] - anchor[1]*h
        x1, y1 = x0+w, y0+h
        v00 = (x0, y0, 0)
        v10 = (x1, y0, 0)
        v01 = (x0, y1, 0)
        v11 = (x1, y1, 0)

        gpu.state.blend_set('ALPHA')
        shader = gpu_shader_from_builtin('UNIFORM_COLOR')
        coords = [v00, v01, v11, v00, v11, v10]
        batch = batch_for_shader(shader, 'TRIS', {'pos': coords})
        shader.uniform_float('color', background_color)
        batch.draw(shader)

        line_x = (x0+x1)*0.5 - tw_total*(0.5-alignment)
        line_y = (y0+y1)*0.5 - th_total*0.5 + text_dy*0.5
        for line, size in zip(lines, sizes):
            tw, th = size
            tx = line_x - tw*alignment
            ty = line_y
            line_y += line_height + spacing

            blf.color(font, *text_color)
            blf.position(font, tx, ty, 0)
            blf.draw(font, line)

    @classmethod
    def draw_3d(cls):
        context = bpy.context
        region = context.region
        rv3d = context.region_data

        active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        nflow_tool = True if active_tool and active_tool.idname == 'nsolve.nflow_edit_mode' else False
        if not nflow_tool:
            return

        if not cls.is_active_tool(context):
            return

        gpu.state.blend_set('ALPHA')

        cls.draw_display_elements_3d(context)

        cls.draw_vertex_overlay(context)

    @classmethod
    def draw_vertex_overlay(cls, context):
        if context.mode != 'EDIT_MESH':
            return

        # if context.tool_settings.mesh_select_mode[0]:
        #     return

        nflow_config_workspace = context.workspace.nsolve.ops.nflow

        if not nflow_config_workspace.show_vertex_overlay:
            return

        space_data = context.space_data
        region = context.region
        rv3d = context.region_data

        view_info = get_view_transform_info(context)
        is_perspective = view_info['is_perspective']
        get_scale_xy = view_info['get_scale_xy']
        origin = view_info['origin']
        axis_x = view_info['axis_x']
        axis_y = view_info['axis_y']
        axis_z = view_info['axis_z']

        scale = NFlowPrefs.get('vertex_overlay_radius')
        radius_x = axis_x * scale
        radius_y = axis_y * scale

        def to_color(c):
            return (tuple(c) if len(c) == 4 else (c[0], c[1], c[2], 1.0))

        if NFlowPrefs.get('vertex_overlay_use_custom_colors'):
            color_selected = NFlowPrefs.get('vertex_overlay_selected')
            color_regular = NFlowPrefs.get('vertex_overlay_unselected')
        else:
            themes = context.preferences.themes
            theme = themes.get("Default") or themes[0]
            color_selected = to_color(theme.view_3d.vertex_select)
            color_regular = to_color(theme.view_3d.vertex)

        coords_selected = []
        coords_regular = []

        # Judging by the "Projection Matrix Tricks" reference in
        # source/blender/draw/intern/shaders/common_view_lib.glsl
        # Blender essentially uses constant offset in world-space
        retopology_offset = getattr(space_data.overlay, 'retopology_offset', 0.0)

        bias_factor = NFlowPrefs.get('vertex_overlay_depth_bias')
        bias_factor += retopology_offset

        def add_verts(matrix, verts):
            for v in verts:
                if v.hide:
                    continue

                pos3d = Vector(matrix @ v.co)
                pos2d = location_3d_to_region_2d(region, rv3d, pos3d)
                if pos2d is None:
                    continue

                ray_dir = axis_z
                if is_perspective:
                    ray_dir = pos3d - region_2d_to_origin_3d(region, rv3d, pos2d)
                pos3d -= ray_dir.normalized() * bias_factor

                scale_x, scale_y = get_scale_xy(pos3d)
                half_x = radius_x * scale_x
                half_y = radius_y * scale_y

                coords = (coords_selected if v.select else coords_regular)

                v00 = pos3d - half_x - half_y
                v10 = pos3d + half_x - half_y
                v01 = pos3d - half_x + half_y
                v11 = pos3d + half_x + half_y
                coords.append(v00)
                coords.append(v01)
                coords.append(v11)
                coords.append(v00)
                coords.append(v11)
                coords.append(v10)

        for obj, mesh, bm in EditableMeshes.all():
            add_verts(obj.matrix_world, bm.verts)

        depth_test_prev = gpu.state.depth_test_get()
        depth_mask_prev = gpu.state.depth_mask_get()

        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.depth_mask_set(False)
        gpu.state.face_culling_set('NONE')

        gpu.state.blend_set('ALPHA')

        shader = gpu_shader_from_builtin('UNIFORM_COLOR')

        batch = batch_for_shader(shader, 'TRIS', {'pos': coords_regular})
        shader.uniform_float('color', color_regular)
        batch.draw(shader)

        batch = batch_for_shader(shader, 'TRIS', {'pos': coords_selected})
        shader.uniform_float('color', color_selected)
        batch.draw(shader)

        gpu.state.face_culling_set('BACK')
        gpu.state.depth_test_set(depth_test_prev)
        gpu.state.depth_mask_set(depth_mask_prev)

    @classmethod
    def draw_display_elements_3d(cls, context):
        region = context.region
        rv3d = context.region_data

        if not cls.validate_display_data(context):
            return

        is_perspective, near, far = get_view_frustum_info(context)
        view_dir = region_2d_to_vector_3d(region, rv3d, (region.width*0.5, region.height*0.5))

        depth_test_prev = gpu.state.depth_test_get()
        depth_mask_prev = gpu.state.depth_mask_get()

        line_width = NFlowPrefs.get('edge_radius_base')
        gpu.state.depth_mask_set(False)

        gpu.state.face_culling_set('NONE')

        def bias_depth(verts, factor=1e-3):
            biased_verts = []
            for v in verts:
                v = Vector(v)
                ray_dir = view_dir
                if is_perspective:
                    p = location_3d_to_region_2d(region, rv3d, v)
                    if p is not None:
                        p = region_2d_to_origin_3d(region, rv3d, p)
                        ray_dir = v - p
                v -= ray_dir * factor
                biased_verts.append(v)
            return biased_verts

        occluded_alpha = NFlowPrefs.get('occluded_alpha')

        if occluded_alpha < 1:
            passes = (('LESS_EQUAL', 1), ('GREATER', occluded_alpha))
        else:
            passes = (('ALWAYS', 1),)

        for depth_test, alpha in passes:
            def apply_alpha(color):
                return (color[0], color[1], color[2], color[3]*alpha)

            gpu.state.depth_test_set(depth_test)

            shader = gpu_shader_from_builtin('SMOOTH_COLOR')

            coords = []
            colors = []
            for info in cls.display_faces:
                coords.extend(bias_depth(info['verts']))
                colors.extend([apply_alpha(info['color'])] * len(info['verts']))

            batch = batch_for_shader(shader, 'TRIS', {'pos': coords, 'color': colors})
            batch.draw(shader)

            shader = gpu_shader_from_builtin('POLYLINE_SMOOTH_COLOR')

            coords = []
            colors = []
            for info in cls.display_edges:
                coords.extend(bias_depth(info['verts']))
                colors.extend([apply_alpha(info['color'])] * len(info['verts']))

            batch = batch_for_shader(shader, 'LINES', {'pos': coords, 'color': colors})
            shader.uniform_float('viewportSize', (region.width, region.height))
            shader.uniform_float('lineWidth', line_width)
            batch.draw(shader)

        gpu.state.face_culling_set('BACK')

        gpu.state.depth_test_set(depth_test_prev)
        gpu.state.depth_mask_set(depth_mask_prev)

    @classmethod
    def on_load(cls, scene):
        cls.cleanup()


class NFlowBehavior:
    undo_message = None

    capabilities = set()

    status_text = ''
    hover_text = ''

    overridden_options = None

    use_post_select_elements = False
    post_select_mode = 'OVERRIDE'
    selection_helper = None

    obj = None
    mesh = None
    bm = None
    elem_type = None
    elements = None

    region = None
    rv3d = None
    is_perspective = None
    near = None
    far = None
    view_center = None
    view_origin = None
    view_direction = None
    raycaster = None

    invoke_mouse_pos = None
    invoke_event_type = None
    cancel_event_types = None
    elem_type_start = None

    snap_time_last = -math.inf
    use_snap = False
    snap_options = None
    snap_options_mirror = None
    snap_verts = None
    snap_kdtree = None

    @classmethod
    def validate_elements(cls, elements):
        return True

    def initialize(self, context, event, **kwargs):
        if self.invoke_event_type is None:
            self.invoke_event_type = event.type
            self.cancel_event_types = get_cancel_event_types(event)

        if self.invoke_mouse_pos is None:
            self.invoke_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        editors = kwargs.get('editors')
        overridden_options = kwargs.get('overridden_options')

        self.view_info = kwargs.get('view_info') or get_view_transform_info(context)
        self.raycaster = kwargs.get('raycaster') or Raycaster(context)
        self.editors = (MeshEditors() if editors is None else editors)
        self.overridden_options = (set() if overridden_options is None else overridden_options)

        nflow_config_workspace = context.workspace.nsolve.ops.nflow

        self.snap_options_mirror = set()
        if nflow_config_workspace.use_mirror_clipping:
            self.snap_options_mirror.add('MIRROR')

        self.snap_options = set()
        if 'VERTS' in nflow_config_workspace.snap_to:
            self.snap_options.add('RAY_VERTS')
        if 'EDGES' in nflow_config_workspace.snap_to:
            self.snap_options.add('RAY_EDGES')
        if 'FACES' in nflow_config_workspace.snap_to:
            self.snap_options.add('RAY_FACES')
        if 'EDGES_MID' in nflow_config_workspace.snap_to:
            self.snap_options.add('RAY_EDGES_MID')
        if 'FACES_MID' in nflow_config_workspace.snap_to:
            self.snap_options.add('RAY_FACES_MID')

        # Note: we can't enable mirror snapping by default,
        # mecause it requires knowing the starting positions

        self.init(context, event)

    def set_target(self, obj, bm, elem_type, elements):
        if self.elem_type_start is None:
            self.elem_type_start = elem_type

        self.obj = obj
        self.mesh = (obj.data if obj else None)
        self.bm = bm
        self.elem_type = elem_type
        self.elements = elements

    def init(self, context, event):
        pass

    def hover(self, context, event):
        pass

    def invoke(self, context, event):
        pass

    def modal(self, context, event):
        pass

    def cleanup(self, context):
        pass

    def make_behavior(self, behavior_class, context, event, elements, prototype=None):
        behavior = behavior_class()
        behavior.initialize(context, event, view_info=self.view_info,
            raycaster=self.raycaster, editors=self.editors,
            overridden_options=self.overridden_options)
        behavior.set_target(self.obj, self.bm, self.elem_type, elements)

        if prototype:
            behavior.invoke_event_type = prototype.invoke_event_type
            behavior.invoke_mouse_pos = prototype.invoke_mouse_pos

        if behavior.invoke(context, event) == 'CANCELLED':
            return None

        return behavior

    @property
    def editor(self):
        if len(self.editors) > 0:
            return self.editors[0]

        editor = self.editors.from_context(new_name='nFlow')

        if editor and editor.is_new:
            bpy.ops.wm.tool_set_by_id(name='nsolve.nflow_edit_mode', space_type='VIEW_3D')

        return editor

    def gather_snap_verts(self, exclude=()):
        kdtree = None
        verts = []

        for obj, mesh, bm in EditableMeshes.all():
            matrix = obj.matrix_world
            for v in bm.verts:
                if (not v.hide) and (v not in exclude):
                    verts.append((bm, v, matrix @ v.co))

        # Note: Blender will crash if we try to use an empty kdtree
        if verts:
            kdtree = KDTree(len(verts))
            for i, (bm, v, p) in enumerate(verts):
                kdtree.insert(p, i)
            kdtree.balance()

        self.snap_verts = verts
        self.snap_kdtree = kdtree


class MeshEditState:
    def __init__(self, editor):
        self.editor = editor
        self.removed = {}
        self.added = {}
        self.moved = {}
        self.flipped = {}
        self.tweaked = {}

    def remove(self, elements):
        for elem in MeshUtil.to_sequence(elements):
            if (elem is not None) and elem.is_valid:
                self.removed.setdefault(elem, elem.hide)
                elem.hide = True

    def add(self, elements):
        for elem in MeshUtil.to_sequence(elements):
            if (elem is not None) and elem.is_valid:
                self.added.setdefault(elem, None)

    def move(self, elements, values=None):
        faces = set()
        for elem, value in MeshUtil.to_items(elements, values):
            if isinstance(elem, BMVert) and elem.is_valid:
                if elem not in self.moved:
                    self.moved[elem] = (tuple(elem.co), tuple(elem.normal))

                if value is not None:
                    elem.co = value
                    faces.update(elem.link_faces)

        for f in faces:
            f.normal_update()

    def flip(self, elements):
        for elem in MeshUtil.to_sequence(elements):
            if isinstance(elem, BMFace) and elem.is_valid:
                if elem in self.flipped:
                    self.flipped.pop(elem, None)
                else:
                    self.flipped.setdefault(elem, None)

                elem.normal_flip()
                elem.normal_update()

    def tweak(self, attr_name, elements, values=None):
        attr_tweaked = self.tweaked.setdefault(attr_name, {})

        for elem, value in MeshUtil.to_items(elements, values):
            if (elem is not None) and elem.is_valid and hasattr(elem, attr_name):
                if elem not in attr_tweaked:
                    attr_tweaked[elem] = getattr(elem, attr_name)

                setattr(elem, attr_name, value)

    def record(self, attr_name, elements):
        if attr_name == 'co':
            for elem in MeshUtil.to_sequence(elements):
                if isinstance(elem, BMVert) and elem.is_valid:
                    if elem not in self.moved:
                        self.moved[elem] = (tuple(elem.co), tuple(elem.normal))
        else:
            attr_tweaked = self.tweaked.setdefault(attr_name, {})

            for elem in MeshUtil.to_sequence(elements):
                if (elem is not None) and elem.is_valid and hasattr(elem, attr_name):
                    if elem not in attr_tweaked:
                        attr_tweaked[elem] = getattr(elem, attr_name)

    def revert(self):
        for attr_name, attr_tweaked in self.tweaked.items():
            for elem, value in attr_tweaked.items():
                if elem.is_valid:
                    setattr(elem, attr_name, value)
        self.tweaked.clear()

        for elem in self.flipped.keys():
            if elem.is_valid:
                elem.normal_flip()
                elem.normal_update()
        self.flipped.clear()

        for elem, (pos, normal) in self.moved.items():
            if elem.is_valid:
                elem.co = pos
        for elem in self.moved.keys():
            if elem.is_valid:
                elem.normal_update()
        self.moved.clear()

        for elem, value in self.removed.items():
            if elem.is_valid:
                elem.hide = value
        self.removed.clear()

        MeshUtil.delete_elements(self.editor.bm, self.added.keys(), sanitize='EXCLUDE')
        self.added.clear()

    def apply(self):
        MeshUtil.delete_elements(self.editor.bm, self.removed.keys(), sanitize='EXCLUDE')
        self.removed.clear()

    def duplicate(self, elements, replace=()):
        if not isinstance(elements, list):
            elements = list(elements) # mesh duplication needs a list anyway

        result = MeshUtil.duplicate_elements(self.editor.bm, elements)
        copy_geom = result['geom']
        vert_map = result['vert_map']
        edge_map = result['edge_map']
        face_map = result['face_map']

        if replace == 'ALL':
            self.remove(elements)
        elif replace:
            if 'VERTS' in replace:
                self.remove(elem for elem in elements if isinstance(elem, BMVert))
            if 'EDGES' in replace:
                self.remove(elem for elem in elements if isinstance(elem, BMEdge))
            if 'FACES' in replace:
                self.remove(elem for elem in elements if isinstance(elem, BMFace))

        self.add(copy_geom)

        dummy_get = (lambda k: None)
        type_map = {BMVert: vert_map.get, BMEdge: edge_map.get, BMFace: face_map.get}.get

        def remap_many(items):
            # Apparently, not all source elements might be copied in some cases
            if hasattr(items, 'items'):
                for k, v in items.items():
                    elem_map = type_map(k.__class__, dummy_get)
                    k = elem_map(k)
                    if k is not None:
                        yield k, v
            else:
                for k in items:
                    elem_map = type_map(k.__class__, dummy_get)
                    k = elem_map(k)
                    if k is not None:
                        yield k

        def remap(items):
            if isinstance(items, BMElements):
                return type_map(items.__class__, dummy_get)(items)
            return remap_many(items)

        return copy_geom, remap


class MeshEditor:
    def __init__(self, obj, mesh=None, bm=None):
        if (not isinstance(obj, bpy.types.Object)) or (obj.type != 'MESH'):
            raise TypeError('obj must be a mesh Object')

        # Note: it doesn't really make sense to support
        # mesh-editing operations in Object mode, since
        # there may not be a 1:1 match due to modifiers
        if obj.mode != 'EDIT':
            raise ValueError('obj must be in Edit mode')

        if mesh is None:
            mesh = obj.data
        elif not isinstance(mesh, bpy.types.Mesh):
            raise TypeError('mesh must be None or a Mesh')

        if bm is None:
            bm = EditableMeshes.get_bm(obj)
        elif not isinstance(bm, BMesh):
            raise TypeError('bm must be None or a BMesh')

        self.obj = obj
        self.mesh = mesh
        self.bm = bm
        self.edits = []
        self.is_new = False
        self.cleanups = []
        self.update_matrices()
        self.push_state()

    @classmethod
    def from_context(cls, context=None, new_name=None):
        if context is None:
            context = bpy.context

        if context.mode == 'EDIT_MESH':
            return cls(context.object)

        if (context.mode != 'OBJECT') or (not new_name):
            return None

        original_object_selection = store_object_selection()

        mesh = bpy.data.meshes.new(new_name)
        obj = bpy.data.objects.new(new_name, mesh)
        context.collection.objects.link(obj)
        obj.matrix_world = context.scene.cursor.matrix

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

        def cleanup():
            bpy.data.objects.remove(obj)
            bpy.data.meshes.remove(mesh)
            restore_object_selection(original_object_selection)

        self = cls(obj)
        self.is_new = True
        self.cleanups.append(cleanup)

        return self

    def update_matrices(self):
        self.world_matrix_p = self.obj.matrix_world
        self.world_matrix_v = self.world_matrix_p.to_3x3()
        self.local_matrix_p = self.world_matrix_p.inverted_safe()
        self.local_matrix_v = self.local_matrix_p.to_3x3()

    def update_mesh(self):
        bmesh.update_edit_mesh(self.mesh)

    def push_state(self):
        self.edits.append(MeshEditState(self))

    def pop_state(self):
        if self.edits:
            edit = self.edits.pop()
            edit.revert()

    def revert(self):
        if (self.edits is None) or (self.cleanups is None):
            return # already reverted

        for edit in reversed(self.edits):
            edit.revert()
        self.edits = None

        # This is needed for correctness
        self.bm.normal_update()

        self.update_mesh()

        for cleanup in reversed(self.cleanups):
            cleanup()
        self.cleanups = None

    def apply(self):
        for edit in self.edits:
            edit.apply()
        self.edits = None
        self.update_mesh()

    def revert_last(self):
        self.edits[-1].revert()

    def _iter_elements(self, which, all_edits):
        if all_edits:
            for edit in self.edits:
                yield from getattr(edit, which)
        else:
            yield from getattr(self.edits[-1], which)

    def get_elements(self, which, mode='RAW'):
        # RAW: return what's stored in the last edit
        # LAST: like RAW, but discard the removed elements
        # ALL: accumulate across all edits, discard the removed elements
        # ORIGINAL: like ALL, but also discard the new elements

        all_edits = (mode == 'ALL') or (mode == 'ORIGINAL')

        if which == 'ADDED':
            if mode == 'ORIGINAL':
                return set()

            result = set(self._iter_elements('added', all_edits))

            if mode != 'RAW':
                result.difference_update(self._iter_elements('removed', all_edits))
        elif which == 'REMOVED':
            result = set(self._iter_elements('removed', all_edits))

            if mode == 'ORIGINAL':
                result.difference_update(self._iter_elements('added', all_edits))
        else:
            if which == 'MOVED':
                result = set(self._iter_elements('moved', all_edits))
            elif which == 'FLIPPED':
                result = set(self._iter_elements('flipped', all_edits))
            elif which == 'TWEAKED':
                result = set(self._iter_elements('tweaked', all_edits))
            elif which == 'CHANGED':
                result = set(self._iter_elements('moved', all_edits))
                result.update(self._iter_elements('flipped', all_edits))
                result.update(self._iter_elements('tweaked', all_edits))
            else:
                raise ValueError(f'Unrecognized \'which\' argument: {which}')

            if mode != 'RAW':
                result.difference_update(self._iter_elements('removed', all_edits))

            if mode == 'ORIGINAL':
                result.difference_update(self._iter_elements('added', all_edits))

        return result

    def __getattr__(self, name):
        return getattr(self.edits[-1], name)

    def add_vert(self, co, example=None, select=None):
        if example is None:
            v = self.bm.verts.new(co)
        else:
            v = self.bm.verts.new(co, example)

            # Needs to be done like this, rather than ... = select or ... |= select
            if example.select and (select is not False):
                v.select = True

        self.add(v)

        return v

    def add_edge(self, verts, example=None, select=None, existing=True):
        e = self.bm.edges.get(verts)
        if e is not None:
            return (e if existing else None)

        if example is None:
            e = self.bm.edges.new(verts)
        else:
            e = self.bm.edges.new(verts, example)

            # Needs to be done like this, rather than ... = select or ... |= select
            if example.select and (select is not False):
                e.select = True

        self.add(e)

        return e

    def add_face(self, verts, example=None, select=None, existing=True):
        f = self.bm.faces.get(verts)
        if f is not None:
            return (f if existing else None)

        if not isinstance(verts, (tuple, list)):
            verts = tuple(verts)
        old_edges = {self.bm.edges.get((verts[i-1], verts[i])) for i in range(len(verts))}

        if example is None:
            f = self.bm.faces.new(verts)
        else:
            f = self.bm.faces.new(verts, example)

            # Needs to be done like this, rather than ... = select or ... |= select
            if example.select and (select is not False):
                f.select = True

        f.normal_update()

        self.add(f)
        self.add(e for e in f.edges if e not in old_edges)

        return f


class MeshEditors:
    type_attr_map = {bpy.types.Object: 'obj', bpy.types.Mesh: 'mesh', BMesh: 'bm'}

    def __init__(self):
        self.all = []

    def __len__(self):
        return len(self.all)

    def __iter__(self):
        return iter(self.all)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.all[key]
        return self.get(key)

    def get(self, key):
        attr_name = self.type_attr_map.get(type(key))
        if not attr_name:
            return None

        for editor in self.all:
            if getattr(editor, attr_name) == key:
                return editor

        for item in EditableMeshes.all():
            if getattr(item, attr_name) == key:
                editor = MeshEditor(item.obj, item.mesh, item.bm)
                self.all.append(editor)
                return editor

        return None

    def from_context(self, context=None, new_name=None):
        if context is None:
            context = bpy.context

        editor = self.get(context.object)

        if not editor:
            editor = MeshEditor.from_context(context, new_name=new_name)
            if editor:
                self.all.append(editor)

        return editor

    def update_matrices(self):
        for editor in self.all:
            editor.update_matrices()

    def update_meshes(self):
        for editor in self.all:
            editor.update_mesh()

    def revert_last(self):
        for editor in self.all:
            editor.revert_last()

    def revert(self):
        for editor in self.all:
            editor.revert()

    def apply(self):
        for editor in self.all:
            editor.apply()

    def get_elements(self, which, mode='RAW', sanitize=None):
        bm_elements = {}
        for editor in self.all:
            elements = editor.get_elements(which, mode)
            if sanitize:
                verts, edges, faces = MeshUtil.sanitize_elements(elements, sanitize)
                elements = verts
                elements.update(edges)
                elements.update(faces)
            bm_elements[editor.bm] = elements
        return bm_elements


class MeshUtil:
    @classmethod
    def to_sequence(cls, elements):
        if isinstance(elements, BMElements):
            yield elements
        else:
            yield from elements

    @classmethod
    def to_items(cls, elements, values):
        if isinstance(elements, BMElements):
            yield (elements, values)
        elif values is not None:
            if callable(values):
                for elem in elements:
                    yield elem, values(elem)
            else:
                yield from zip(elements, values)
        else:
            yield from (elements.items() if hasattr(elements, 'items') else elements)

    @classmethod
    def gather_verts(cls, elements):
        verts = set()
        for elem in elements:
            if isinstance(elem, BMVert):
                verts.add(elem)
            elif isinstance(elem, (BMEdge, BMFace)):
                verts.update(elem.verts)
        return verts

    @classmethod
    def gather_edges(cls, elements):
        edges = set()
        for elem in elements:
            if isinstance(elem, BMEdge):
                edges.add(elem)
            elif isinstance(elem, BMFace):
                edges.update(elem.edges)
        return edges

    @classmethod
    def deselect_all(cls, bm):
        # Sometimes, bpy.ops.mesh.select_all does not work (e.g. if some elements were deleted)
        bm.select_history.clear()
        for v in bm.verts:
            v.select_set(False)
        bm.select_flush(False)

    @classmethod
    def select_elements(cls, bm_elements, mode, sanitize=None):
        if mode == 'KEEP':
            return

        def is_currently_selected():
            return all(elem.select for elements in bm_elements.values() for elem in elements)

        select_value = True

        if mode == 'ADD':
            deselect = False
        elif mode == 'SEMI_OVERRIDE':
            deselect = not is_currently_selected()
        elif mode == 'TOGGLE':
            select_value = not is_currently_selected()
            deselect = False
        elif mode == 'REMOVE':
            select_value = False
            deselect = False
        else:
            deselect = True

        for bm, elements in bm_elements.items():
            if deselect:
                cls.deselect_all(bm)

            if sanitize:
                elements = itertools.chain(*cls.sanitize_elements(elements, sanitize))

            select_history_add = bm.select_history.add
            for elem in elements:
                elem.select = select_value
                select_history_add(elem)

    @classmethod
    def sort_loop_edges(cls, edges):
        edges = set(edges)
        edges_sorted = []
        if not edges:
            return edges_sorted

        def add(e, append):
            if append:
                edges_sorted.append(e)
            else:
                edges_sorted.insert(0, e)
            edges.discard(e)

        def next_edge(e, v, append):
            for e2 in v.link_edges:
                if e2 in edges:
                    add(e2, append)
                    return e2, e2.other_vert(v)
            return None, None

        e0 = next(iter(edges))
        add(e0, True)

        e, v = e0, e0.verts[1]
        while e:
            e, v = next_edge(e, v, True)

        e, v = e0, e0.verts[0]
        while e:
            e, v = next_edge(e, v, False)

        return edges_sorted

    @classmethod
    def sanitize_elements(cls, elements, include_mode):
        verts = set()
        edges = set()
        faces = set()

        for elem in elements:
            if (elem is None) or (not elem.is_valid):
                continue
            if isinstance(elem, BMVert):
                verts.add(elem)
            elif isinstance(elem, BMEdge):
                edges.add(elem)
            elif isinstance(elem, BMFace):
                faces.add(elem)

        if include_mode == 'SHARED':
            edges.update(e for f in faces for e in f.edges
                if (e not in edges) and all((f2 in faces) for f2 in e.link_faces))
            verts.update(v for e in edges for v in e.verts
                if (v not in verts) and all((e2 in edges) for e2 in v.link_edges))
        elif include_mode == 'INCLUDE':
            edges.update(e for f in faces for e in f.edges)
            verts.update(v for e in edges for v in e.verts)
        elif include_mode == 'EXCLUDE':
            for v in verts:
                for e in v.link_edges:
                    edges.discard(e)
                for f in v.link_faces:
                    faces.discard(f)

            for e in edges:
                for f in e.link_faces:
                    faces.discard(f)

        return verts, edges, faces

    @classmethod
    def delete_elements(cls, bm, elements, sanitize='SHARED'):
        verts, edges, faces = cls.sanitize_elements(elements, sanitize)

        # Remove elements explicitly to avoid Blender's idiosyncrasies

        for f in faces:
            bm.faces.remove(f)

        for e in edges:
            bm.edges.remove(e)

        for v in verts:
            bm.verts.remove(v)

    @classmethod
    def dissolve_elements(cls, bm, elements):
        verts, edges, faces = cls.sanitize_elements(elements, 'EXCLUDE')

        if verts:
            bmesh.ops.dissolve_verts(bm, verts=list(verts))

        if edges:
            bmesh.ops.dissolve_edges(bm, edges=list(edges))

        if faces:
            bmesh.ops.dissolve_faces(bm, faces=list(faces))

    @classmethod
    def collapse_elements(cls, bm, elements, merge_point):
        verts, edges, faces = cls.sanitize_elements(elements, 'INCLUDE')

        if len(verts) <= 1:
            return

        if merge_point is None:
            bbox_min = Vector((math.inf, math.inf, math.inf))
            bbox_max = Vector((-math.inf, -math.inf, -math.inf))
            for v in verts:
                p = v.co
                bbox_min.x = min(bbox_min.x, p.x)
                bbox_min.y = min(bbox_min.y, p.y)
                bbox_min.z = min(bbox_min.z, p.z)
                bbox_max.x = max(bbox_max.x, p.x)
                bbox_max.y = max(bbox_max.y, p.y)
                bbox_max.z = max(bbox_max.z, p.z)

            merge_point = (bbox_min + bbox_max) * 0.5

        verts = list(verts)
        bmesh.ops.pointmerge(bm, verts=verts, merge_co=merge_point)
        return verts[0]

    @classmethod
    def merge_nearby_verts(cls, bm, verts, distance=None, connected_only=False):
        if distance is None:
            distance = NFlowPrefs.get('merge_radius')

        if not connected_only:
            result = bmesh.ops.find_doubles(bm, verts=bm.verts, keep_verts=verts, dist=distance)
            bmesh.ops.weld_verts(bm, targetmap=result['targetmap'])

        edges = {e for v in verts for e in v.link_edges}
        verts = {v for e in edges for v in e.verts}
        bmesh.ops.remove_doubles(bm, verts=list(verts), dist=distance)

    @classmethod
    def duplicate_elements(cls, bm, elements):
        if not isinstance(elements, list):
            elements = list(elements)

        result = bmesh.ops.duplicate(bm, geom=elements)

        copy_geom = result['geom']
        vert_map = result['vert_map']
        edge_map = result['edge_map']
        face_map = result['face_map']

        for elem_dst in copy_geom:
            if isinstance(elem_dst, BMVert):
                elem_src = vert_map[elem_dst]
            elif isinstance(elem_dst, BMEdge):
                elem_src = edge_map[elem_dst]
            elif isinstance(elem_dst, BMFace):
                elem_src = face_map[elem_dst]

            # Needs to be done like this, rather than ... = select or ... |= select
            if elem_src.select:
                elem_dst.select = True

        return result

    @classmethod
    def find_misaligned_faces(cls, elements, direction=None, update_normals='ALL', fallback=None):
        for elem in elements:
            if (not isinstance(elem, BMFace)) or (not elem.is_valid):
                continue

            if cls.is_face_misaligned(elem, direction, update_normals, fallback):
                yield elem

    @classmethod
    def is_face_misaligned(cls, face, direction=None, update_normals='ALL', fallback=None):
        update_normals_all = (update_normals == 'ALL')
        update_normals_self = (update_normals != 'NONE')

        if direction is None:
            agreement_score = 0
            for l in face.loops:
                for l2 in l.link_loops:
                    agreement_score += (1 if l2.vert != l.vert else -1)

            if agreement_score != 0:
                return (agreement_score < 0)

            direction = Vector()
            for v in face.verts:
                for f in v.link_faces:
                    if f != face:
                        if update_normals_all:
                            f.normal_update()
                        direction += f.normal

            if (direction.length_squared == 0) and (fallback is not None):
                direction = fallback

        if update_normals_self:
            face.normal_update()

        if not isinstance(direction, Vector):
            direction = Vector(direction)

        return (direction.dot(face.normal) < 0)

    @classmethod
    def snap(cls, points, options, output=None, **kwargs):
        if output is None:
            points = list(points)
        elif output is not points:
            output[:] = points
            points = output

        if 'SURFACE' in options:
            raycaster = kwargs.get('raycaster')
            directions = kwargs.get('directions')
            raycaster.snap_points_to_surface(Matrix(), points, directions, output=points)

        ray_modes = (
            'RAY_VERTS',
            'RAY_EDGES',
            'RAY_FACES',
            'RAY_EDGES_MID',
            'RAY_FACES_MID',
        )
        if not options.isdisjoint(ray_modes):
            raycaster = kwargs.get('raycaster')
            depth_refs = kwargs.get('depth_refs')
            radius = kwargs.get('radius_scene')
            context = kwargs.get('context')
            cls._snap_raycast_elements(points, depth_refs, raycaster, options, radius, context=context)

        if 'EDIT_VERTS' in options:
            context = kwargs.get('context')
            radius = kwargs.get('radius_edit')
            kdtree = kwargs.get('kdtree')
            raycaster = kwargs.get('raycaster')
            hide_elements = kwargs.get('hide_elements')
            if (len(points) == 1) and (hide_elements is not None):
                cls._snap_select(points, radius, raycaster, hide_elements, context=context)
            elif kdtree:
                cls._snap_kdtree(points, kdtree, radius, context=context)

        if 'MIRROR' in options:
            obj = kwargs.get('obj')
            original_points = kwargs.get('original_points')
            clamp_bisected = kwargs.get('clamp_bisected', False)
            cls._snap_mirror(points, original_points, obj, clamp_bisected)

        return points

    @classmethod
    def _snap_kdtree(cls, points, kdtree, radius, context=None):
        if kdtree is None:
            return

        if context is None:
            context = bpy.context

        view_info = get_view_transform_info(context)
        get_scale = view_info['get_scale']

        for i, p in enumerate(points):
            p_target, index, dist = kdtree.find(p)
            if (radius is None) or (dist <= (get_scale(p) * radius)):
                points[i] = p_target

    @classmethod
    def _snap_select(cls, points, radius, raycaster, hide_elements, context=None):
        # WARNING: this does not work well for more than one point
        # (if there are more, Blender starts to sporadically stop detecting elements)

        if context is None:
            context = bpy.context

        bm_infos = []
        for obj, mesh, bm in EditableMeshes.all():
            bm_infos.append((bm, mesh, obj.matrix_world, MeshSelectionState(bm)))

        hide_elements = cls.gather_verts(hide_elements)

        hidden = []
        for elem in hide_elements:
            hidden.append((elem, elem.hide))
            elem.hide = True

        for bm, mesh, matrix, selection_state in bm_infos:
            bmesh.update_edit_mesh(mesh)

        active_obj = context.view_layer.objects.active

        prev_select_mode = tuple(context.tool_settings.mesh_select_mode)

        context.tool_settings.mesh_select_mode = (True, False, False)

        def cast(pos2d):
            for bm, mesh, matrix, selection_state in bm_infos:
                bm.select_history.clear()

            location=(int(pos2d[0]), int(pos2d[1]))
            bpy.ops.view3d.select('EXEC_DEFAULT', location=location)

            for bm, mesh, matrix, selection_state in bm_infos:
                v = bm.select_history.active
                if isinstance(v, BMVert):
                    return matrix @ v.co

        for i, pos3d in enumerate(points):
            pos2d = raycaster.project(pos3d)
            if pos2d is None:
                continue

            snap_pos = cast(pos2d)
            if snap_pos is None:
                continue

            snap_pos2d = raycaster.project(snap_pos)
            dist = (math.inf if snap_pos2d is None else (snap_pos2d - pos2d).magnitude)

            if (radius is None) or (dist <= radius):
                points[i] = snap_pos

        for elem, hide in hidden:
            elem.hide = hide

        for bm, mesh, matrix, selection_state in bm_infos:
            selection_state.restore()
            bmesh.update_edit_mesh(mesh)

        if context.view_layer.objects.active != active_obj:
            context.view_layer.objects.active = active_obj

        context.tool_settings.mesh_select_mode = prev_select_mode

    @classmethod
    def _snap_mirror(cls, points, original_points, obj, clamp_bisected=False, epsilon=1e-6):
        if (obj is None) or (original_points is None):
            return

        for md in obj.modifiers:
            if (md.type != 'MIRROR') or (not md.show_viewport) or (not md.use_clip):
                continue

            use_axis = tuple(md.use_axis)

            if not any(use_axis):
                continue

            bisect_axis = tuple(md.use_bisect_axis)
            flip_axis = tuple(md.use_bisect_flip_axis)

            mirror_obj = md.mirror_object or obj
            matrix = mirror_obj.matrix_world
            matrix_inv = matrix.inverted_safe()

            for i in range(len(points)):
                p, p0 = points[i], original_points[i]
                if p0 is None:
                    continue

                p0 = matrix_inv @ p0
                p = matrix_inv @ p

                for axis, use in enumerate(use_axis):
                    if not use:
                        continue

                    if bisect_axis[axis]:
                        if abs(p0[axis]) <= epsilon:
                            p[axis] = 0
                        elif (p0[axis] < 0) != flip_axis[axis]:
                            p[axis] = (0 if clamp_bisected else p0[axis])
                        elif (p[axis] < 0) != flip_axis[axis]:
                            p[axis] = 0
                    elif p0[axis]*p[axis] <= epsilon:
                        p[axis] = 0

                points[i] = matrix @ p

    @classmethod
    def _snap_raycast_elements(cls, points, depth_refs, raycaster, options, radius, context=None):
        to_verts = ('RAY_VERTS' in options)
        to_edges = ('RAY_EDGES' in options)
        to_faces = ('RAY_FACES' in options)
        to_edges_mid = ('RAY_EDGES_MID' in options)
        to_faces_mid = ('RAY_FACES_MID' in options)

        if context is None:
            context = bpy.context

        depsgraph = context.view_layer.depsgraph

        obj_candidates = {}
        eval_objs = {}

        def get_snap_points(raycast_obj, raycast_face, pos3d):
            poly_candidates = obj_candidates.get(raycast_obj)
            if poly_candidates is None:
                poly_candidates = {}
                obj_candidates[raycast_obj] = poly_candidates

            if raycast_obj not in eval_objs:
                if raycast_obj.is_evaluated:
                    eval_obj = raycast_obj
                else:
                    eval_obj = raycast_obj.evaluated_get(depsgraph)
                eval_mesh = eval_obj.to_mesh(preserve_all_data_layers=False)
                eval_objs[raycast_obj] = (eval_obj, eval_obj.matrix_world, eval_mesh)

            snap_points = poly_candidates.get(raycast_face)
            if snap_points is None:
                eval_obj, matrix, eval_mesh = eval_objs[raycast_obj]
                snap_points = list(cls.polygon_snap_points(matrix, eval_mesh, raycast_face,
                    to_verts, to_edges_mid, to_faces_mid))
                poly_candidates[raycast_face] = snap_points

            if to_edges:
                eval_obj, matrix, eval_mesh = eval_objs[raycast_obj]
                yield from cls.polygon_snap_points_edges(matrix, eval_mesh, raycast_face, pos3d)

            yield from snap_points

        with raycaster.batch():
            for i, pos3d in enumerate(points):
                pos2d = raycaster.project(pos3d)
                if pos2d is None:
                    continue

                origin, direction = raycaster.ray(pos2d)
                result = raycaster.query(origin, direction)

                if not result[0]:
                    if depth_refs:
                        points[i] = raycaster.unproject(pos2d, depth_refs[i])
                    continue

                if to_faces:
                    points[i] = result[1]
                    continue

                use_radius = (radius is not None) and (radius < math.inf)
                best_dist = math.inf

                for snap_pos in get_snap_points(result[4], result[3], pos3d):
                    if use_radius:
                        snap_pos_2d = raycaster.project(snap_pos)
                        if snap_pos_2d is None:
                            continue

                        dist_2d = (snap_pos_2d - pos2d).magnitude
                        if dist_2d > radius:
                            continue

                    dist = (snap_pos - pos3d).length_squared
                    if dist < best_dist:
                        best_dist = dist
                        points[i] = snap_pos

        for eval_obj, matrix, eval_mesh in eval_objs.values():
            eval_obj.to_mesh_clear()

    @classmethod
    def polygon_snap_points(cls, matrix, mesh, face_index, to_verts, to_edges_mid, to_faces_mid):
        if (face_index < 0) or (face_index >= len(mesh.polygons)):
            return

        polygon = mesh.polygons[face_index]

        if to_faces_mid:
            yield matrix @ polygon.center

        if not (to_verts or to_edges_mid):
            return

        p_first = None
        p_last = None

        for vi in polygon.vertices:
            p = matrix @ mesh.vertices[vi].co

            if to_verts:
                yield p

            if to_edges_mid and (p_last is not None):
                yield (p + p_last) * 0.5

            p_last = p
            if p_first is None:
                p_first = p

        if to_edges_mid and (p_last is not None):
            yield (p_first + p_last) * 0.5

    @classmethod
    def polygon_snap_points_edges(cls, matrix, mesh, face_index, pos3d):
        if (face_index < 0) or (face_index >= len(mesh.polygons)):
            return

        polygon = mesh.polygons[face_index]

        p_first = None
        p_last = None

        for vi in polygon.vertices:
            p = matrix @ mesh.vertices[vi].co

            if p_last is not None:
                yield closest_point_on_line(pos3d, p, p_last)

            p_last = p
            if p_first is None:
                p_first = p

        if p_last is not None:
            yield closest_point_on_line(pos3d, p_first, p_last)

    @classmethod
    def create_polyline(cls, bm, points, mode='OPEN'):
        new_elements = []

        last_v = None
        for p in points:
            v = bm.verts.new(p)
            new_elements.append(v)
            if last_v is not None:
                e = bm.edges.new((last_v, v))
                new_elements.append(e)
            last_v = v

        # points may be an iterator
        if len(new_elements) > 3:
            if mode != 'OPEN':
                e = bm.edges.new((last_v, new_elements[0]))
                new_elements.append(e)

            if mode == 'FILLED':
                f = bm.faces.new([v for v in new_elements if isinstance(v, BMVert)])
                f.normal_update()
                new_elements.append(f)

        return new_elements

    @classmethod
    def insert_edge_loop_parallel(cls, bm, faces, edges, ref_edges):
        new_verts = []
        new_edges = []
        new_faces = []

        for e in edges:
            v0, v1 = e.verts

            e_new, v_new = bmesh.utils.edge_split(e, v0, 0.5)

            if e.select:
                e_new.select = True
                v_new.select = True

            new_verts.append(v_new)
            new_edges.append(e_new)

        new_verts_set = set(new_verts)

        edge_loop = []

        if 'source' in bmesh.utils.face_split.__doc__:
            def face_split(f, v0, v1, example=None):
                return bmesh.utils.face_split(f, v0, v1, source=example)

        else:
            # pre 5.1 signature
            def face_split(f, v0, v1, example=None):
                return bmesh.utils.face_split(f, v0, v1, example=example)

        for f in faces:
            split_candidates = []

            for l in f.loops:
                if l.edge not in ref_edges:
                    continue

                v0 = l.link_loop_prev.vert
                v1 = l.link_loop_next.link_loop_next.vert

                if (v0 == v1) or (bm.edges.get((v0, v1))):
                    continue

                if (v0 in new_verts_set) and (v1 in new_verts_set):
                    split_candidates.append((v0, v1, l.edge))

            for v0, v1, ref_edge in split_candidates:
                new_face, new_loop = face_split(f, v0, v1, example=ref_edge)

                # Needs to be done like this, rather than ... = select or ... |= select
                if f.select:
                    new_face.select = True

                new_faces.append(new_face)
                new_edges.append(new_loop.edge)
                edge_loop.append(new_loop.edge)

        return {'verts': new_verts, 'edges': new_edges, 'faces': new_faces, 'edge_loop': edge_loop}
