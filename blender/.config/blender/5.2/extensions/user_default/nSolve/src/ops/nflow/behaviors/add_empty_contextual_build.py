import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *


class Add_Empty_ContextualBuild(NFlowBehavior):
    undo_message = 'Contextual Build'

    capabilities = {'SHRINKWRAP', 'SNAP', 'MIRROR'}

    from_selection = True
    select_end = False
    force_tris = False
    enable_retopo_overlay = False

    @classmethod
    def validate_elements(cls, elements):
        if not elements:
            return True
        
        elem = elements[0]
        
        if isinstance(elem, BMFace):
            return False
        
        return cls.is_boundary(elem)

    def hover(self, context, event):
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        obj, elem, pos3d = self.find_candidate(mouse_pos)
        
        NFlow.update_scene_ref()
        
        radius = NFlowPrefs.get('vert_radius_base')
        NFlow.add_vert(pos3d, PresetOverride.get('color_vertex'), radius)
        
        if elem is None:
            return
        
        matrix = obj.matrix_world
        
        if isinstance(elem, BMVert):
            verts = [pos3d, matrix @ elem.co]
            NFlow.add_edge(verts, PresetOverride.get('color_edge'))
        elif isinstance(elem, BMEdge):
            verts = [pos3d, *((matrix @ v.co) for v in elem.verts)]
            NFlow.add_face(verts, PresetOverride.get('color_face'))
            # NFlow.add_edge([verts[0], verts[1]], PresetOverride.get('color_edge'))
            # NFlow.add_edge([verts[0], verts[2]], PresetOverride.get('color_edge'))

    def invoke(self, context, event):
        if self.enable_retopo_overlay:
            space_data = context.space_data
            if hasattr(space_data.overlay, 'show_retopology'):
                space_data.overlay.show_retopology = True
        
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        obj, elem, pos3d = self.find_candidate(mouse_pos)
        
        editor = (self.editors.get(obj) if obj else self.editor)
        
        self.original_mesh_selection = store_mesh_selection()
        
        v = editor.add_vert(editor.local_matrix_p @ pos3d)
        self.vertex = v
        self.start_pos = pos3d
        self.last_pos = pos3d
        self.snap_vertex = None
        
        self.use_align_to_view = False
        
        has_end_edge = False
        
        if isinstance(elem, BMVert):
            editor.add_edge((elem, v))
        elif isinstance(elem, BMEdge):
            face = next(iter(elem.link_faces), None)
            args = ([] if face is None else [face])
            
            v0, v1 = elem.verts
            editor.add_edge((v0, v))
            editor.add_edge((v1, v))
            
            if self.force_tris or (face is None) or (len(face.verts) > 3):
                editor.add_face((v, v0, v1), face, select=False)
                self.use_align_to_view = True
            else:
                face_verts = list(face.verts)
                i0 = face_verts.index(v0)
                i1 = face_verts.index(v1)
                i = (i1 if (abs(i1 - i0) > 1) == (i0 > i1) else i0)
                face_verts.insert(i, v)
                editor.add_face(face_verts, face, select=False)
                editor.remove([elem, face])
                has_end_edge = True
        
        elements = editor.get_elements('ADDED')
        
        elem_type = 'NONE'
        self.set_target(editor.obj, editor.bm, elem_type, elements)
        
        if self.use_post_select_elements:
            select_elements = self.filter_select_elements(elements, has_end_edge)
            MeshUtil.select_elements({editor.bm: select_elements}, mode=self.post_select_mode)
        
        self.fix_face_orientation()
        
        self.editors.update_meshes()
        
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            self.on_mousemove(mouse_pos, context)
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            self.on_finish()
            return 'FINISHED'
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.on_cancel()
            return 'CANCELLED'

    def on_mousemove(self, mouse_pos, context):
        editor = self.editor
        
        select = self.vertex.select
        
        self.vertex.hide = True
        editor.update_mesh()
        
        elem_type = 'VERTEX'
        obj, bm, elem_type, elements = find_closest_mesh_element(context, mouse_pos, elem_type)
        
        if elements and (elements[0] != self.vertex):
            NFlow.update_display_data(obj, elem_type, elements)
            pos3d = obj.matrix_world @ elements[0].co
            self.last_pos = pos3d
            self.snap_vertex = elements[0]
        else:
            NFlow.cleanup()
            self.snap_vertex = None
            pos3d, self.last_pos = self.snap_cast(mouse_pos, self.last_pos)
        
        self.vertex.hide = False
        self.vertex.select = select
        
        self.vertex.co = editor.local_matrix_p @ pos3d
        
        self.fix_face_orientation()
        
        editor.update_mesh()

    def on_finish(self):
        self.editors.apply()
        
        if self.snap_vertex is not None:
            bm = self.editor.bm
            
            verts = [self.snap_vertex, self.vertex]
            bmesh.ops.pointmerge(bm, verts=verts, merge_co=self.snap_vertex.co)
            
            if self.use_post_select_elements:
                self.snap_vertex.select = True
                bm.select_history.add(self.snap_vertex)
                bm.select_flush(True)
            
            self.editors.update_meshes()

    def on_cancel(self):
        restore_mesh_selection(self.original_mesh_selection)
        
        self.editors.revert()
        
        NFlow.cleanup()
        NFlow.update_scene_ref()

    def filter_select_elements(self, elements, has_end_edge):
        if not self.select_end:
            return elements
        
        select_elements = {self.vertex}
        
        if not has_end_edge:
            return select_elements
        
        def count_faces(v):
            return sum(1 for f in v.link_faces if not f.hide)
        
        for elem in elements:
            if not (isinstance(elem, BMEdge) and elem.is_boundary):
                continue
            
            if all((count_faces(v2) < 2) for v2 in elem.verts):
                select_elements.add(elem)
        
        return select_elements

    def fix_face_orientation(self):
        if self.use_align_to_view:
            editor = self.editor
            view_dir_local = editor.local_matrix_v @ self.view_info['axis_z']
            misaligned = MeshUtil.find_misaligned_faces(self.elements, fallback=-view_dir_local)
            editor.flip(misaligned)

    @classmethod
    def is_boundary(cls, elem):
        if isinstance(elem, BMFace):
            return False
        return elem.is_boundary or (len(elem.link_faces) == 0)

    @classmethod
    def find_selected_boundary(cls, bm, use_history=False):
        if use_history:
            edges = set()
            verts = set()
            
            for elem in bm.select_history:
                if isinstance(elem, BMFace):
                    if (not elem.hide) and elem.select:
                        for elem in elem.edges:
                            if (not elem.hide) and cls.is_boundary(elem):
                                edges.add(elem)
                    continue
                
                if (not elem.hide) and elem.select and cls.is_boundary(elem):
                    if isinstance(elem, BMEdge):
                        edges.add(elem)
                    else:
                        verts.add(elem)
            
            return edges or verts
        
        elements = set()
        
        for elem in bm.edges:
            if (not elem.hide) and elem.select and cls.is_boundary(elem):
                elements.add(elem)
        
        for elem in bm.faces:
            if (not elem.hide) and elem.select:
                for elem in elem.edges:
                    if (not elem.hide) and cls.is_boundary(elem):
                        elements.add(elem)
        
        if elements:
            return elements
        
        for elem in bm.verts:
            if (not elem.hide) and elem.select and cls.is_boundary(elem):
                elements.add(elem)
        
        return elements

    def find_candidate(self, mouse_pos):
        context = bpy.context
        active_obj = context.object
        
        element_sets = []
        if self.from_selection:
            for obj, mesh, bm in EditableMeshes.all():
                element_sets.append((obj, self.find_selected_boundary(bm)))
        
        pos3d, obj, elem = self.raycaster.nearest_along_ray(mouse_pos, element_sets,
            use_raycast=False, use_depth=False, clamp=True)
        
        if active_obj:
            depth_ref = Vector(active_obj.matrix_world.translation)
        else:
            depth_ref = Vector(context.scene.cursor.location)
        pos3d, depth_ref = self.snap_cast(mouse_pos, depth_ref)
        
        if self.elements and self.is_boundary(self.elements[0]):
            obj = self.obj
            elem = self.elements[0]
        else:
            if (obj is None) and active_obj:
                if (active_obj.type == 'MESH') and (active_obj.mode == 'EDIT'):
                    obj = active_obj
        
        return obj, elem, pos3d

    def snap_cast(self, mouse_pos, depth_ref):
        origin, direction = self.raycaster.ray(mouse_pos)
        result = self.raycaster.query(origin, direction)
        
        if result[0]:
            points = [result[1]]
            snap_options = set(self.snap_options_mirror)
            if self.use_snap:
                snap_options.update(self.snap_options)
            radius_scene = NFlowPrefs.get('snap_radius')
            MeshUtil.snap(points, snap_options, output=points,
                raycaster=self.raycaster, radius_scene=radius_scene,
                obj=self.obj, original_points=[getattr(self, 'start_pos', None)])
            pos3d = points[0]
            depth_ref = pos3d
        else:
            pos3d = self.raycaster.unproject(mouse_pos, depth_ref)
        
        return pos3d, depth_ref


NFlow.behaviors['nFlow: Easy Build'] = dict(
    type=Add_Empty_ContextualBuild,
    description='Make a vertex, edge, triangle or quad depending on the context',
    cursor='PAINT_BRUSH',
    elements={'NONE', 'VERTEX', 'EDGE'},
    options=[
        dict(idname='from_selection', name='From selection', default=True),
        dict(idname='select_end', name='Select only the end', default=False),
        dict(idname='force_tris', name='Force triangles', default=False),
        dict(idname='enable_retopo_overlay', name='Enable Retopology overlay', default=False),
    ],
    context_modes={'EDIT_MESH', 'OBJECT'},
)
