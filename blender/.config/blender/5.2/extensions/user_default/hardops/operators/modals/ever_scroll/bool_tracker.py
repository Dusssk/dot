import bpy
from .... utility import addon, modifier
from .... utility.base_modal_controls import increment_maps, decrement_maps

from . import States, Auto_Scroll, update_local_view, mods_exit_options, turn_on_coll
from .... utility.collections import unhide_layers


class Bool_Data:
    def __init__(self):
        self.parent_obj_name = ''
        self.mod_name = ''
        self.tracked = False


    def real_obj(self):
        return bpy.data.objects[self.parent_obj_name] if self.parent_obj_name in bpy.data.objects else None


    def real_mod(self):
        obj = self.real_obj()
        if not obj: return None
        return obj.modifiers[self.mod_name] if self.mod_name in obj.modifiers else None


class Recursive_Group:
    def __init__(self):
        self.parent_mod = '' # Selected object mod to stem from
        self.index = 0       # Active Index
        self.bool_datas = []


    def cycle(self, step=0):

        # No datas
        if len(self.bool_datas) <= 0: return

        # Clamp
        self.index += step
        if self.index < 0:
            self.index = len(self.bool_datas) - 1
        elif self.index > len(self.bool_datas) - 1:
            self.index = 0

        # Hide non tracked bools
        self.hide_bool_mods(self.bool_datas[self.index])

        # Reveal Current
        obj, mod = self.get_real_refs(self.bool_datas[self.index])
        if not obj or not mod: return

        mod_obj = modifier.bool_object_get(mod)
        if not mod_obj: return
        obj = mod_obj
        obj.hide_set(False)
        obj.select_set(True)
        bpy.ops.hops.draw_wire_mesh_launcher(object_name=obj.name)


    def hide_bool_mods(self, group):
        for bool_data in self.bool_datas:
            if bool_data.tracked: continue

            obj, mod = self.get_real_refs(bool_data)
            if not obj or not mod: continue

            obj.hide_set(True)
            obj.select_set(False)

            mod_object = modifier.bool_object_get(mod)
            if not mod_object: continue
            mod_object.hide_set(True)
            mod_object.select_set(False)


    def get_real_refs(self, bool_data):
        obj = bool_data.real_obj()
        if not obj: return (None, None)
        mod = bool_data.real_mod()
        if not mod: return (None, None)
        return (obj, mod)


    def get_bool_data(self, index):
        if index > len(self.bool_datas) - 1: return None
        if index < 0: return None
        return self.bool_datas[index]


    def active_bool_data(self):
        if self.index > len(self.bool_datas) - 1: return None
        if self.index < 0: return None
        return self.bool_datas[self.index]


    def set_index(self, index):
        if index > len(self.bool_datas) - 1: return
        if index < 0: return
        self.index = index


    def active_mod(self):
        if self.index > len(self.bool_datas) - 1: return None
        if self.index < 0: return None
        return self.bool_datas[self.index].mod_name


