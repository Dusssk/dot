import bpy, pathlib, sys

# track if mod object is usable as dict for properties lookup pre 5.2
ID_PROP_LOOKUP = 2 # 0 no 5.2+, 1 yes, 2 unchecked

class NodeModifier():
    '''Base wrapper class for asset geometry nodes modifiers'''

    input_map = dict()
    prop_draw_map = dict()
    modifier = None
    last_valid_group_name = ''
    default_name = ''
    asset_name = '' # name of asset as in library blend file
    _filepath = '' # used for cacheing string
    blend_filename = 'geometry_nodes_essentials.blend' #5.0 node lib
    str_enum = False # track if enums value are handled as strings 5.2+

    # Copy shared modifier interface
    @property
    def show_on_cage(self):
        return self.modifier.show_on_cage

    @show_on_cage.setter
    def show_on_cage(self, val):
        self.modifier.show_on_cage = val

    @property
    def show_in_editmode(self):
        return self.modifier.show_in_editmode

    @show_in_editmode.setter
    def show_in_editmode(self, val):
        self.modifier.show_in_editmode = val

    @property
    def show_viewport(self):
        return self.modifier.show_viewport

    @show_viewport.setter
    def show_viewport(self, val):
        self.modifier.show_viewport = val

    @property
    def show_render(self):
        return self.modifier.show_render

    @show_render.setter
    def show_render(self, val):
        self.modifier.show_render = val

    @property
    def show_expanded(self):
        return self.modifier.show_render

    @show_expanded.setter
    def show_expanded(self, val):
        self.modifier.show_expanded = val

    @property
    def name(self):
        return self.modifier.name

    @name.setter
    def name(self, val):
        self.modifier.name = val

    @property
    def use_pin_to_last(self):
        return getattr(self.modifier, 'use_pin_to_last', False)

    @use_pin_to_last.setter
    def use_pin_to_last(self, val):
        try:
            self.modifier.use_pin_to_last = val
        except:
            pass

    @property
    def show_group_selector(self):
        return getattr(self.modifier, 'show_group_selector', False)

    @show_group_selector.setter
    def show_group_selector(self, val):
        try:
            self.modifier.show_group_selector = val
        except:
            pass

    # Shared implementation

    @classmethod
    def new(cls, modifier):
        '''Return new wrapper for modifer or None if modifier's node group is not valid'''

        if not cls.is_valid_modifier(modifier): return None

        return cls.new_unchecked(modifier)

    @classmethod
    def from_object (cls, object):
        '''Create new modifier on object and return wrapper'''

        modifier = object.modifiers.new(cls.default_name, 'NODES')
        modifier.node_group = cls.get_or_load_node_group()
        modifier.node_group.is_modifier = False # keep modifier dropdown clean
        modifier.node_group.asset_clear() # match ops behavior

        return cls.new_unchecked(modifier)

    @classmethod
    def get_filepath(cls):
        '''Return chached filepath to the blend file'''

        if not cls._filepath:
            cls._filepath = cls.calc_asset_path()

        return cls._filepath

    @classmethod
    def new_unchecked (cls, modifier):
        '''Crate new wrapper from modifier without checking modifier validity and create input map for the types'''

        if not cls.input_map:
            cls.input_map_build(modifier)

        new = cls()
        new.modifier = modifier
        new.show_group_selector = False

        NodeModifier.validate_id_prop_lookup()

        return new

    @classmethod
    def input_map_build(cls, modifier):
        cls.input_map = {input.name : input.identifier for input in modifier.node_group.interface.items_tree if input.item_type == 'SOCKET' and input.in_out=='INPUT'}

    @classmethod
    def prop_draw_map_build(cls, modifier):
        cls.prop_draw_map = {input.name.lower().replace(' ', '_') : input.identifier for input in modifier.node_group.interface.items_tree if input.item_type == 'SOCKET' and input.in_out=='INPUT'}

    @classmethod
    def is_valid_modifier (cls, modifier) -> bool:
        '''Check if modifier object can be wrapped'''

        if modifier.type != 'NODES': return False
        if not modifier.node_group: return False
        if not cls.is_asset_node_group(modifier.node_group): return False
        if not cls.is_valid_node_group(modifier.node_group): return False
        return True

    @classmethod
    def is_asset_node_group(cls, node_group) -> bool:
        '''Check if node group has appropriate asset asset_name and filepath'''

        weak_ref = node_group.library_weak_reference

        # is not packed, so check id_name
        if weak_ref:
            return bool(weak_ref.id_name.endswith(cls.asset_name))

        # is packed, so also check filename
        # the name is not-user editable but it is not clear for name conflicts
        if node_group.library:
            name = pathlib.Path(node_group.library.filepath).name
            if name != cls.blend_filename: return False

            return node_group.name == cls.asset_name

        return False

    @classmethod
    def builtin_geometry_nodes_path(cls) -> pathlib.Path:
        '''Return OS-specific path to builtin geometry_nodes folder.'''
        ver = f'{bpy.app.version[0]}.{bpy.app.version[1]}'
        path = pathlib.Path(bpy.app.binary_path).resolve().parent # exec folder

        if sys.platform == 'darwin':
            path = path.parent / 'Resources' / ver

        elif sys.platform == 'linux':

            # installed via apt install
            if path.name == 'bin':
                path = path.parent / 'share' / 'blender'
                path_ver = path / ver

                if path_ver.exists():
                    path = path_ver

            else:
                path = path / ver

        else:
            path = path / ver

        path = path / 'datafiles' / 'assets'

        nodes = path / 'nodes'

        if nodes.exists() : return nodes

        return path / 'geometry_nodes'

    @classmethod
    def prop_draw_object_string(cls, modifier, string):
        '''Get object and string for drawing modifier's prop \n
        Returns input modifier and string if string can't be calculated e.g. input modifier of incompatible type'''

        if hasattr(modifier, string): return modifier,  string

        if not cls.prop_draw_map:
            if not cls.is_valid_modifier(modifier): return modifier, string
            cls.prop_draw_map_build(modifier)

        identifier = cls.prop_draw_map.get(string, None)
        if not identifier: return modifier, string

        NodeModifier.validate_id_prop_lookup()

        if ID_PROP_LOOKUP:
            return modifier,  f'["{identifier}"]'

        return getattr(modifier.properties.inputs, identifier),  'value'

    def update_tag(self):
        '''Tag object and UI for update\n
        Setting modifier values doesn't tag object  update and has to be done manually\n'''

        self.modifier.id_data.update_tag()

        for area in bpy.context.screen.areas:
            area.tag_redraw()


    def input_get(self, name: str):
        if ID_PROP_LOOKUP:
            return self.modifier[self.input_map[name]]

        return getattr(self.modifier.properties.inputs, self.input_map[name]).value

    def input_set(self, name: str, val):
        if ID_PROP_LOOKUP:
            self.modifier[self.input_map[name]] = val

            return

        getattr(self.modifier.properties.inputs, self.input_map[name]).value = val

    @classmethod
    def validate_id_prop_lookup(cls):
        '''Check how to handle modifier input and chache result '''
        global ID_PROP_LOOKUP

        if ID_PROP_LOOKUP == 2:
            if 'properties' in bpy.types.NodesModifier.bl_rna.properties:
                ID_PROP_LOOKUP = 0
                cls.str_enum = True

            else:
                ID_PROP_LOOKUP = 1
                cls.str_enum = False

    # Mandatory overloads

    @classmethod
    def is_valid_node_group(cls, node_group) -> bool:
        '''Returns true if node group is compatible with wrapper e.g. I/O matches wrapper's expectation'''

        raise NotImplementedError

    @classmethod
    def get_or_load_node_group(cls):
        '''Get node group from data or load new copy if it's invalid'''

        raise NotImplementedError

    @classmethod
    def calc_asset_path(cls) -> str:
        '''Calculate absolute path to blend file the asset is stored in'''

        raise NotImplementedError



