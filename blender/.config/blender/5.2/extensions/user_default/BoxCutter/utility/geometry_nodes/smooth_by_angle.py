import bpy, pathlib, sys
from . node_modifier import NodeModifier


class SmoothByAngle(NodeModifier):
    default_name = 'Smooth by Angle'
    asset_name = 'Smooth by Angle'

    # input wrappers

    @property
    def angle (self):
        return self.input_get('Angle')

    @angle.setter
    def angle(self, value):
        self.input_set('Angle', float(value))
        self.update_tag()

    @property
    def ignore_sharpness (self):
        return self.input_get('Ignore Sharpness')

    @ignore_sharpness.setter
    def ignore_sharpness(self, value):
        self.input_set('Ignore Sharpness', bool(value))
        self.update_tag()

    @classmethod
    def is_valid_node_group(cls, node_group) -> bool:
        return {'Angle', 'Ignore Sharpness'}.issubset(node_group.interface.items_tree.keys())

    @classmethod
    def calc_asset_path(cls):
        blend = 'smooth_by_angle.blend' # pre 5.0 blend file

        path = cls.builtin_geometry_nodes_path() / blend
        if path.exists():
            return str(path)

        blend = 'geometry_nodes_essentials.blend'
        return str(cls.builtin_geometry_nodes_path() / blend)

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
            data_to.node_groups.append('Smooth by Angle')

        node_group = data_to.node_groups[0]

        cls.last_valid_group_name = data_to.node_groups[0].name

        return data_to.node_groups[0]