class Recursive_Tracker:
    def __init__(self):
        self.index = 0    # Active Group
        self.groups = []  # Groups
        self.reveal_objects = []


    def setup(self, obj):
        self.index = 0
        self.groups = []
        self.reveal_objects = []

        self.temp_data = []
        rec_filter = set()

        def bool_collect(mod):
            mod_object = modifier.bool_object_get(mod)
            if not mod_object or mod_object in rec_filter:
                return
            else:
                rec_filter.add(mod_object)

            for next_mod in mod_object.modifiers:
                if modifier.mod_type(next_mod) != 'BOOLEAN': continue
                self.temp_data.append((mod_object, next_mod))
                bool_collect(next_mod)

        for mod in obj.modifiers:
            if modifier.mod_type(mod) != 'BOOLEAN': continue

            recursive_group = Recursive_Group()
            recursive_group.parent_mod = mod.name

            self.temp_data = []
            bool_collect(mod)

            for recursive_obj, recursive_mod in self.temp_data:

                if recursive_mod == mod: continue

                bool_data = Bool_Data()
                bool_data.parent_obj_name = recursive_obj.name
                bool_data.mod_name = recursive_mod.name

                recursive_group.bool_datas.append(bool_data)

            self.groups.append(recursive_group)


    def cycle(self, step=0):
        group = self.active_group()
        if not group: return
        group.cycle(step)


    def active_group(self):
        if self.index > len(self.groups) - 1: return None
        if self.index < 0: return None
        return self.groups[self.index]


    def active_mod(self):
        group = self.active_group()
        if not group: return None
        return group.active_mod()


    def set_recursive_index(self, mod):
        for index, group in enumerate(self.groups):
            if group.parent_mod == mod.name:
                self.index = index
                return True
        return False


    def active_mods(self):
        group = self.active_group()
        if not group: return []
        return [bool_data.mod_name for bool_data in group.bool_datas]


    def activate_selected(self, index):
        group = self.active_group()
        if not group: return
        group.set_index(index)
        self.cycle()


    def active_highlight(self, index):
        group = self.active_group()
        if not group: return False
        if index == group.index: return True
        return False


    def show_all_recursive_objs(self, parent_mod):

        if not parent_mod or modifier.mod_type(parent_mod) != 'BOOLEAN':
            bpy.ops.hops.display_notification(info='Unable to show Recursive Booleans')
            return

        if self.reveal_objects:

            group = self.active_group()
            tracked_objs = []
            if group:
                for bool_data in group.bool_datas:
                    if bool_data.tracked:
                        obj = bool_data.real_obj()
                        if obj: tracked_objs.append(obj)

            for obj in self.reveal_objects:
                if obj in tracked_objs: continue
                obj.hide_set(True)
                obj.select_set(False)

        self.reveal_objects = []

        def bool_collect(start_mod):
            if not start_mod.object: return
            for mod in start_mod.object.modifiers:
                bool_obj = modifier.bool_object_get(mod)
                if bool_obj:
                    self.reveal_objects.append(bool_obj)
                    bool_collect(mod)

        bool_collect(parent_mod)

        if not self.reveal_objects:
            bpy.ops.hops.display_notification(info='No recursive objects to show')
            return

        for obj in self.reveal_objects:
            obj.hide_set(False)
            obj.select_set(True)

        bpy.ops.hops.display_notification(info=f'Revealed {len(self.reveal_objects)} booleans')


    def selection_to_tracked(self, index):
        group = self.active_group()
        if not group: return

        bool_data = group.bool_datas[index]
        obj, mod = group.get_real_refs(bool_data)
        if not obj or not mod: return

        bool_obj = modifier.bool_object_get(mod)

        if bool_data.tracked:
            bool_data.tracked = False
            if bool_obj:
                obj = bool_obj
                obj.hide_set(True)
                obj.select_set(False)

        else:
            bool_data.tracked = True
            if bool_obj:
                obj = bool_obj
                obj.hide_set(False)
                obj.select_set(True)
                bpy.ops.hops.draw_wire_mesh_launcher(object_name=obj.name)


    def tracked_highlight(self, index):
        group = self.__group_with_index_check(index)
        if not group: return False
        return group.bool_datas[index].tracked


    def tracked_img_key_update(self, index):
        group = self.__group_with_index_check(index)
        if not group: return 'eyecon_closed'
        if group.bool_datas[index].tracked: return 'eyecon_open'
        return 'eyecon_closed'


    def bool_toggle(self, index):
        group = self.active_group()
        if not group: return False
        bool_data = group.get_bool_data(index)
        mod = bool_data.real_mod()
        if not mod: return
        mod.show_viewport = not mod.show_viewport


    def bool_show_view_highlight(self, index):
        group = self.active_group()
        if not group: return False
        bool_data = group.get_bool_data(index)
        mod = bool_data.real_mod()
        if not mod: return False
        if mod.show_viewport: return False
        return True


    def __group_with_index_check(self, index):
        group = self.active_group()
        if not group: return None
        if index > len(group.bool_datas) - 1: return None
        if index < 0: return None
        return group


    def apply_to(self, context, root_obj):
        group = self.active_group()
        if not group: return
        index = group.index

        reset_active = context.view_layer.objects.active

        for i, bool_data in enumerate(group.bool_datas):
            obj = bool_data.real_obj()
            if not obj: continue
            mod = bool_data.real_mod()
            if not mod: continue

            context.view_layer.objects.active = obj

            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
                bpy.ops.hops.display_notification(info=f'Applied : {mod.name}')
            except: pass

            if i == group.index:
                context.view_layer.objects.active = reset_active
                break

        self.setup(root_obj)


