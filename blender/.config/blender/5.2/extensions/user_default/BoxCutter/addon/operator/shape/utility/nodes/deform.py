import bpy, pathlib
from ...... utility.geometry_nodes import NodeModifier


NODES_FOLDER = 'BC_Nodes'
INPUTS = {'Taper Gizmo', 'Z Max', 'Max', 'Double Extrude', 'Taper Factor', 'Wedge Gizmo', 'Wedge Offset', 'Dimensions', 'Wedge Width', 'Bounds Mode', 'Wedge Mode', 'Method', 'Offset', 'Min', 'Wedge Factor', 'Twist Gizmo', 'Twist', 'Bounds Max', 'Wedge', 'Geometry', 'Twist Angle', 'Center', 'Taper', 'Deform Gizmo', 'Bounds Min', 'Wedge Flip', 'Z Min', 'Auto Flip'}
METHOD_INPUT = {0: 'CORNER', 'CORNER': 0, 1: 'CENTER', 'CENTER': 1, 2: 'DIMENSIONS', 'DIMENSIONS': 2, 3: 'Z ONLY', 'Z ONLY': 3}
METHOD_INPUT_STR = {'Corner': 'CORNER', 'CORNER': 'Corner', 'Center': 'CENTER', 'CENTER': 'Center', 'Dimensions': 'DIMENSIONS', 'DIMENSIONS': 'Dimensions', 'Z Only': 'Z ONLY', 'Z ONLY': 'Z Only'}
WEDGE_MODE_INPUT = {0: 'X', 'X': 0, 1: 'Y', 'Y': 1, 2: 'XY', 'XY': 2, 3: 'YX', 'YX': 3}
WEDGE_MODE_INPUT_STR = {'X': 'X', 'Y': 'Y', 'XY': 'XY', 'YX': 'YX'}
BOUNDS_MODE_INPUT = {0: 'AUTO', 'AUTO': 0, 1: 'INPUT', 'INPUT': 1}
BOUNDS_MODE_INPUT_STR = {'Auto': 'AUTO', 'AUTO': 'Auto', 'Input': 'INPUT', 'INPUT': 'Input'}
AUTO_FLIP_INPUT = {0: 'FACES', 'FACES': 0, 1: 'SCALE', 'SCALE': 1, 2: 'NONE', 'NONE': 2}
AUTO_FLIP_INPUT_STR = {'Faces': 'FACES', 'FACES': 'Faces', 'Scale': 'SCALE', 'SCALE': 'Scale', 'None': 'NONE', 'NONE': 'None'}

