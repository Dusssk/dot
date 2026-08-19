import bpy, pathlib
from ...... utility.geometry_nodes import NodeModifier


NODES_FOLDER = 'BC_Nodes'
INPUTS = {'Wireframe', 'Box X', 'Ngon Fill', 'Face Shading', 'Flip Top Faces', 'Ngon Offset Bottom', 'Object', 'Grid Border', 'Wedge Width', 'Mid Edges Float', 'Bounds Mode', 'Flip X', 'Grid Y', 'Gridify Y', 'Flip Z', 'Top Edges', 'Shape', 'Wedge Factor', 'Extrude Mode', 'Resample Edges', 'Bot Edge', 'Bounds Max', 'Merge Dist', 'Divisions Z', 'Geometry', 'Star', 'Gridify', 'Grid X', 'Wedge Axis', 'Flip Y', 'Top Edges Float Val', 'Bot Edges Float Val', 'Gridify Scale', 'Gridify X', 'Passthrough', 'Vertices', 'Mid Edges', 'Vertex Bevel', 'Bounds Min', 'Flip Bottom Faces', 'Bot Edges Float', 'Wedge Flip', 'Flip Face Name', 'Ngon Offset Top', 'Top Edges Float', 'Mid Edges Float Val', 'Box Z', 'Box Y', 'Star Factor', 'Ngon Cyclic'}
SHAPE_INPUT = {0: 'INPUT', 'INPUT': 0, 1: 'EXTRUDE', 'EXTRUDE': 1, 2: 'BOX', 'BOX': 2, 5: 'GRID', 'GRID': 5, 3: 'WEDGE', 'WEDGE': 3, 4: 'CYLINDER', 'CYLINDER': 4, 6: 'NGON', 'NGON': 6}
SHAPE_INPUT_STR = {'Input': 'INPUT', 'INPUT': 'Input', 'Extrude': 'EXTRUDE', 'EXTRUDE': 'Extrude', 'Box': 'BOX', 'BOX': 'Box', 'Grid': 'GRID', 'GRID': 'Grid', 'Wedge': 'WEDGE', 'WEDGE': 'Wedge', 'Cylinder': 'CYLINDER', 'CYLINDER': 'Cylinder', 'Ngon': 'NGON', 'NGON': 'Ngon'}
EXTRUDE_MODE_INPUT = {0: 'CURVE', 'CURVE': 0, 1: 'MESH', 'MESH': 1}
EXTRUDE_MODE_INPUT_STR = {'Curve': 'CURVE', 'CURVE': 'Curve', 'Mesh': 'MESH', 'MESH': 'Mesh'}
FACE_SHADING_INPUT = {0: 'KEEP', 'KEEP': 0, 1: 'FLAT', 'FLAT': 1, 2: 'SMOOTH', 'SMOOTH': 2}
FACE_SHADING_INPUT_STR = {'Keep': 'KEEP', 'KEEP': 'Keep', 'Flat': 'FLAT', 'FLAT': 'Flat', 'Smooth': 'SMOOTH', 'SMOOTH': 'Smooth'}
WEDGE_AXIS_INPUT = {0: 'X', 'X': 0, 1: 'Y', 'Y': 1, 2: 'XY', 'XY': 2, 3: 'YX', 'YX': 3}
WEDGE_AXIS_INPUT_STR = {'X': 'X', 'Y': 'Y', 'XY': 'XY', 'YX': 'YX'}
BOUNDS_MODE_INPUT = {0: 'AUTO', 'AUTO': 0, 1: 'INPUT', 'INPUT': 1}
BOUNDS_MODE_INPUT_STR = {'Auto': 'AUTO', 'AUTO': 'Auto', 'Input': 'INPUT', 'INPUT': 'Input'}

