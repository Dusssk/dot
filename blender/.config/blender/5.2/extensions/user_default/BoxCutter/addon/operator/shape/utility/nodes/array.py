import bpy, pathlib
from ...... utility.geometry_nodes import NodeModifier


NODES_FOLDER = 'BC_Nodes'
INPUTS = {'Count', 'Geometry', 'Mode', 'Align Rotation', 'Angle', 'Pivot', 'Offset Mode', 'Pivot Vec', 'Full Circle', 'Offset', 'Displacement'}
MODE_INPUT = {0: 'LINEAR', 'LINEAR': 0, 1: 'CIRCLE', 'CIRCLE': 1}
MODE_INPUT_STR = {'Linear': 'LINEAR', 'LINEAR': 'Linear', 'Circle': 'CIRCLE', 'CIRCLE': 'Circle'}
OFFSET_MODE_INPUT = {2: 'OFFSET', 'OFFSET': 2, 3: 'STRETCH', 'STRETCH': 3}
OFFSET_MODE_INPUT_STR = {'Offset': 'OFFSET', 'OFFSET': 'Offset', 'Stretch': 'STRETCH', 'STRETCH': 'Stretch'}
PIVOT_INPUT = {0: 'CENTER', 'CENTER': 0, 1: 'VECTOR', 'VECTOR': 1}
PIVOT_INPUT_STR = {'Center': 'CENTER', 'CENTER': 'Center', 'Vector': 'VECTOR', 'VECTOR': 'Vector'}


class Array(NodeModifier):
    default_name = 'BC_Array'
    asset_name = 'BC_Array'
    blend_filename = 'BC_Shape_nodes.blend'

    @property
    def geometry(self):
        return self.input_get("Geometry")

    @geometry.setter
    def geometry(self, val):
        self.input_set("Geometry", val)
        self.update_tag()

    @property
    def mode(self):
        return MODE_INPUT_STR[self.input_get("Mode")] if self.str_enum else MODE_INPUT[self.input_get("Mode")]

    @mode.setter
    def mode(self, val):
        self.input_set("Mode", MODE_INPUT_STR[val] if self.str_enum else MODE_INPUT[val])
        self.update_tag()

    @property
    def offset_mode(self):
        return OFFSET_MODE_INPUT_STR[self.input_get("Offset Mode")] if self.str_enum else OFFSET_MODE_INPUT[self.input_get("Offset Mode")]

    @offset_mode.setter
    def offset_mode(self, val):
        self.input_set("Offset Mode", OFFSET_MODE_INPUT_STR[val] if self.str_enum else OFFSET_MODE_INPUT[val])
        self.update_tag()

    @property
    def pivot(self):
        return PIVOT_INPUT_STR[self.input_get("Pivot")] if self.str_enum else PIVOT_INPUT[self.input_get("Pivot")]

    @pivot.setter
    def pivot(self, val):
        self.input_set("Pivot", PIVOT_INPUT_STR[val] if self.str_enum else PIVOT_INPUT[val])
        self.update_tag()

    @property
    def pivot_vec(self):
        return self.input_get("Pivot Vec")

    @pivot_vec.setter
    def pivot_vec(self, val):
        self.input_set("Pivot Vec", val)
        self.update_tag()

    @property
    def offset(self):
        return self.input_get("Offset")

    @offset.setter
    def offset(self, val):
        self.input_set("Offset", val)
        self.update_tag()

    @property
    def count(self):
        return self.input_get("Count")

    @count.setter
    def count(self, val):
        self.input_set("Count", val)
        self.update_tag()

    @property
    def displacement(self):
        return self.input_get("Displacement")

    @displacement.setter
    def displacement(self, val):
        self.input_set("Displacement", val)
        self.update_tag()

    @property
    def full_circle(self):
        return self.input_get("Full Circle")

    @full_circle.setter
    def full_circle(self, val):
        self.input_set("Full Circle", bool(val))
        self.update_tag()

    @property
    def angle(self):
        return self.input_get("Angle")

    @angle.setter
    def angle(self, val):
        self.input_set("Angle", float(val))
        self.update_tag()

    @property
    def align_rotation(self):
        return self.input_get("Align Rotation")

    @align_rotation.setter
    def align_rotation(self, val):
        self.input_set("Align Rotation", bool(val))
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