class Bool_Tracker:
    def __init__(self):
        self.all_mods = []
        self.bools = []
        self.tracked_bools = [] # Appended bools to end selction
        self.index = 0
        self.current_mod = None
        self.auto_scroll_sequance_begin = False

        self.protected_additive = []

        # Recursive
        self.recursive = Recursive_Tracker()
        self.recursive_active = False
        self.r_mods = []

        self.help = [
        ("CTRL",         "HOPStool Dots"),
        ("W",            "Show wire fade for object"),
        ("A",            "Add / Remove bool to visibility set"),
        ("Alt A",        "Reveal All"),
        ("Shift A",       "Hide All"),
        #("F",            "Apply modifier to mesh"),
        ("R",            "Start Recursive Scroll"),
        ("Shift R",      "Stop Recursive Scroll"),
        ("S",            "Show Recursive Booleans"),
        ("Shift F",      "Apply modifiers up to current"),
        ("V",            "Toggle modifier visibility"),
        ("Shift V",      "Toggle all modifier visibility"),
        ("Shift Scroll", "Move modifiers")]


    def update_data(self, context, obj):
        self.all_mods = []
        self.bools = []
        self.tracked_bools = []
        self.index = 0

        # Setup recursive
        self.recursive.setup(obj)

        self.protected_additive = []
        if addon.preference().property.bool_scroll == 'ADDITIVE':
            for mod in obj.modifiers:

                bool_object = modifier.bool_object_get(mod)

                if valid_bool_obj(context, bool_object):
                    if bool_object.visible_get():
                        self.protected_additive.append(mod)

        main_coll = obj.users_collection[0]

        objs = []
        for mod in obj.modifiers:
            self.all_mods.append(mod)
            if mod in self.protected_additive: continue

            if modifier.mod_type(mod) == 'BOOLEAN':
                self.bools.append(mod)

                bool_object = modifier.bool_object_get(mod)

                if valid_bool_obj(context, bool_object):
                    objs.append(bool_object)

        objs = list(set(objs))

        filtered = []
        colls = [o.users_collection[0] for o in objs if len(o.users_collection) > 0]
        for obj in objs:
            obj.hide_viewport = False
            if obj.name in context.view_layer.objects:
                obj.hide_set(True)

            if not obj.users_collection: continue
            if obj.users_collection[0] != colls:
                filtered.append(obj)

        if addon.preference().property.bool_scroll == 'ADDITIVE':
            for obj in filtered: unhide_layers(obj)

        else:
            cache = set()

            for obj in filtered:
                unhide_layers(obj)

                for coll in obj.users_collection:
                    if coll != main_coll:
                        if coll in cache: continue
                        cache.add(coll)

                    for object in coll.objects:
                        if object.display_type == 'WIRE':
                            if object.hide_viewport:
                                object.hide_viewport = False
                            if not object.hide_get():
                                object.hide_set(True)

        if self.bools:
            self.index = len(self.bools) -1
            self.current_mod = self.bools[self.index]
        else:
            self.current_mod = None

        # Local mode support
        if context.space_data.local_view:

            def obj_set_hide(mod):
                obj = modifier.bool_object_get(mod)
                if not obj: return

                return (obj, obj.select_get(), obj.hide_get())


            bools = [obj_set_hide(mod) for mod in self.bools if modifier.bool_object_get(mod)]
            bools = [itm for itm in bools if itm[0].name in context.view_layer.objects]
            protected = [obj_set_hide(mod) for mod in self.protected_additive if modifier.bool_object_get(mod)]
            visible = [(o, o.select_get(), False) for o in context.visible_objects]
            objects = bools + visible + protected
            bpy.ops.view3d.localview(frame_selected=False)
            bpy.ops.object.select_all(action='DESELECT')

            for obj, *_ in objects:
                obj.hide_set(False)
                obj.select_set(True)

            bpy.ops.view3d.localview(frame_selected=False)

            for obj, select, hide in objects:
                obj.hide_set(hide)
                obj.select_set(select)

        # Additive : turn_on_coll will hide all objects that are using wire
        # Its best to not mess with this and just turn on whats needed after
        for mod in self.protected_additive:
            bool_object = modifier.bool_object_get(mod)
            if bool_object:
                bool_object.hide_set(False)

        # Select first
        self.cycle_bools(context, step=0)



    def cycle_bools(self, context, step=0):
        if len(self.bools) == 0: return

        self.auto_scroll_sequance_begin = False

        if addon.preference().property.modal_handedness == 'RIGHT':
            step *= -1

        for mod in self.bools:
            bool_obj = modifier.bool_object_get(mod)
            if valid_bool_obj(context, bool_obj):
                if bool_obj not in self.tracked_bools:
                    bool_obj.hide_set(True)
                    bool_obj.select_set(False)

        # Recursive bool scroll
        if self.recursive_active:
            self.recursive.cycle(step)
            return

        self.index += step
        if self.index < 0:
            self.index = len(self.bools) - 1
        elif self.index > len(self.bools) - 1:
            self.index = 0
            self.auto_scroll_sequance_begin = True

        mod = self.bools[self.index]

        self.current_mod = mod

        bool_obj = modifier.bool_object_get(mod)

        if valid_bool_obj(context, bool_obj):
            bool_obj.hide_set(False)
            bool_obj.select_set(True)
            bpy.ops.hops.draw_wire_mesh_launcher(object_name=bool_obj.name)

    # --- OPERATIONS --- #

    def event_update(self, op, context, event, obj):

        # Visible toggle
        if event.type == 'V' and event.value == 'PRESS':
            if event.shift:
                self.toggle_all_visible()
            else:
                self.toggle_visible()

        # Apply current
        elif event.type == 'F' and event.value == 'PRESS':
            if event.shift:
                self.recursive.apply_to(context, obj)
            else:
                self.apply_current(obj)
                self.update_data(context, obj)
            op.alter_form_layout(context)

        # Append bool object to tracked / All Visible
        elif event.type == 'A' and event.value == 'PRESS':
            if event.shift:
                self.hide_all_objs()
            elif event.alt:
                self.reveal_all_objs()
            else:
                self.add_current_to_tracked()

        # Wire display current
        elif event.type == 'W' and event.value == 'PRESS':
            self.wire_display_current()

        # Start recursive
        elif event.type == 'R' and event.value == 'PRESS':
            if event.shift:
                self.stop_recursive(context, op)
                op.alter_form_layout(context)
            else:
                if self.has_recursive_mods(self.current_mod):
                    self.start_recursive(obj, context, op)
                    op.alter_form_layout(context)
                else: bpy.ops.hops.display_notification(info='No Recursive Booleans found')

        # Show Recursive Bools
        elif event.type == 'S' and event.value == 'PRESS':
            if not event.ctrl:
                self.recursive.show_all_recursive_objs(self.current_mod)

        # Shift mods
        if event.shift and event.value == 'PRESS':
            if event.type in increment_maps:
                self.move_mod(obj, direction=1)
                op.alter_form_layout(context)
            elif event.type in decrement_maps:
                self.move_mod(obj, direction=-1)
                op.alter_form_layout(context)


    def toggle_visible(self):
        if self.current_mod:
            self.current_mod.show_viewport = not self.current_mod.show_viewport


    def toggle_all_visible(self):
        if self.bools:
            show = not any([m.show_viewport for m in self.bools])
            for mod in self.bools:
                mod.show_viewport = show
            msg = "On" if show else "Off"
            bpy.ops.hops.display_notification(info=f"Visible : {msg}")


    def reveal_all_objs(self):
        for mod in self.bools:
            bool_obj = modifier.bool_object_get(mod)
            if valid_bool_obj(bpy.context, bool_obj):
                bool_obj.hide_set(False)

        self.tracked_bools = [modifier.bool_object_get(m) for m in self.bools if modifier.bool_object_get(m)]


    def hide_all_objs(self):
        for mod in self.bools:
            bool_object = modifier.bool_object_get(mod)
            if valid_bool_obj(bpy.context, bool_object):
                bool_object.hide_set(True)
        self.tracked_bools = []

        if not self.current_mod: return

        bool_object = modifier.bool_object_get(mod)
        if valid_bool_obj(bpy.context, bool_object):
            bool_object.hide_set(False)


    def add_current_to_tracked(self):
        if not self.current_mod: return

        bool_object = modifier.bool_object_get(self.current_mod)
        if not valid_bool_obj(bpy.context, bool_object): return

        # Regular modal option
        if bool_object not in self.tracked_bools:
            self.tracked_bools.append(bool_object)
            bpy.ops.hops.draw_wire_mesh_launcher(object_name=bool_object.name)
            bpy.ops.hops.display_notification(info='Bool appended to visibility')
            bool_object.hide_set(False)
        else:
            self.tracked_bools.remove(bool_object)
            bpy.ops.hops.draw_wire_mesh_launcher(object_name=bool_object.name)
            bpy.ops.hops.display_notification(info='Bool removed from visibility')
            bool_object.hide_set(True)


    def add_selected_to_tracked(self, obj, mod_name=''):
        mod = obj.modifiers.get(mod_name, None)
        if not mod: return

        bool_object = modifier.bool_object_get(mod)
        if not valid_bool_obj(bpy.context, bool_object): return

        if bool_object not in self.tracked_bools:
            self.tracked_bools.append(bool_object)
            bpy.ops.hops.draw_wire_mesh_launcher(object_name=bool_object.name)
            bpy.ops.hops.display_notification(info='Bool appended to visibility')
            bool_object.hide_set(False)
        else:
            self.tracked_bools.remove(bool_object)
            bpy.ops.hops.draw_wire_mesh_launcher(object_name=bool_object.name)
            bpy.ops.hops.display_notification(info='Bool removed from visibility')
            bool_object.hide_set(True)


    def apply_current(self, obj):
        if self.current_mod:
            # Remove from tracked
            bool_object = modifier.bool_object_get(self.current_mod)
            if bool_object:
                if self.current_mod.object in self.tracked_bools:
                    self.tracked_bools.remove(bool_object)
            try:
                bpy.ops.object.modifier_apply(modifier=self.current_mod.name)
            except:
                obj.modifiers.remove(self.current_mod)


    def apply_to(self, obj, context):
        if not self.current_mod: return

        if self.recursive_active:
            self.recursive.apply_to(context)
            return

        count = 0
        target_name = self.current_mod.name
        for mod in obj.modifiers:
            count += 1
            cut_off_name = mod.name

            if mod in self.protected_additive:
                self.protected_additive.remove(mod)

            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except:
                obj.modifiers.remove(mod)

            if target_name == cut_off_name: break
        bpy.ops.hops.display_notification(info=f'{count} modifiers applied')


    def move_mod(self, obj, direction=0):
        if not self.current_mod: return
        if direction > 0:
            bpy.ops.object.modifier_move_up(modifier=self.current_mod.name)
        elif direction < 0:
            bpy.ops.object.modifier_move_down(modifier=self.current_mod.name)

        if self.current_mod:
            self.all_mods = []
            self.bools = []
            for mod in obj.modifiers:
                self.all_mods.append(mod)
                if modifier.mod_type(mod) == 'BOOLEAN':
                    if mod in self.protected_additive: continue
                    self.bools.append(mod)
            if self.current_mod in self.bools:
                self.index = self.bools.index(self.current_mod)


    def wire_display_current(self):
        if not self.current_mod: return

        bool_object = modifier.bool_object_get(self.current_mod)

        if not valid_bool_obj(bpy.context, bool_object): return
        bpy.ops.hops.draw_wire_mesh_launcher(object_name=bool_object.name)


    def exit_tracker(self, context, select_all=False):
        active = context.active_object
        bpy.ops.object.select_all(action='DESELECT')

        # Select all visible if hops dot was used
        if select_all:
            for mod in self.bools:
                bool_object = modifier.bool_object_get(mod)

                if not valid_bool_obj(bpy.context, bool_object): continue
                if bool_object.hide_get(): continue
                bool_object.select_set(True)

        if not self.current_mod: return

        current_bool_object = modifier.bool_object_get(self.current_mod)

        # No mod to set as the active : restore active
        if not current_bool_object:
            context.view_layer.objects.active = active
            return

        # Set current mod obj as active
        if not valid_bool_obj(bpy.context, current_bool_object): return
        current_bool_object.select_set(True)
        context.view_layer.objects.active = current_bool_object
        current_bool_object.hide_set(False)

    # --- RECURSIVE --- #

    def start_recursive(self, obj, context, op):

        self.recursive_active = False

        if not self.current_mod or modifier.mod_type(self.current_mod) != 'BOOLEAN':
            bpy.ops.hops.display_notification(info='Unable to begin Recursive Booleans')

        if self.recursive.set_recursive_index(self.current_mod):
            self.recursive_active = True
            bpy.ops.hops.display_notification(info='Started Recursive Scroll')
        else:
            bpy.ops.hops.display_notification(info='No Recursive Booleans found')


    def stop_recursive(self, context, op):
        self.recursive_active = False
        op.late_update = True

    # --- FORM --- #

    def make_selected_active(self, index=0, additive=False):
        if index < len(self.bools):
            if index < 0: index = 0
            self.index = index
            self.current_mod = self.bools[self.index]

            current_mod_object = modifier.bool_object_get(self.current_mod)

            if current_mod_object:
                for mod in self.bools:
                    bool_object = modifier.bool_object_get(mod)

                    if bool_object:
                        if bool_object not in self.tracked_bools:
                            if valid_bool_obj(bpy.context, bool_object):
                                bool_object.hide_set(True)

                if bool_mod_valid_obj(bpy.context, mod):
                    current_mod_object.hide_set(False)
                    bpy.ops.hops.draw_wire_mesh_launcher(object_name=current_mod_object.name)

        if additive:
            self.add_current_to_tracked()


    def highlight(self, index=None):
        if index == None: return
        if index == self.index: return True
        return False


    def bool_toggle(self, obj, mod_name=''):
        if mod_name not in obj.modifiers: return
        mod = obj.modifiers[mod_name]
        mod.show_viewport = not mod.show_viewport


    def bool_show_view_highlight(self, obj, mod_name=''):
        if mod_name not in obj.modifiers: return False
        mod = obj.modifiers[mod_name]
        if mod.show_viewport: return False
        return True


    def bool_tracked_highlight(self, obj, mod_name=''):
        mod = obj.modifiers.get(mod_name, None)
        if not mod: return False

        mod_object = modifier.bool_object_get(mod)

        return mod_object and mod_object in self.tracked_bools


    def bool_tracked_img_key_update(self, obj, mod_name=''):
        if self.bool_tracked_highlight(obj, mod_name):
            return 'eyecon_open'
        return 'eyecon_closed'


    def apply_mods_form(self, context, op, mod_name='', up_to=False):
        obj = op.obj
        if mod_name not in obj.modifiers: return
        mod = obj.modifiers[mod_name]
        apply_mod = mod

        if up_to:
            count = 0
            for mod in obj.modifiers:
                count += 1
                should_break = True if mod.name == apply_mod.name else False
                try:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                except:
                    obj.modifiers.remove(mod)
                if should_break: break
            bpy.ops.hops.display_notification(info=f'{count} modifiers applied')
        else:
            try:
                name = apply_mod.name
                bpy.ops.object.modifier_apply(modifier=apply_mod.name)
                bpy.ops.hops.display_notification(info=f'Applied : {name}')
            except:
                obj.modifiers.remove(apply_mod)

        # Rebuild Form / Update Data
        self.update_data(context, obj)
        op.alter_form_layout(context)


    def has_recursive_mods(self, mod):
        if not mod: return False

        bool_object = modifier.bool_object_get(mod)
        if not bool_object: return False
        for mod in bool_object.modifiers:
            bool_object = modifier.bool_object_get(mod)
            if bool_object: return True
        return False


    def select_start_recursive(self, context, op, index):
        self.make_selected_active(index)
        self.start_recursive(op.obj, context, op)
        op.late_update = True


    def isolate_mod(self, mod):
        self.current_mod = mod
        self.recursive_active = False

        for index, mod in enumerate(self.bools):
            bool_object = modifier.bool_object_get(mod)

            if mod == self.current_mod:
                mod.show_viewport = True
                self.index = index
                if valid_bool_obj(bpy.context, bool_object):
                    bool_object.hide_set(False)
            else:
                mod.show_viewport = False
                if valid_bool_obj(bpy.context, bool_object):
                    if bool_object not in self.tracked_bools:
                        bool_object.hide_set(True)

    # --- FAS --- #

    def FAS_data(self):
        data = ['Boolean']

        if self.recursive_active:
            data = ['Recursive', self.recursive.active_mod()]
            return data

        if self.current_mod:
            if self.all_mods and self.current_mod in self.all_mods:
                index = self.all_mods.index(self.current_mod) + 1
                data.append(index)
            data.append(self.current_mod.name)

            bool_object = modifier.bool_object_get(self.current_mod)

            if bool_object:
                data.append(bool_object.name)

        return data

# --- UTILS --- #

def bool_mod_valid_obj(context, mod):
    object = modifier.bool_object_get(mod)

    return valid_bool_obj(context, object)

def valid_bool_obj(context, object):
    if not object: return False

    return context.scene in object.users_scene