class Generate(NodeModifier):
    default_name = 'BC_Generate'
    asset_name = 'BC_Generate'
    blend_filename = 'BC_Shape_nodes.blend'

    @property
    def geometry(self):
        return self.input_get("Geometry")

    @geometry.setter
    def geometry(self, val):
        self.input_set("Geometry", val)
        self.update_tag()

    @property
    def shape(self):
        return SHAPE_INPUT_STR[self.input_get("Shape")] if self.str_enum else SHAPE_INPUT[self.input_get("Shape")]

    @shape.setter
    def shape(self, val):
        self.input_set("Shape", SHAPE_INPUT_STR[val] if self.str_enum else SHAPE_INPUT[val])
        self.update_tag()

    @property
    def object(self):
        return self.input_get("Object")

    @object.setter
    def object(self, val):
        self.input_set("Object", val)
        self.update_tag()

    @property
    def passthrough(self):
        return self.input_get("Passthrough")

    @passthrough.setter
    def passthrough(self, val):
        self.input_set("Passthrough", bool(val))
        self.update_tag()

    @property
    def extrude_mode(self):
        return EXTRUDE_MODE_INPUT_STR[self.input_get("Extrude Mode")] if self.str_enum else EXTRUDE_MODE_INPUT[self.input_get("Extrude Mode")]

    @extrude_mode.setter
    def extrude_mode(self, val):
        self.input_set("Extrude Mode", EXTRUDE_MODE_INPUT_STR[val] if self.str_enum else EXTRUDE_MODE_INPUT[val])
        self.update_tag()

    @property
    def resample_edges(self):
        return self.input_get("Resample Edges")

    @resample_edges.setter
    def resample_edges(self, val):
        self.input_set("Resample Edges", bool(val))
        self.update_tag()

    @property
    def face_shading(self):
        return FACE_SHADING_INPUT_STR[self.input_get("Face Shading")] if self.str_enum else FACE_SHADING_INPUT[self.input_get("Face Shading")]

    @face_shading.setter
    def face_shading(self, val):
        self.input_set("Face Shading", FACE_SHADING_INPUT_STR[val] if self.str_enum else FACE_SHADING_INPUT[val])
        self.update_tag()

    @property
    def vertices(self):
        return self.input_get("Vertices")

    @vertices.setter
    def vertices(self, val):
        self.input_set("Vertices", val)
        self.update_tag()

    @property
    def grid_x(self):
        return self.input_get("Grid X")

    @grid_x.setter
    def grid_x(self, val):
        self.input_set("Grid X", val)
        self.update_tag()

    @property
    def grid_y(self):
        return self.input_get("Grid Y")

    @grid_y.setter
    def grid_y(self, val):
        self.input_set("Grid Y", val)
        self.update_tag()

    @property
    def grid_border(self):
        return self.input_get("Grid Border")

    @grid_border.setter
    def grid_border(self, val):
        self.input_set("Grid Border", bool(val))
        self.update_tag()

    @property
    def divisions_z(self):
        return self.input_get("Divisions Z")

    @divisions_z.setter
    def divisions_z(self, val):
        self.input_set("Divisions Z", val)
        self.update_tag()

    @property
    def wedge_axis(self):
        return WEDGE_AXIS_INPUT_STR[self.input_get("Wedge Axis")] if self.str_enum else WEDGE_AXIS_INPUT[self.input_get("Wedge Axis")]

    @wedge_axis.setter
    def wedge_axis(self, val):
        self.input_set("Wedge Axis", WEDGE_AXIS_INPUT_STR[val] if self.str_enum else WEDGE_AXIS_INPUT[val])
        self.update_tag()

    @property
    def wedge_flip(self):
        return self.input_get("Wedge Flip")

    @wedge_flip.setter
    def wedge_flip(self, val):
        self.input_set("Wedge Flip", bool(val))
        self.update_tag()

    @property
    def wedge_factor(self):
        return self.input_get("Wedge Factor")

    @wedge_factor.setter
    def wedge_factor(self, val):
        self.input_set("Wedge Factor", float(val))
        self.update_tag()

    @property
    def wedge_width(self):
        return self.input_get("Wedge Width")

    @wedge_width.setter
    def wedge_width(self, val):
        self.input_set("Wedge Width", float(val))
        self.update_tag()

    @property
    def star(self):
        return self.input_get("Star")

    @star.setter
    def star(self, val):
        self.input_set("Star", bool(val))
        self.update_tag()

    @property
    def star_factor(self):
        return self.input_get("Star Factor")

    @star_factor.setter
    def star_factor(self, val):
        self.input_set("Star Factor", float(val))
        self.update_tag()

    @property
    def box_x(self):
        return self.input_get("Box X")

    @box_x.setter
    def box_x(self, val):
        self.input_set("Box X", val)
        self.update_tag()

    @property
    def box_y(self):
        return self.input_get("Box Y")

    @box_y.setter
    def box_y(self, val):
        self.input_set("Box Y", val)
        self.update_tag()

    @property
    def box_z(self):
        return self.input_get("Box Z")

    @box_z.setter
    def box_z(self, val):
        self.input_set("Box Z", val)
        self.update_tag()

    @property
    def ngon_cyclic(self):
        return self.input_get("Ngon Cyclic")

    @ngon_cyclic.setter
    def ngon_cyclic(self, val):
        self.input_set("Ngon Cyclic", bool(val))
        self.update_tag()

    @property
    def ngon_fill(self):
        return self.input_get("Ngon Fill")

    @ngon_fill.setter
    def ngon_fill(self, val):
        self.input_set("Ngon Fill", bool(val))
        self.update_tag()

    @property
    def ngon_offset_top(self):
        return self.input_get("Ngon Offset Top")

    @ngon_offset_top.setter
    def ngon_offset_top(self, val):
        self.input_set("Ngon Offset Top", float(val))
        self.update_tag()

    @property
    def ngon_offset_bottom(self):
        return self.input_get("Ngon Offset Bottom")

    @ngon_offset_bottom.setter
    def ngon_offset_bottom(self, val):
        self.input_set("Ngon Offset Bottom", float(val))
        self.update_tag()

    @property
    def wireframe(self):
        return self.input_get("Wireframe")

    @wireframe.setter
    def wireframe(self, val):
        self.input_set("Wireframe", bool(val))
        self.update_tag()

    @property
    def flip_x(self):
        return self.input_get("Flip X")

    @flip_x.setter
    def flip_x(self, val):
        self.input_set("Flip X", bool(val))
        self.update_tag()

    @property
    def flip_y(self):
        return self.input_get("Flip Y")

    @flip_y.setter
    def flip_y(self, val):
        self.input_set("Flip Y", bool(val))
        self.update_tag()

    @property
    def flip_z(self):
        return self.input_get("Flip Z")

    @flip_z.setter
    def flip_z(self, val):
        self.input_set("Flip Z", bool(val))
        self.update_tag()

    @property
    def flip_top_faces(self):
        return self.input_get("Flip Top Faces")

    @flip_top_faces.setter
    def flip_top_faces(self, val):
        self.input_set("Flip Top Faces", bool(val))
        self.update_tag()

    @property
    def flip_bottom_faces(self):
        return self.input_get("Flip Bottom Faces")

    @flip_bottom_faces.setter
    def flip_bottom_faces(self, val):
        self.input_set("Flip Bottom Faces", bool(val))
        self.update_tag()

    @property
    def flip_face_name(self):
        return self.input_get("Flip Face Name")

    @flip_face_name.setter
    def flip_face_name(self, val):
        self.input_set("Flip Face Name", val)
        self.update_tag()

    @property
    def gridify(self):
        return self.input_get("Gridify")

    @gridify.setter
    def gridify(self, val):
        self.input_set("Gridify", bool(val))
        self.update_tag()

    @property
    def gridify_x(self):
        return self.input_get("Gridify X")

    @gridify_x.setter
    def gridify_x(self, val):
        self.input_set("Gridify X", val)
        self.update_tag()

    @property
    def gridify_y(self):
        return self.input_get("Gridify Y")

    @gridify_y.setter
    def gridify_y(self, val):
        self.input_set("Gridify Y", val)
        self.update_tag()

    @property
    def gridify_scale(self):
        return self.input_get("Gridify Scale")

    @gridify_scale.setter
    def gridify_scale(self, val):
        self.input_set("Gridify Scale", float(val))
        self.update_tag()

    @property
    def bounds_mode(self):
        return BOUNDS_MODE_INPUT_STR[self.input_get("Bounds Mode")] if self.str_enum else BOUNDS_MODE_INPUT[self.input_get("Bounds Mode")]

    @bounds_mode.setter
    def bounds_mode(self, val):
        self.input_set("Bounds Mode", BOUNDS_MODE_INPUT_STR[val] if self.str_enum else BOUNDS_MODE_INPUT[val])
        self.update_tag()

    @property
    def bounds_min(self):
        return self.input_get("Bounds Min")

    @bounds_min.setter
    def bounds_min(self, val):
        self.input_set("Bounds Min", val)
        self.update_tag()

    @property
    def bounds_max(self):
        return self.input_get("Bounds Max")

    @bounds_max.setter
    def bounds_max(self, val):
        self.input_set("Bounds Max", val)
        self.update_tag()

    @property
    def top_edges(self):
        return self.input_get("Top Edges")

    @top_edges.setter
    def top_edges(self, val):
        self.input_set("Top Edges", val)
        self.update_tag()

    @property
    def mid_edges(self):
        return self.input_get("Mid Edges")

    @mid_edges.setter
    def mid_edges(self, val):
        self.input_set("Mid Edges", val)
        self.update_tag()

    @property
    def bot_edge(self):
        return self.input_get("Bot Edge")

    @bot_edge.setter
    def bot_edge(self, val):
        self.input_set("Bot Edge", val)
        self.update_tag()

    @property
    def top_edges_float(self):
        return self.input_get("Top Edges Float")

    @top_edges_float.setter
    def top_edges_float(self, val):
        self.input_set("Top Edges Float", val)
        self.update_tag()

    @property
    def top_edges_float_val(self):
        return self.input_get("Top Edges Float Val")

    @top_edges_float_val.setter
    def top_edges_float_val(self, val):
        self.input_set("Top Edges Float Val", float(val))
        self.update_tag()

    @property
    def mid_edges_float(self):
        return self.input_get("Mid Edges Float")

    @mid_edges_float.setter
    def mid_edges_float(self, val):
        self.input_set("Mid Edges Float", val)
        self.update_tag()

    @property
    def mid_edges_float_val(self):
        return self.input_get("Mid Edges Float Val")

    @mid_edges_float_val.setter
    def mid_edges_float_val(self, val):
        self.input_set("Mid Edges Float Val", float(val))
        self.update_tag()

    @property
    def bot_edges_float(self):
        return self.input_get("Bot Edges Float")

    @bot_edges_float.setter
    def bot_edges_float(self, val):
        self.input_set("Bot Edges Float", val)
        self.update_tag()

    @property
    def bot_edges_float_val(self):
        return self.input_get("Bot Edges Float Val")

    @bot_edges_float_val.setter
    def bot_edges_float_val(self, val):
        self.input_set("Bot Edges Float Val", float(val))
        self.update_tag()

    @property
    def vertex_bevel(self):
        return self.input_get("Vertex Bevel")

    @vertex_bevel.setter
    def vertex_bevel(self, val):
        self.input_set("Vertex Bevel", val)
        self.update_tag()

    @property
    def merge_dist(self):
        return self.input_get("Merge Dist")

    @merge_dist.setter
    def merge_dist(self, val):
        self.input_set("Merge Dist", float(val))
        self.update_tag()

    @classmethod
    def is_valid_node_group(cls, node_group) -> bool:
        return INPUTS.issubset(node_group.interface.items_tree.keys())

    @classmethod
    def get_or_load_node_group(cls):
        if not cls.last_valid_group_name:
            node_groups = list(filter(cls.is_asset_node_group, bpy.data.node_groups))

            for ng in node_groups:
                if cls.is_valid_node_group(ng):
                    return ng

        try:
            node_group = bpy.data.node_groups[cls.last_valid_group_name]
            if cls.is_asset_node_group(node_group) and cls.is_valid_node_group(node_group):
                return node_group

        except KeyError:
            pass

        # if last loaded group isn't valid, load a new one
        path = cls.get_filepath()

        with bpy.data.libraries.load(path) as (data_from, data_to):
            data_to.node_groups.append(cls.asset_name)

        node_group = data_to.node_groups[0]

        cls.last_valid_group_name = data_to.node_groups[0].name

        return data_to.node_groups[0]

    @classmethod
    def calc_asset_path(cls):
        blend = cls.blend_filename

        path = pathlib.Path(__file__).parent / NODES_FOLDER

        return str(path / blend)

    def update_tag(self):
        self.modifier.id_data.update_tag()
