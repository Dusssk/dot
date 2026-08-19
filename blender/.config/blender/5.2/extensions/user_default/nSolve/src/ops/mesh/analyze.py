import bpy
import bmesh
import blf
from ...draw.face import DrawFace
from ....utils import addon
from ... import analytics


def file_load_handler(var):
    if NSOLVE_OT_Analyze._operator:
        NSOLVE_OT_Analyze._operator.end(bpy.context)
    bpy.context.scene.nsolve.ops.mesh.analyze.running = False


class NSOLVE_OT_Analyze(bpy.types.Operator):
    bl_idname = "nsolve.analyze"
    bl_label = "Analyze"
    bl_description = f"{bl_label}\n\nDisplay visual information about the mesh"
    bl_options = {'REGISTER', 'UNDO'}

    offset: bpy.props.FloatProperty(name="Offset", description="Offset distance", default=0.1, min=0.0, precision=3)

    bm: bmesh.types.BMesh = None
    mesh: bpy.types.Mesh = None
    edges: list = []

    tris: list = []
    ngons: list = []
    ngon_tris: list = []
    tris_points: list = []

    _callback_fliped: DrawFace
    _handle_fliped: int

    _callback_ngon: DrawFace
    _handle_ngon: int

    _callback_tris: DrawFace
    _handle_tris: int

    _handle_ui: int

    _operator = None
    _runnning = False

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):

        if self.__class__._operator:
            context.scene.nsolve.ops.mesh.analyze.running = False
            self.__class__._operator.end(context)
            return {'CANCELLED'}

        context.scene.nsolve.ops.mesh.analyze.running = True
        self._runnning = True

        obj = context.edit_object
        obj.update_from_editmode()

        matrix = obj.matrix_world

        self.update_mesh_info(obj.data, matrix)
        self.setup_drawing(context, self.ngon_tris, self.tris_points)

        bpy.app.handlers.depsgraph_update_post.append(self.depsgraph_update)

        bpy.app.handlers.load_pre.append(file_load_handler)
        bpy.app.handlers.load_factory_startup_post.append(file_load_handler)

        context.window_manager.modal_handler_add(self)

        self.__class__._operator = self
        analytics.stats("nSuite: Analyze")
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return {'FINISHED'}

    def depsgraph_update(self, scene, depsgraph):
        obj = bpy.context.edit_object
        if not obj:
            return

        updated = False

        for update in depsgraph.updates:
            if isinstance(update.id, bpy.types.Object):
                updated_obj = update.id.original
                if updated_obj == obj:
                    updated = True

        if updated:
            obj.update_from_editmode()
            matrix = obj.matrix_world
            self.update_mesh_info(obj.data, matrix)
            self.update_drawing(bpy.context)

    def modal(self, context, event):
        '''Main modal loop.'''

        if not self._runnning or not context.area:
            self.end(context)
            return {'CANCELLED'}

        # End the operator if we leave edit mode
        if context.mode != 'EDIT_MESH':
            self.end(context)
            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE':
            context.area.tag_redraw()

        elif event.type in {'ESC'}:
            self.end(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def end(self, context):
        '''Clean up.'''

        self.edges = []

        self.ngon_tris = []
        self.tris_points = []
        self.ngons = []
        self.tris = []
        self._runnning = False
        self.__class__._operator = None
        context.scene.nsolve.ops.mesh.analyze.running = False

        self.remove_draw_handlers()

        if self.depsgraph_update in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(self.depsgraph_update)

        if file_load_handler in bpy.app.handlers.load_pre:
            bpy.app.handlers.load_pre.remove(file_load_handler)

        if file_load_handler in bpy.app.handlers.load_factory_startup_post:
            bpy.app.handlers.load_factory_startup_post.remove(file_load_handler)

        if context.area: context.area.tag_redraw()

    def remove_draw_handlers(self):
        if self._handle_ngon: self._handle_ngon = bpy.types.SpaceView3D.draw_handler_remove(self._handle_ngon, 'WINDOW')
        if self._handle_tris: self._handle_tris = bpy.types.SpaceView3D.draw_handler_remove(self._handle_tris, 'WINDOW')
        if self._handle_ui: self._handle_ui = bpy.types.SpaceView3D.draw_handler_remove(self._handle_ui, 'WINDOW')
        if self._handle_fliped: self._handle_fliped = bpy.types.SpaceView3D.draw_handler_remove(self._handle_fliped, 'WINDOW')

    def setup_drawing(self, context, ngons, tris):
        '''Setup the drawing'''

        theme = addon.pref().theme.ops.mesh.analyze

        self._handle_ui = bpy.types.SpaceView3D.draw_handler_add(self.draw_ui, (context,), 'WINDOW', 'POST_PIXEL')

        self._callback_ngon = DrawFace(self.ngon_tris, color=theme.ngon, culling=True)
        self._handle_ngon = bpy.types.SpaceView3D.draw_handler_add(self._callback_ngon.draw, (context,), 'WINDOW', 'POST_VIEW')

        self._callback_tris = DrawFace(self.tris_points, color=theme.tris, culling=True)
        self._handle_tris = bpy.types.SpaceView3D.draw_handler_add(self._callback_tris.draw, (context,), 'WINDOW', 'POST_VIEW')

        fliped = addon.pref().ops.mesh.analyze.show_fliped
        alltris = self.ngon_tris + self.tris_points if fliped else []
        self._callback_fliped = DrawFace(alltris, color=theme.fliped, culling=True, culling_method='FRONT')
        self._handle_fliped = bpy.types.SpaceView3D.draw_handler_add(self._callback_fliped.draw, (context,), 'WINDOW', 'POST_VIEW')

    def update_drawing(self, context):
        '''Update the drawing with new points'''

        self._callback_ngon.update_batch(self.ngon_tris)
        self._callback_tris.update_batch(self.tris_points)

        fliped = addon.pref().ops.mesh.analyze.show_fliped
        alltris = self.ngon_tris + self.tris_points if fliped else []
        self._callback_fliped.update_batch(alltris)

    def update_mesh_info(self, me, matrix):
        '''Update mesh info for drawing'''

        me.calc_loop_triangles()
        self.tris_points.clear()
        self.ngon_tris.clear()
        self.ngons.clear()

        for i, loop in enumerate(me.loop_triangles):
            poly = me.polygons[me.loop_triangle_polygons[i].value]

            if poly.hide: continue

            if len(poly.vertices) == 3:
                tri = tuple(matrix @ me.vertices[j].co for j in loop.vertices)
                self.tris_points.append(tri)

            if len(poly.vertices) > 4:
                tri = tuple(matrix @ me.vertices[j].co for j in loop.vertices)
                self.ngon_tris.append(tri)

        ngons = [poly for poly in me.polygons if len(poly.vertices) > 4 and not poly.hide]
        self.ngons = [tuple(matrix @ me.vertices[j].co for j in poly.vertices) for poly in ngons]

    def draw_ui(self, context):
        # Set position and size
        region = context.region
        width = region.width

        # Get interface options
        nsolve_prefs = addon.pref().tools.nsolve
        show_interface = nsolve_prefs.InterfaceOptions.show_interface

        # x and y in percentage of width and height
        x = width/2 if show_interface else width - 170
        y = 70

        text = "Analyze"

        font_id = 0
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 20)
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 5, 0, 0, 0, 1)
        blf.color(font_id, 1, 1, 1, 0.6)
        blf.draw(font_id, text)
        interface = addon.pref().ops.mesh.analyze.show_interface
        if interface:
            blf.position(font_id, x - 22, y - 20, 0)
            blf.size(font_id, 14)
            blf.draw(font_id, f"Tris: {len(self.tris_points)} / Ngons: {len(self.ngons)}")