class Deform(NodeModifier):
    default_name = 'BC_Deform'
    asset_name = 'BC_Deform'
    blend_filename = 'BC_Shape_nodes.blend'

    @property
    def geometry(self):
        return self.input_get("Geometry")

    @geometry.setter
    def geometry(self, val):
        self.input_set("Geometry", val)
        self.update_tag()

    @property
    def method(self):
        return METHOD_INPUT_STR[self.input_get("Method")] if self.str_enum else METHOD_INPUT[self.input_get("Method")]

    @method.setter
    def method(self, val):
        self.input_set("Method", METHOD_INPUT_STR[val] if self.str_enum else METHOD_INPUT[val])
        self.update_tag()

    @property
    def deform_gizmo(self):
        return self.input_get("Deform Gizmo")

    @deform_gizmo.setter
    def deform_gizmo(self, val):
        self.input_set("Deform Gizmo", bool(val))
        self.update_tag()

    @property
    def min(self):
        return self.input_get("Min")

    @min.setter
    def min(self, val):
        self.input_set("Min", val)
        self.update_tag()

    @property
    def max(self):
        return self.input_get("Max")

    @max.setter
    def max(self, val):
        self.input_set("Max", val)
        self.update_tag()

    @property
    def center(self):
        return self.input_get("Center")

    @center.setter
    def center(self, val):
        self.input_set("Center", val)
        self.update_tag()

    @property
    def offset(self):
        return self.input_get("Offset")

    @offset.setter
    def offset(self, val):
        self.input_set("Offset", val)
        self.update_tag()

    @property
    def dimensions(self):
        return self.input_get("Dimensions")

    @dimensions.setter
    def dimensions(self, val):
        self.input_set("Dimensions", val)
        self.update_tag()

    @property
    def double_extrude(self):
        return self.input_get("Double Extrude")

    @double_extrude.setter
    def double_extrude(self, val):
        self.input_set("Double Extrude", bool(val))
        self.update_tag()

    @property
    def z_min(self):
        return self.input_get("Z Min")

    @z_min.setter
    def z_min(self, val):
        self.input_set("Z Min", float(val))
        self.update_tag()

    @property
    def z_max(self):
        return self.input_get("Z Max")

    @z_max.setter
    def z_max(self, val):
        self.input_set("Z Max", float(val))
        self.update_tag()

    @property
    def wedge(self):
        return self.input_get("Wedge")

    @wedge.setter
    def wedge(self, val):
        self.input_set("Wedge", bool(val))
        self.update_tag()

    @property
    def wedge_mode(self):
        return WEDGE_MODE_INPUT_STR[self.input_get("Wedge Mode")] if self.str_enum else WEDGE_MODE_INPUT[self.input_get("Wedge Mode")]

    @wedge_mode.setter
    def wedge_mode(self, val):
        self.input_set("Wedge Mode", WEDGE_MODE_INPUT_STR[val] if self.str_enum else WEDGE_MODE_INPUT[val])
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
    def wedge_offset(self):
        return self.input_get("Wedge Offset")

    @wedge_offset.setter
    def wedge_offset(self, val):
        self.input_set("Wedge Offset", float(val))
        self.update_tag()

    @property
    def wedge_width(self):
        return self.input_get("Wedge Width")

    @wedge_width.setter
    def wedge_width(self, val):
        self.input_set("Wedge Width", float(val))
        self.update_tag()

    @property
    def wedge_gizmo(self):
        return self.input_get("Wedge Gizmo")

    @wedge_gizmo.setter
    def wedge_gizmo(self, val):
        self.input_set("Wedge Gizmo", bool(val))
        self.update_tag()

    @property
    def twist(self):
        return self.input_get("Twist")

    @twist.setter
    def twist(self, val):
        self.input_set("Twist", bool(val))
        self.update_tag()

    @property
    def twist_angle(self):
        return self.input_get("Twist Angle")

    @twist_angle.setter
    def twist_angle(self, val):
        self.input_set("Twist Angle", float(val))
        self.update_tag()

    @property
    def twist_gizmo(self):
        return self.input_get("Twist Gizmo")

    @twist_gizmo.setter
    def twist_gizmo(self, val):
        self.input_set("Twist Gizmo", bool(val))
        self.update_tag()

    @property
    def taper(self):
        return self.input_get("Taper")

    @taper.setter
    def taper(self, val):
        self.input_set("Taper", bool(val))
        self.update_tag()

    @property
    def taper_factor(self):
        return self.input_get("Taper Factor")

    @taper_factor.setter
    def taper_factor(self, val):
        self.input_set("Taper Factor", val)
        self.update_tag()

    @property
    def taper_gizmo(self):
        return self.input_get("Taper Gizmo")

    @taper_gizmo.setter
    def taper_gizmo(self, val):
        self.input_set("Taper Gizmo", bool(val))
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
    def auto_flip(self):
        return AUTO_FLIP_INPUT_STR[self.input_get("Auto Flip")] if self.str_enum else AUTO_FLIP_INPUT[self.input_get("Auto Flip")]

    @auto_flip.setter
    def auto_flip(self, val):
        self.input_set("Auto Flip", AUTO_FLIP_INPUT_STR[val] if self.str_enum else AUTO_FLIP_INPUT[val])
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