class types():
    class theme(bpy.types.PropertyGroup):
        ngon: bpy.props.FloatVectorProperty(name="Analyze Ngon", description="Color of Ngon", size=4, subtype='COLOR', default=(0.5, 0.0, 0.0, 0.1), min=0.0, max=1.0)
        tris: bpy.props.FloatVectorProperty(name="Analyze Tris", description="Color of Tris", size=4, subtype='COLOR', default=(0.5, 0.5, 0.0, 0.1), min=0.0, max=1.0)
        intersect: bpy.props.FloatVectorProperty(name="Analyze Intersect", description="Color of Intersect", size=4, subtype='COLOR', default=(0.0, 0.9, 0.0, 0.3), min=0.0, max=1.0)
        fliped: bpy.props.FloatVectorProperty(name="Analyze Fliped", description="Color of Fliped", size=4, subtype='COLOR', default=(0.1, 0.1, 0.1, 0.5), min=0.0, max=1.0)

    class scene(bpy.types.PropertyGroup):
        running: bpy.props.BoolProperty(name="Running", description="Operator is running", default=False)

    class pref(bpy.types.PropertyGroup):
        show_interface: bpy.props.BoolProperty(name="Show Interface", description="Show the interface", default=True)
        show_fliped: bpy.props.BoolProperty(name="Show Fliped", description="Show the fliped faces", default=False)


types_classes = (types.theme,
                 types.scene,
                 types.pref)
