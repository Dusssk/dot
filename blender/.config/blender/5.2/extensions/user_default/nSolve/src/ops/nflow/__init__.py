import time
import math
import json
import ast
import os
import glob
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector, Matrix

from ....icons.menus import get_icon_id

from .common import *
from . import behaviors


class NSOLVE_OT_NFlow(bpy.types.Operator):
    bl_idname = 'nsolve.nflow'
    bl_label = 'nFlow'
    bl_options = {'BLOCKING', 'INTERNAL'}

    invoke_mode: bpy.props.EnumProperty(name='Invoke mode', description='',
        items=[
            ('HOVER', 'Hover', ''),
            ('BEGIN', 'Begin', ''),
        ],
        default='HOVER',
    )

    number_key_to_index = {
        'ONE': 0,
        'TWO': 1,
        'THREE': 2,
        'FOUR': 3,
        'FIVE': 4,
        'SIX': 5,
        'SEVEN': 6,
        'EIGHT': 7,
        'NINE': 8,
        'ZERO': 9,
    }

    @classmethod
    def poll(cls, context):
        return (context.area.type == 'VIEW_3D') and (context.mode in ('OBJECT', 'EDIT_MESH'))

    def invoke(self, context, event):
        # Make sure we start afresh
        EditableMeshes.clear()
        # But we DO need stable bmesh references during a behavior operation
        EditableMeshes.keep = True
        
        result = {'PASS_THROUGH'}
        
        try:
            result = self._invoke(context, event)
        finally:
            if 'RUNNING_MODAL' not in result:
                EditableMeshes.keep = False
                EditableMeshes.clear()
        
        return result

    def _invoke(self, context, event):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        space_data = context.space_data
        if context.screen.show_fullscreen:
            context.space_data.show_region_tool_header = True
        
        if not behavior_presets_config.is_initialized:
            NFlowBehaviorPresetsConfig.initialize()
            # Assign True in any case, to make sure it's processed only once
            behavior_presets_config.is_initialized = True
        
        if not nflow_config_workspace.is_initialized:
            nflow_config_workspace.initialize()
        
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        
        NFlow.display_region = context.region
        NFlow.display_mouse_pos = mouse_pos
        
        NFlow.ui_cheatsheet = None
        
        if not nflow_config_workspace.enable:
            self.update_display_info(context, None)
            return {'PASS_THROUGH'}
        
        if NFlowPrefs.get('behavior_preset_scroll_enable'):
            if event.type in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'LEFT_ARROW', 'RIGHT_ARROW'):
                mods = NFlowPrefs.get('behavior_preset_scroll_modifiers')
                if all(getattr(event, mod) == (mod in mods) for mod in ('shift', 'ctrl', 'alt')):
                    if 'ARROW' in event.type:
                        scroll_dir = (1 if 'RIGHT' in event.type else -1)
                    else:
                        scroll_dir = (1 if 'UP' in event.type else -1)
                        if NFlowPrefs.get('behavior_preset_scroll_invert'):
                            scroll_dir = -scroll_dir
                    self.scroll_preset(context, scroll_dir=scroll_dir)
                    return {'FINISHED'}
        
        if NFlowPrefs.get('behavior_preset_use_number_shortcuts'):
            if not (event.alt or event.ctrl or event.shift or event.oskey):
                preset_index = self.number_key_to_index.get(event.type)
                if preset_index is not None:
                    self.scroll_preset(context, index=preset_index)
                    return {'FINISHED'}
        
        behavior_preset = behavior_presets_config.get_active_preset()
        
        event_arg = dict(type=event.type, shift=event.shift, ctrl=event.ctrl, alt=event.alt)
        if event.type not in ('LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE'):
            event_arg['type'] = None
        
        elem_types = NFlow.gather_element_types(behavior_preset, context, event_arg)
        
        obj, bm, elem_type, elements = NFlow.detect_closest_element(context, mouse_pos, elem_types)
        
        full_name = not NFlowPrefs.get('behavior_shorten_name')
        event_types = NFlow.gather_event_types(behavior_preset,
            elem_type, elements, context, event_arg, full_name)
        
        help_text_show_all = NFlowPrefs.get('help_text_show_all')
        if help_text_show_all == 'MODIFIERS':
            all_shortcuts = not (event.shift or event.ctrl or event.alt)
        else:
            all_shortcuts = (help_text_show_all != 'RELEVANT')
        all_contexts = (help_text_show_all == 'ALL')
        
        preset_name = (behavior_preset.name if behavior_preset else '')
        all_event_arg = (None if all_shortcuts else event_arg)
        all_context = (None if all_contexts else context)
        all_event_types = NFlow.gather_event_types(behavior_preset,
            None, None, all_context, all_event_arg, full_name)
        preset_cheatsheet = self.format_event_types(all_event_types, True)
        help_text = '\n\n'.join(item for item in [preset_name, preset_cheatsheet] if item)
        
        self.invoke_event_type = event.type
        self.cancel_event_types = get_cancel_event_types(event)
        self.event_type_start = event.type
        self.elem_type_start = elem_type
        self.behavior_type_start = None
        self.behavior = None
        self.operator = None
        self.kwargs = None
        self.selection_helper = None
        self.is_modal_selection = False
        self.cursor_matrix = None
        self.help_text = ''
        
        behavior_info = NFlow.get_behavior(behavior_preset,
            elem_type, elements, context, event_arg, full_name=full_name)
        
        NFlow.ui_cheatsheet = {'infos': all_event_types, 'active': None}
        
        if behavior_info:
            self.update_display_info(context, behavior_info, event_types, help_text=help_text)
            
            self.kwargs = behavior_info.get('kwargs')
            
            self.operator = behavior_info.get('operator')
            
            if self.invoke_mode == 'BEGIN':
                NFlow.ui_cheatsheet['active'] = behavior_info
                
                self.cursor_matrix = Matrix(context.scene.cursor.matrix)
                if behavior_info['cursor_3d_snap']:
                    Cursor3DHelper.snap(context, mouse_pos, obj, elements)
                
                self.preferred_element_selection = behavior_info.get('ensure_element_selection', set())
                self.ensure_element_selection(context)
            
            if self.operator is not None:
                if self.invoke_mode == 'BEGIN':
                    self.update_display_info(context, None)
                    
                    self.select_push_undo = behavior_info['select_push_undo']
                    
                    self.selection_helper = SelectionHelper(behavior_info)
                    
                    if context.mode == 'OBJECT':
                        self.selection_helper.init_object(context, mouse_pos)
                    
                    if behavior_info['select_after']:
                        if context.mode == 'EDIT_MESH':
                            self.selection_helper.init_mesh(context, mouse_pos,
                                obj, bm, elem_type, elements)
                        
                        self.update_active_behavior_help_text(preset_name, behavior_info)
                        
                        self.is_modal_selection = True
                        context.window_manager.modal_handler_add(self)
                        return {'RUNNING_MODAL'}
                    
                    if (context.mode == 'EDIT_MESH') and bm:
                        self.selection_helper.use_update_highlight = False
                        self.selection_helper.init_mesh(context, mouse_pos,
                            obj, bm, elem_type, elements)
                    
                    result = self.invoke_operator(self.operator)
                    
                    if 'RUNNING_MODAL' in result:
                        self.update_active_behavior_help_text(preset_name, behavior_info)
                    
                    return ({'FINISHED'} if 'CANCEL' not in result else result)
            else:
                self.behavior_type_start = behavior_info['type']
                self.behavior = behavior_info['type']()
                self.behavior.use_post_select_elements = behavior_info['select_after']
                self.behavior.post_select_mode = behavior_info['selection_mode']
                self.behavior.selection_helper = SelectionHelper(behavior_info)
                
                for name, value in behavior_info.get('options', {}).items():
                    setattr(self.behavior, name, value)
        else:
            self.update_display_info(context, None, help_text=help_text)
        
        result = None
        
        if self.behavior:
            self.behavior.initialize(context, event)
            self.behavior.set_target(obj, bm, elem_type, elements)
            
            with self.behavior.raycaster:
                if self.invoke_mode == 'HOVER':
                    result = self.behavior.hover(context, event)
                    if self.behavior.hover_text:
                        NFlow.hover_text += f'\n\n{self.behavior.hover_text}'
                    if result:
                        return {'CANCELLED'} # consume the event
                    result = None # make sure no cleanup logic is executed
                elif self.invoke_mode == 'BEGIN':
                    result = self.behavior.invoke(context, event)
                    # Some behaviors can switch from Object to Edit mode
                    self.ensure_element_selection(context)
        
        if result == 'RUNNING_MODAL':
            self.update_active_behavior_help_text(preset_name, behavior_info)
            context.window_manager.modal_handler_add(self)
        elif result is not None:
            if self.behavior:
                self.behavior.cleanup(context)
            
            if result == 'FINISHED':
                if self.behavior.undo_message:
                    bpy.ops.ed.undo_push(message=self.behavior.undo_message)
                
                # E.g. to highlight the newly created element
                NFlow.detect_closest_element(context, mouse_pos)
        
        return {result or 'PASS_THROUGH'}

    def modal(self, context, event):
        result = {'CANCELLED'}
        
        try:
            result = self._modal(context, event)
        finally:
            if ('CANCELLED' in result) or ('FINISHED' in result):
                EditableMeshes.keep = False
                EditableMeshes.clear()
        
        return result

    def _modal(self, context, event):
        if self.is_modal_selection:
            return self.modal_select(context, event)
        return self.modal_behavior(context, event)

    def modal_select(self, context, event):
        context.area.tag_redraw()
        
        if event.type == 'MOUSEMOVE':
            self.selection_helper.on_mousemove(context, event)
        elif event.type in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE'):
            self.selection_helper.on_wheel(context, event)
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            self.update_display_info(context, None)
            result = self.invoke_operator(self.operator)
            return ({'FINISHED'} if 'CANCEL' not in result else result)
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.update_display_info(context, None)
            self.selection_helper.on_cancel(context)
            Cursor3DHelper.set_matrix(context.scene.cursor, self.cursor_matrix)
            self.on_cancel(context)
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}

    def modal_behavior(self, context, event):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        event_arg = dict(type=self.event_type_start, shift=event.shift, ctrl=event.ctrl, alt=event.alt)
        elem_type = self.elem_type_start
        
        behavior_preset = behavior_presets_config.get_active_preset()
        behavior_info = NFlow.get_behavior(behavior_preset, elem_type, None, context, event_arg)
        if behavior_info and (behavior_info.get('type') == self.behavior_type_start):
            for name, value in behavior_info.get('options', {}).items():
                if name not in self.behavior.overridden_options:
                    setattr(self.behavior, name, value)
        
        self.behavior.editors.update_matrices()
        
        if (event.type == nflow_config_workspace.snap_key) and (event.value in ('PRESS', 'RELEASE')):
            current_time = time.time()
            ignore_time = context.preferences.inputs.mouse_double_click_time / 1000.0
            if current_time > self.behavior.snap_time_last + ignore_time:
                self.behavior.snap_time_last = current_time
                self.behavior.use_snap = not self.behavior.use_snap
        
        help_text = self.help_text
        if self.behavior.use_snap:
            help_text += '\n\n' + 'Snap: ON'
        NFlow.help_text = help_text
        
        error = None
        with self.behavior.raycaster:
            try:
                result = self.behavior.modal(context, event)
            except Exception as exc:
                result = 'CANCELLED'
                error = exc
        
        if result in ('FINISHED', 'CANCELLED'):
            self.modal_cleanup(context, finished=(result == 'FINISHED'))
        else:
            status_items = [self.behavior.status_text]
            
            if 'SNAP' in self.behavior.capabilities:
                snap_key = event_key_map_names.get(nflow_config_workspace.snap_key)
                if snap_key:
                    status_items.append(f'{snap_key}: snap')
            
            status_text = ', '.join(item for item in status_items if item)
            context.workspace.status_text_set(status_text or None)
        
        if error is not None:
            raise error
        
        if (result == 'FINISHED') and self.behavior.undo_message:
            bpy.ops.ed.undo_push(message=self.behavior.undo_message)
        
        if result == 'FINISHED':
            # E.g. to highlight the newly created element
            mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            NFlow.detect_closest_element(context, mouse_pos)
        
        context.area.tag_redraw()
        
        return {result or 'RUNNING_MODAL'}

    def modal_cleanup(self, context, finished):
        self.behavior.cleanup(context)
        
        context.workspace.status_text_set(None)
        
        if not finished:
            Cursor3DHelper.set_matrix(context.scene.cursor, self.cursor_matrix)
            self.on_cancel(context)
            self.behavior.editors.revert()

    def on_cancel(self, context):
        if context.mode == 'EDIT_MESH':
            prev_select_mode = getattr(self, 'prev_select_mode', None)
            if prev_select_mode is not None:
                context.tool_settings.mesh_select_mode = prev_select_mode

    def invoke_operator(self, op, undo='YES'):
        # This is necessary to avoid crashes in some circumstances
        self.selection_helper.cleanup()
        
        if self.select_push_undo:
            bpy.ops.ed.undo_push(message='Select')
        
        try:
            kwargs = self.kwargs or {}
            result = op('INVOKE_DEFAULT', (undo == 'YES'), **kwargs)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        
        if (undo == 'FORCE') and ('FINISHED' in result):
            bpy.ops.ed.undo_push(message=op.get_rna_type().name)
        
        return result

    def update_active_behavior_help_text(self, preset_name, behavior_info):
        active_event_types = [{
            'event': behavior_info['entry'].event,
            'modifiers': behavior_info['entry'].modifiers,
            'name': behavior_info['name'],
        }]
        preset_cheatsheet = self.format_event_types(active_event_types, True)
        help_text = '\n\n'.join(item for item in [preset_name, preset_cheatsheet] if item)
        
        self.help_text = help_text
        
        NFlow.hover_text = ''
        NFlow.help_text = help_text

    def update_display_info(self, context, behavior_info, event_types=None, help_text=''):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        NFlow.help_text = help_text
        
        if behavior_info:
            if NFlowPrefs.get('use_specialized_cursors'):
                context.window.cursor_modal_set(behavior_info.get('cursor', 'DEFAULT'))
            context.workspace.status_text_set(self.get_event_types_draw_func(event_types))
            NFlow.hover_text = self.format_event_types(event_types, False) or behavior_info['name']
            NFlow.show_highlight = bool(behavior_info.get('highlight'))
        else:
            context.window.cursor_modal_restore()
            context.workspace.status_text_set(None)
            NFlow.hover_text = ''
            NFlow.show_highlight = False
            NFlow.cleanup()
        
        context.area.tag_redraw()

    def format_event_types(self, event_types, include_modifiers):
        if not event_types:
            return ''
        
        event_type_map = {'LEFTMOUSE': 'LMB', 'MIDDLEMOUSE': 'MMB', 'RIGHTMOUSE': 'RMB'}
        
        lines = []
        
        for event_type_info in event_types:
            event_type = event_type_info['event']
            modifiers = event_type_info['modifiers']
            name = event_type_info['name']
            
            event_type = event_type_map.get(event_type, '?')
            if include_modifiers:
                modifiers = sorted(mod.capitalize() for mod in modifiers)
                event_type = '+'.join(modifiers + [event_type])
            lines.append(f'{event_type}: {name}')
        
        # if include_modifiers:
        #     lines.sort()
        
        return '\n'.join(lines)

    def get_event_types_draw_func(self, event_types):
        if not event_types:
            return None
        
        event_type_map = {'LEFTMOUSE': 'MOUSE_LMB', 'MIDDLEMOUSE': 'MOUSE_MMB', 'RIGHTMOUSE': 'MOUSE_RMB'}
        
        labels = []
        
        for event_type_info in event_types:
            event_type = event_type_info['event']
            modifiers = event_type_info['modifiers']
            name = event_type_info['name']
            
            icon = event_type_map.get(event_type, 'QUESTION')
            labels.append({'text': name, 'icon': icon})
        
        def draw(header, context):
            layout = header.layout
            for label in labels:
                layout.label(**label)
        
        return draw

    def scroll_preset(self, context, index=None, scroll_dir=0):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        behavior_presets = behavior_presets_config.behavior_presets
        if len(behavior_presets) == 0:
            return
        
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        if index is None:
            index = behavior_presets_config.clamp_active_index()
            index = (index + scroll_dir) % len(behavior_presets)
        behavior_presets_config.behavior_preset_active = index
        
        context.area.tag_redraw()

    def ensure_element_selection(self, context):
        preferred_element_selection = getattr(self, 'preferred_element_selection', None)
        
        if preferred_element_selection is None:
            return
        
        if context.mode == 'EDIT_MESH':
            self.prev_select_mode = tuple(context.tool_settings.mesh_select_mode)
            
            if 'ADDITIVE' in preferred_element_selection:
                select_mode = list(self.prev_select_mode)
            else:
                select_mode = [False, False, False]
            
            select_mode[0] |= ('VERT' in preferred_element_selection)
            select_mode[1] |= ('EDGE' in preferred_element_selection)
            select_mode[2] |= ('FACE' in preferred_element_selection)
            
            context.tool_settings.mesh_select_mode = tuple(select_mode)
            
            self.preferred_element_selection = None # ensure selection only once


class NSOLVE_OT_NFlow_Shrinkwrap(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_shrinkwrap'
    bl_label = 'Shrinkwrap'
    bl_description = '\n'.join([
        'Snap/project the edited/selected mesh(es) on the target or nearest object',
        '(Click: visible vertices only, Ctrl+Click: selected vertices only, Shift+Click: all vertices)',
    ])
    bl_options = {'REGISTER', 'UNDO'}

    wrap_method: bpy.props.EnumProperty(name='Wrap method', description='Wrap method',
        items=[
            ('NEAREST_SURFACEPOINT', 'Nearest (surface)', 'Snap to the nearest target surface'),
            ('NEAREST_VERTEX', 'Nearest (vertex)', 'Snap to the nearest target vertex'),
            ('PROJECT', 'Project (self normals)', 'Project along the edited mesh\'s normals'),
            ('TARGET_PROJECT', 'Project (target normals)', 'Project along target\'s interpolated vertex normals'),
        ],
        default='NEAREST_SURFACEPOINT',
    )

    which: bpy.props.EnumProperty(name='Which vertices', description='Which vertices',
        items=[
            ('CONTEXT', 'Context', 'Context'),
            ('ALL', 'All', 'All'),
            ('VISIBLE', 'Visible', 'Visible'),
            ('SELECTED', 'Selected', 'Selected'),
        ],
        default='SELECTED',
    )

    @classmethod
    def poll(cls, context):
        return context.mode in ('OBJECT', 'EDIT_MESH')

    def invoke(self, context, event):
        if self.which == 'CONTEXT':
            if event.shift:
                self.which = 'ALL'
            elif event.ctrl:
                self.which = 'SELECTED'
            else:
                self.which = 'VISIBLE'
        return self.execute(context)

    def execute(self, context):
        is_edit_mode = (context.mode == 'EDIT_MESH')
        
        if is_edit_mode:
            objs = [obj for obj, mesh, bm in EditableMeshes.all() if len(bm.verts) > 0]
        else:
            objs = [obj for obj in context.selected_objects
                if (obj.type == 'MESH') and obj.visible_get() and (len(obj.data.vertices) > 0)]
        
        if not objs:
            return {'CANCELLED'}
        
        get_target, converted = self.make_target_getter(context, objs)
        if not get_target:
            return {'CANCELLED'}
        
        if is_edit_mode:
            bpy.ops.object.mode_set(mode='OBJECT')
        
        layer_objs = context.view_layer.objects
        active_obj = layer_objs.active
        
        use_vertex_group = (self.which != 'ALL')
        
        for obj in objs:
            if use_vertex_group:
                vg = obj.vertex_groups.new(name='Visible')
                if self.which == 'VISIBLE':
                    indices = [v.index for v in obj.data.vertices if not v.hide]
                else:
                    indices = [v.index for v in obj.data.vertices if v.select]
                vg.add(indices, 1.0, 'REPLACE')
                vg_name = vg.name
            
            md = obj.modifiers.new('Shrinkwrap', 'SHRINKWRAP')
            md.wrap_method = self.wrap_method
            md.wrap_mode = 'ON_SURFACE'
            md.use_negative_direction = True
            md.use_positive_direction = True
            md.target = get_target(obj)
            
            if use_vertex_group:
                md.vertex_group = vg_name
            
            obj.modifiers.move(len(obj.modifiers)-1, 0)
            layer_objs.active = obj
            bpy.ops.object.modifier_apply(modifier=md.name)
            
            if use_vertex_group:
                # At this point, the reference is no longer valid
                vg = obj.vertex_groups[vg_name]
                obj.vertex_groups.remove(vg)
        
        for target in converted.values():
            mesh = target.data
            bpy.data.objects.remove(target)
            bpy.data.meshes.remove(mesh)
        
        if is_edit_mode:
            bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}

    def make_target_getter(self, context, objs):
        nflow_config_scene = context.scene.nsolve.ops.nflow
        
        target = nflow_config_scene.projection_target
        candidates = ([target] if target else context.scene.objects)
        
        # Shrinkwrap only supports meshes as targets
        targets = [obj for obj in candidates
            if (obj.type in Raycaster.obj_types) and obj.visible_get() and (obj not in objs)]
        
        if not targets:
            return None, None
        
        def find_target(obj):
            obj_matrix = obj.matrix_world
            verts = [(obj_matrix @ v.co) for v in obj.data.vertices]
            
            best_dist = math.inf
            best_target = None
            
            for target in targets:
                matrix = target.matrix_world
                matrix_inv = matrix.inverted_safe()
                
                dist = 0
                count = 0
                
                for v in verts:
                    try:
                        result = target.closest_point_on_mesh(matrix_inv @ v)
                    except Exception:
                        break # could not create BVH tree (e.g. if mesh is too big)
                    
                    if result[0]:
                        dist += ((matrix @ result[1]) - v).magnitude
                        count += 1
                
                if count > 0:
                    dist /= count * (count / len(verts))
                    if dist < best_dist:
                        best_dist = dist
                        best_target = target
            
            return best_target
        
        converted = {}
        
        def get_target(obj):
            target = targets[0] if len(targets) == 1 else find_target(obj)
            if target.type == 'MESH':
                return target
            
            new_target = converted.get(target)
            if new_target is None:
                depsgraph = context.evaluated_depsgraph_get()
                target_eval = target.evaluated_get(depsgraph)
                mesh = bpy.data.meshes.new_from_object(target_eval)
                new_target = bpy.data.objects.new(target.name, mesh)
                # context.collection.objects.link(new_target)
                new_target.matrix_world = target_eval.matrix_world
                converted[target] = new_target
            
            return new_target
        
        return get_target, converted


class NSOLVE_PT_NFlow_Snapping_Options(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_Snapping_Options'
    bl_label = 'nFlow snapping'
    bl_space_type = 'CONSOLE'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        
        self.draw_options(layout, context)

    @classmethod
    def draw_options(cls, layout, context):
        workspace = context.workspace
        
        nflow_config_scene = context.scene.nsolve.ops.nflow
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        behavior_preset = behavior_presets_config.get_active_preset()
        capabilities = NFlow.gather_capabilities(behavior_preset)
        
        nflow_prefs = NFlowPrefs.prefs()
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        row = layout.row()
        row.label(text='Shrinkwrap', icon='MOD_SHRINKWRAP')
        subrow = row.row()
        subrow.alignment = 'RIGHT'
        op = subrow.operator_menu_enum('nsolve.nflow_shrinkwrap', 'wrap_method', text='Do now')
        op.which = 'CONTEXT'
        
        row = layout.row()
        ui_prop(row, nflow_config_scene, 'projection_target', text='', placeholder='Target')
        
        row = layout.row()
        row.active = ('SHRINKWRAP' in capabilities)
        subrow = row.row()
        subrow.alignment = 'LEFT'
        subrow.prop(nflow_config_workspace, 'use_auto_shrinkwrap',text='Auto', toggle=True)
        row.prop(nflow_config_workspace, 'auto_shrinkwrap_mode', text='')
        
        layout.separator()
        
        row = layout.row()
        row.active = ('SNAP' in capabilities)
        split = row.split()
        split.label(text='Snapping', icon='SNAP_ON')
        subrow = split.row()
        subrow.prop(nflow_config_workspace, 'snap_key', text='', event=True)
        
        row = layout.row()
        row.active = ('SNAP' in capabilities)
        split = row.split()
        subrow = split.row(align=True)
        draw_enum_items(subrow, nflow_config_workspace, 'snap_to', text='')
        split.prop(nflow_prefs, 'snap_radius', text='Radius')
        
        row = layout.row()
        row.active = ('SNAP' in capabilities)
        row.prop(nflow_prefs, 'merge_radius')
        
        layout.separator()
        
        row = layout.row()
        row.active = ('MIRROR' in capabilities)
        row.label(text='Mirror', icon='MOD_MIRROR')
        subrow = row.row()
        subrow.alignment = 'RIGHT'
        subrow.prop(nflow_config_workspace, 'use_mirror_clipping', text='Clip')


class NSOLVE_MT_NFlow_Select_Behavior_Preset(bpy.types.Menu):
    bl_idname = 'NSOLVE_MT_NFlow_Select_Behavior_Preset'
    bl_label = 'Select a preset to edit'

    def draw(self, context):
        layout = self.layout
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        behavior_presets = behavior_presets_config.behavior_presets
        
        active_preset = behavior_presets_config.get_active_preset()
        
        for i, behavior_preset in enumerate(behavior_presets):
            icon = ('SOLO_ON' if behavior_preset == active_preset else 'SOLO_OFF')
            op = layout.operator('nsolve.nflow_select_behavior_preset',
                text=behavior_preset.name, icon=icon)
            op.index = i


class NSOLVE_OT_NFlow_Select_Behavior_Preset(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_select_behavior_preset'
    bl_label = 'Select preset'
    bl_description = 'Select preset'
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        # This is a convenient time to update the items
        BehaviorPresetEntryItems.update_items()
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        behavior_presets_config.behavior_preset_active = self.index
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Activate_Behavior_Preset(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_activate_behavior_preset'
    bl_label = 'Activate preset'
    bl_description = 'Activate/deactivate preset'
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        # This is a convenient time to update the items
        BehaviorPresetEntryItems.update_items()
        
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        if behavior_presets_config.behavior_preset_active != self.index:
            behavior_presets_config.behavior_preset_active = self.index
        # else:
        #     behavior_presets_config.behavior_preset_active = -1
        context.area.tag_redraw()
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Add_Behavior_Preset(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_add_behavior_preset'
    bl_label = 'New preset'
    bl_description = 'Add preset'
    bl_options = {'INTERNAL'}

    copy_active: bpy.props.BoolProperty()

    @classmethod
    def description(cls, context, properties):
        return ('Copy this preset' if properties.copy_active else 'Add a new preset')

    def execute(self, context):
        # This is a convenient time to update the items
        BehaviorPresetEntryItems.update_items()
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        behavior_presets = behavior_presets_config.behavior_presets
        active_preset = behavior_presets_config.get_active_preset()
        
        behavior_preset = behavior_presets.add()
        
        behavior_presets_config.behavior_preset_active = len(behavior_presets)-1
        
        if active_preset and self.copy_active:
            behavior_preset.name = self.make_name(behavior_presets, active_preset.name)
            
            for entry_src in active_preset.entries:
                entry_dst = behavior_preset.entries.add()
                entry_dst.copy(entry_src)
        else:
            behavior_preset.name = self.make_name(behavior_presets, 'Preset')
            behavior_preset.entries.add()
        
        if len(behavior_presets) == 1:
            behavior_presets_config.set_active_preset(behavior_preset)
        
        behavior_presets_config.is_initialized = True
        
        context.area.tag_redraw()
        
        return {'FINISHED'}

    def make_name(self, behavior_presets, src_name):
        base_name, max_index, padding = self.split_name_index(src_name)
        if (base_name == src_name) and not base_name.endswith(' '):
            base_name += ' '
        
        for behavior_preset in behavior_presets:
            name, index, _ = self.split_name_index(behavior_preset.name)
            if name == base_name:
                max_index = max(max_index, index)
        
        return base_name + str(max_index+1).zfill(padding)

    def split_name_index(self, name):
        number = 0
        count = 0
        digits = '0123456789'
        for c in reversed(name):
            if c not in digits:
                break
            number += int(c) * 10**count
            count += 1
        return (name[:-count] if count > 0 else name), number, count


class NSOLVE_OT_NFlow_Remove_Behavior_Preset(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_remove_behavior_preset'
    bl_label = 'Remove preset'
    bl_description = '\n'.join([
        'Click: remove this preset',
        'Ctrl+Click: remove other presets',
        'Shift+Click: remove all presets',
    ])
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    mode: bpy.props.EnumProperty(name='Mode', description='Mode',
        items=[
            ('ACTIVE', 'Active', 'Active'),
            ('ALL', 'All', 'All'),
            ('OTHER', 'Other', 'Other'),
        ],
        default='ACTIVE',
    )

    def invoke(self, context, event):
        if event.shift:
            self.mode = 'ALL'
        elif event.ctrl:
            self.mode = 'OTHER'
        else:
            self.mode = 'ACTIVE'
        return self.execute(context)

    def execute(self, context):
        # This is a convenient time to update the items
        BehaviorPresetEntryItems.update_items()
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        behavior_presets = behavior_presets_config.behavior_presets
        if self.mode == 'ALL':
            behavior_presets.clear()
        else:
            if (self.index >= 0) and (self.index < len(behavior_presets)):
                if self.mode == 'OTHER':
                    while self.index > 0:
                        behavior_presets.remove(0)
                        self.index -= 1
                    while len(behavior_presets) > 1:
                        behavior_presets.remove(1)
                else:
                    behavior_presets.remove(self.index)
        context.area.tag_redraw()
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Add_Behavior_Preset_Entry(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_add_behavior_preset_entry'
    bl_label = 'Add'
    bl_description = 'Add a new entry'
    bl_options = {'INTERNAL'}

    def execute(self, context):
        # This is a convenient time to update the items
        BehaviorPresetEntryItems.update_items()
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        active_preset = behavior_presets_config.get_active_preset()
        
        if active_preset is None:
            return {'CANCELLED'}
        
        entry = active_preset.entries.add()
        
        if not behavior_presets_config.behavior_default_enable:
            entry.elements = set()
        
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Remove_Behavior_Preset_Entry(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_remove_behavior_preset_entry'
    bl_label = 'Remove'
    bl_description = 'Remove this entry'
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        # This is a convenient time to update the items
        BehaviorPresetEntryItems.update_items()
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        active_preset = behavior_presets_config.get_active_preset()
        
        if active_preset is None:
            return {'CANCELLED'}
        
        if (self.index >= 0) and (self.index < len(active_preset.entries)):
            active_preset.entries.remove(self.index)
        
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Duplicate_Behavior_Preset_Entry(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_duplicate_behavior_preset_entry'
    bl_label = 'Duplicate'
    bl_description = 'Duplicate this entry'
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        # This is a convenient time to update the items
        BehaviorPresetEntryItems.update_items()
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        active_preset = behavior_presets_config.get_active_preset()
        
        if active_preset is None:
            return {'CANCELLED'}
        
        if (self.index >= 0) and (self.index < len(active_preset.entries)):
            source = active_preset.entries[self.index]
            entry = active_preset.entries.add()
            entry.copy(source)
            active_preset.entries.move(len(active_preset.entries)-1, self.index+1)
        
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Move_Behavior_Preset_Entry(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_move_behavior_preset_entry'
    bl_label = 'Move'
    bl_description = 'Move this entry'
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()
    new_index: bpy.props.IntProperty()

    def execute(self, context):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        active_preset = behavior_presets_config.get_active_preset()
        
        if active_preset is None:
            return {'CANCELLED'}
        
        count = len(active_preset.entries)
        if (self.index >= 0) and (self.index < count):
            new_index = min(max(self.new_index, 0), count-1)
            active_preset.entries.move(self.index, new_index)
        
        return {'FINISHED'}


class BehaviorPresetEntryItems:
    special = '@'

    str_map = {}
    items = []
    grouped = {}
    all = {}
    recent = []

    @classmethod
    def get_str(cls, s):
        s2 = cls.str_map.get(s)
        if s2 is None:
            s2 = s
            cls.str_map[s] = s2
        return s2

    @classmethod
    def parse_filters(cls):
        nflow_prefs = NFlowPrefs.prefs()
        
        filter_all = nflow_prefs.behavior_filter_all
        
        include = {}
        exclude = {}
        
        for behavior_filter in nflow_prefs.behavior_filters:
            category_key = behavior_filter.name.strip().casefold()
            if not category_key:
                continue
            
            filters = []
            
            for part in behavior_filter.filter.split(','):
                part = part.strip()
                
                show = True
                if part.startswith('!'):
                    show = False
                    part = part.strip('!').strip()
                
                if part:
                    filters.append((part.casefold(), show))
            
            def make_filter(filters):
                if not filters:
                    return (lambda name: True)
                
                def filter_func(name):
                    name = name.casefold()
                    show = filter_all
                    for pattern, filter_show in filters:
                        if pattern in name:
                            show = filter_show
                    return show
                
                return filter_func
            
            container = (include if behavior_filter.show else exclude)
            container[category_key] = make_filter(filters)
        
        def get_filter(category):
            category = category.casefold()
            
            if not filter_all:
                return include.get(category)
            
            if category in exclude:
                return None
            
            return include.get(category) or (lambda name: True)
        
        return get_filter

    @classmethod
    def enumerate_items(cls):
        get_filter = cls.parse_filters()
        
        yield '', ('', '', '')
        
        for name, info in sorted(NFlow.behaviors.items()):
            yield cls.special, (name, name, info['description'])
        
        NFlow.update_special_operators()
        yield from NFlow.special_operators_items
        
        for category_name in dir(bpy.ops):
            category = getattr(bpy.ops, category_name)
            category_label = category_name.capitalize().replace('_', ' ')
            
            filter_func = get_filter(category_label)
            if filter_func is None:
                continue
            
            for op_name in dir(category):
                op = getattr(category, op_name)
                
                if 'INTERNAL' in op.bl_options:
                    continue
                
                op_rna = op.get_rna_type()
                
                if not filter_func(op_rna.name):
                    continue
                
                yield category_label, (op.idname_py(), op_rna.name, op_rna.description)

    @classmethod
    def on_load(cls, scene):
        cls.update_items()

    @classmethod
    def update_items(cls):
        wm = bpy.context.window_manager
        behavior_search_candidates = wm.nsolve.ops.nflow.behavior_search_candidates
        behavior_search_candidates.clear()
        
        cls.items.clear()
        cls.grouped.clear()
        cls.all.clear()
        
        def to_name(idname):
            return idname.split('.')[-1].replace('_', ' ').capitalize()
        
        for category, item in cls.enumerate_items():
            idname, name, description = item
            idname = cls.get_str(idname)
            name = cls.get_str(name or to_name(idname))
            description = cls.get_str(description)
            
            prefixed_name = (f'{category}: {name}' if name and (category != cls.special) else name)
            
            cls.items.append((idname, prefixed_name, description))
            
            group = cls.grouped.get(category)
            if group is None:
                group = []
                cls.grouped[category] = group
            group.append((idname, name, description))
            
            cls.all[idname] = (idname, prefixed_name, description)
            
            if idname:
                search_candidate = behavior_search_candidates.add()
                search_candidate.name = idname

    @classmethod
    def get_items(cls):
        if not cls.items:
            cls.update_items()
        return cls.items

    @classmethod
    def get_grouped(cls):
        if not cls.grouped:
            cls.update_items()
        return cls.grouped

    @classmethod
    def get_recent_group(cls):
        if not cls.all:
            cls.update_items()
        return [cls.all[idname] for idname in reversed(cls.recent) if idname in cls.all]

    @classmethod
    def add_recent(cls, idname):
        if not idname:
            return
        
        try:
            cls.recent.remove(idname)
        except ValueError:
            pass
        
        cls.recent.append(idname)


class NSOLVE_OT_NFlow_Select_Behavior_Preset_Entry(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_select_behavior_preset_entry'
    bl_label = 'Select'
    bl_description = 'Select a behavior or operator'
    bl_options = {'INTERNAL'}

    behavior: bpy.props.StringProperty()

    description: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        return properties.description

    def execute(self, context):
        entry = getattr(context, 'nflow_preset_entry', None)
        
        if entry is not None:
            BehaviorPresetEntryItems.add_recent(self.behavior)
            entry.behavior = self.behavior
            context.area.tag_redraw()
            return {'FINISHED'}
        
        return {'CANCELLED'}


class NSOLVE_OT_NFlow_Search_Behavior_Preset_Entry(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_search_behavior_preset_entry'
    bl_label = 'Search'
    bl_description = 'Find an operator'
    bl_options = {'INTERNAL'}

    bl_property = 'behavior'

    behavior: bpy.props.EnumProperty(
        items=(lambda self, context: BehaviorPresetEntryItems.get_items()),
    )

    entry = None

    def invoke(self, context, event):
        cls = NSOLVE_OT_NFlow_Search_Behavior_Preset_Entry
        
        cls.entry = getattr(context, 'nflow_preset_entry', None)
        if cls.entry is None:
            return {'CANCELLED'}
        
        # Since this will be invoked from inside of the menu,
        # items will already be updated
        # BehaviorPresetEntryItems.update_items()
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):
        cls = NSOLVE_OT_NFlow_Search_Behavior_Preset_Entry
        if cls.entry is not None:
            BehaviorPresetEntryItems.add_recent(self.behavior)
            cls.entry.behavior = self.behavior
            cls.entry = None
        context.area.tag_redraw()
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Add_Behavior_Filter(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_add_behavior_filter'
    bl_label = 'Add'
    bl_description = 'Add a filter'
    bl_options = {'INTERNAL'}

    def execute(self, context):
        behavior_filters = NFlowPrefs.get('behavior_filters')
        behavior_filters.add()
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Remove_Behavior_Filter(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_remove_behavior_filter'
    bl_label = 'Remove'
    bl_description = 'Remove this filter'
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        behavior_filters = NFlowPrefs.get('behavior_filters')
        if (self.index >= 0) and (self.index < len(behavior_filters)):
            behavior_filters.remove(self.index)
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Reset_Behavior_Filters(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_reset_behavior_filters'
    bl_label = 'Reset'
    bl_description = 'Reset filters'
    bl_options = {'INTERNAL'}

    def execute(self, context):
        nflow_prefs = NFlowPrefs.prefs()
        nflow_prefs.behavior_filters_initialized = False
        setup_default_behavior_filters()
        return {'FINISHED'}


class NSOLVE_PT_NFlow_Filter_Behavior_Preset_Entries(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_Filter_Behavior_Preset_Entries'
    bl_label = 'Filter'
    bl_space_type = 'CONSOLE'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        
        nflow_prefs = NFlowPrefs.prefs()
        
        # layout.label(text='Will be applied on menu reopen')
        
        row = layout.row()
        subrow = row.row()
        subrow.alignment = 'LEFT'
        subrow.prop(nflow_prefs, 'behavior_filter_all')
        subrow = row.row()
        subrow.alignment = 'RIGHT'
        subrow.operator('nsolve.nflow_reset_behavior_filters', text='', icon='RECOVER_LAST')
        
        for i, behavior_filter in enumerate(nflow_prefs.behavior_filters):
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(behavior_filter, 'show', text='', icon='HIDE_OFF')
            row.prop(behavior_filter, 'name', text='')
            op = row.operator('nsolve.nflow_remove_behavior_filter', text='', icon='X')
            op.index = i
            col.prop(behavior_filter, 'filter', text='')
        
        layout.operator('nsolve.nflow_add_behavior_filter', text='Add', icon='ADD')


class NSOLVE_MT_NFlow_Choose_Behavior_Preset_Entry(bpy.types.Menu):
    bl_label = 'Choose'
    bl_idname = 'NSOLVE_MT_NFlow_Choose_Behavior_Preset_Entry'

    def draw(self, context):
        layout = self.layout
        
        recent_mark = '#'
        operators_mark = '*'
        
        metadata = UIMetadata.get(context)
        
        category = metadata.get('category')
        
        def draw_category(layout, category, prefix=None, text=None, icon='BLANK1'):
            prefix = (text if prefix is None else prefix)
            UIMetadata.set(layout, {'category': category, 'prefix': prefix})
            layout.menu(self.bl_idname, text=(text or category), icon=icon)
        
        if not category:
            layout.operator('nsolve.nflow_search_behavior_preset_entry', text='Search', icon='VIEWZOOM')
            draw_category(layout, recent_mark, prefix='', text='Recent', icon='RECOVER_LAST')
            layout.popover('NSOLVE_PT_NFlow_Filter_Behavior_Preset_Entries', text='Filters', icon='FILTER')
            
            layout.separator()
            
            draw_category(layout, BehaviorPresetEntryItems.special, text='nFlow', icon='SOLO_ON')
            
            layout.separator()
            
            draw_category(layout, operators_mark, text='Operators', icon='SCRIPT')
        elif category == operators_mark:
            BehaviorPresetEntryItems.update_items()
            grouped = BehaviorPresetEntryItems.get_grouped()
            
            for category, group in grouped.items():
                if category and (category != BehaviorPresetEntryItems.special):
                    draw_category(layout, category, icon='SCRIPT')
        else:
            layout.operator_context = 'EXEC_DEFAULT'
            
            entry = getattr(context, 'nflow_preset_entry', None)
            if entry:
                command, _ = parse_operator_command(entry.behavior)
            else:
                command = ''
            
            prefix = metadata.get('prefix')
            if prefix:
                prefix = prefix + ': '
            
            if category == recent_mark:
                group = BehaviorPresetEntryItems.get_recent_group()
            else:
                grouped = BehaviorPresetEntryItems.get_grouped()
                group = grouped.get(category, ())
            
            if not group:
                layout.label(text='(empty)')
            
            for idname, name, description in group:
                icon = ('CHECKBOX_HLT' if idname == command else 'CHECKBOX_DEHLT')
                text = (name[len(prefix):] if prefix else name)
                op = layout.operator('nsolve.nflow_select_behavior_preset_entry', text=text, icon=icon)
                op.behavior = idname
                op.description = description


class NSOLVE_OT_NFlow_Clear_Behavior_Preset_Entry_Command(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_clear_behavior_preset_entry_command'
    bl_label = 'Clear'
    bl_description = 'Clear the textbox value'
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        active_preset = behavior_presets_config.get_active_preset()
        
        if active_preset is None:
            return {'CANCELLED'}
        
        if (self.index >= 0) and (self.index < len(active_preset.entries)):
            active_preset.entries[self.index].behavior = ''
        
        return {'FINISHED'}


class NSOLVE_MT_NFlow_Choose_Behavior_Preset_Entry_Option_Enum(bpy.types.Menu):
    bl_label = 'Choose'
    bl_idname = 'NSOLVE_MT_NFlow_Choose_Behavior_Preset_Entry_Option_Enum'

    def draw(self, context):
        layout = self.layout
        
        metadata = UIMetadata.get(context)
        
        option_idname = metadata.get('option_idname')
        items = metadata.get('option_enum_items')
        
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except Exception:
                items = None
        
        if not (option_idname and items):
            return
        
        for item in items:
            idname = item[0]
            name = item[1]
            op = layout.operator('nsolve.nflow_set_behavior_preset_entry_option_enum', text=name)
            op.option_idname = option_idname
            op.value = idname


class NSOLVE_OT_NFlow_Set_Behavior_Preset_Entry_Option_Enum(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_set_behavior_preset_entry_option_enum'
    bl_label = 'Value'
    bl_description = 'Select an option'
    bl_options = {'INTERNAL'}

    option_idname: bpy.props.StringProperty()

    value: bpy.props.StringProperty()

    def execute(self, context):
        entry = getattr(context, 'nflow_preset_entry', None)
        
        if entry is not None:
            option = entry.find_option(self.option_idname)
            if option is not None:
                option.string_value = self.value
            return {'FINISHED'}
        
        return {'CANCELLED'}


class NFlowBehaviorPresetEntryOperatorArgument(bpy.types.PropertyGroup):
    exists: bpy.props.BoolProperty(name='Exists', description='Operator has this argument')
    hidden: bpy.props.BoolProperty(name='Hidden', description='This argument is hidden')
    use: bpy.props.BoolProperty(name='Use', description='Use this argument')
    value: bpy.props.StringProperty(name='Value', description='Python value')


class NSOLVE_OT_NFlow_Edit_Behavior_Preset_Entry_Operator_Args(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_edit_behavior_preset_entry_operator_args'
    bl_label = 'Edit operator arguments'
    bl_description = 'Customize the arguments of this operator'
    bl_options = {'INTERNAL'}

    show_hidden: bpy.props.BoolProperty(name='Show hidden', description='Show hidden arguments')
    arguments: bpy.props.CollectionProperty(type=NFlowBehaviorPresetEntryOperatorArgument)

    entry = None
    prefix = ''
    command = ''

    def invoke(self, context, event):
        entry = getattr(context, 'nflow_preset_entry', None)
        if entry is None:
            return {'CANCELLED'}
        
        command = entry.behavior
        
        bracket_index = command.find('(')
        if bracket_index >= 0:
            prefix = command[:bracket_index].strip()
        else:
            prefix = command.strip()
        
        command, args = parse_operator_command(command, remap_special=True)
        
        self.arguments.clear()
        
        op = get_operator(command)
        
        if op is not None:
            op_rna = op.get_rna_type()
            
            dummy_info = {'hidden': False}
            prop_infos_dict = {}
            prop_infos_list = []
            
            def serialize_value(value):
                if (not hasattr(value, '__len__')) or isinstance(value, (str, set)):
                    return value
                
                return tuple(serialize_value(item) for item in value)
            
            rna_names = ('bl_rna', 'rna_type')
            
            for rna_prop in op_rna.properties:
                identifier = rna_prop.identifier
                if identifier in rna_names:
                    continue
                
                is_hidden = getattr(rna_prop, 'is_hidden', False)
                array_length = getattr(rna_prop, 'array_length', 0)
                
                if array_length == 0:
                    value = getattr(rna_prop, 'default', None)
                else:
                    value = getattr(rna_prop, 'array_dimensions', None)
                    value = serialize_value(value)
                
                info = dict(idname=identifier, hidden=is_hidden, value=value)
                prop_infos_dict[identifier] = info
                prop_infos_list.append(info)
            
            args = eval_operator_args(args)
            if isinstance(args, dict):
                for idname, value in args.items():
                    argument = self.arguments.add()
                    argument.name = idname
                    argument.value = repr(value)
                    argument.use = True
                    argument.exists = (idname in prop_infos_dict)
                    argument.hidden = prop_infos_dict.get(idname, dummy_info)['hidden']
            else:
                args = {}
            
            for info in prop_infos_list:
                idname = info['idname']
                value = info['value']
                hidden = info['hidden']
                if idname not in args:
                    argument = self.arguments.add()
                    argument.name = idname
                    argument.value = repr(value)
                    argument.use = False
                    argument.exists = True
                    argument.hidden = hidden
        
        self.entry = entry
        self.op = op
        self.prefix = prefix
        self.command = command
        
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=300)

    def execute(self, context):
        if self.entry is None:
            return {'CANCELLED'}
        
        args = ', '.join(f'{arg.name}={arg.value}' for arg in self.arguments if arg.use)
        self.entry.behavior = f'{self.prefix}({args})'
        
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        
        if not self.op:
            layout.label(text=f'Unknown operator: {self.prefix}', icon='ERROR')
            return
        
        row = layout.row()
        row.prop(self, 'show_hidden', text='', icon='GHOST_ENABLED')
        row.label(text=self.command)
        
        col = layout.column(align=True)
        for argument in self.arguments:
            if self.show_hidden or not argument.hidden:
                row = col.row(align=True)
                row.alert = not argument.exists
                row.prop(argument, 'use', text=argument.name, toggle=True)
                subrow = row.row(align=True)
                subrow.active = argument.use
                subrow.prop(argument, 'value', text='')


class NSOLVE_PT_NFlow_Preset_Entry_Options(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_Preset_Entry_Options'
    bl_label = 'Options'
    bl_space_type = 'CONSOLE'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        
        entry = getattr(context, 'nflow_preset_entry', None)
        if entry is None:
            return
        
        is_behavior = entry.is_behavior()
        is_operator = (not is_behavior) and entry.is_operator()
        
        if not (is_behavior or is_operator):
            layout.label(text='Invalid behavior name', icon='ERROR')
            return
        
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        behavior_entry_display = nflow_config_workspace.behavior_entry_display
        
        metadata = UIMetadata.get(context)
        
        workspace = context.workspace
        
        def grouped_layout(text, align=False, fold=True):
            return foldable_layout(layout, workspace, self.bl_idname, text, align=align, fold=fold)
        
        is_configurable = (behavior_entry_display not in ('TOUR', 'HELP'))
        
        if not is_configurable:
            sublayout = grouped_layout('Advanced')
        else:
            sublayout = layout
        
        if behavior_entry_display != 'FULL':
            try:
                index = int(metadata['index'])
            except Exception:
                index = None
            
            if index is not None:
                if sublayout:
                    box = sublayout.box()
                    box.alert = entry.get('is_error')
                    row = box.row()
                    row.alignment = 'CENTER'
                    entry.draw_shortcut(row, index, alignment='CENTER')
                    entry.draw_extras(row, index, alignment='CENTER', locked=(not is_configurable))
                    entry.draw_elements(box, index, alignment='CENTER')
        
        if sublayout:
            ui_prop(sublayout, entry, 'name', text='', placeholder='Custom name')
            
            col = sublayout.column(align=True)
            row = col.row()
            row.label(text='Selection & history:')
            subrow = ui_row(row, alignment='LEFT')
            # Using RADIOBUT_ON, because 'record' icon has different idnames in Blender 4.0 and 4.1
            subrow.prop(entry, 'select_push_undo', text='Undo', icon='RADIOBUT_ON', toggle=True)
            
            row = col.row(align=True)
            row.prop(entry, 'selection_mode', text='')
            row_right = ui_row(row, alignment='RIGHT')
            row_right.prop(entry, 'select_after', text='After', toggle=True)
            row_right.prop(entry, 'select_lock_element_type', text='', icon='LOCKED')
            
            row = col.row(align=True)
            row.prop(entry, 'select_first_vertex', text='First', icon='VERTEXSEL', toggle=True)
            row.prop(entry, 'select_last_vertex', text='Last', icon='VERTEXSEL', toggle=True)
            draw_enum_items(row, entry, 'ensure_element_selection', text='')
            
            row = sublayout.row(align=True)
            row.prop(entry, 'cursor_3d_snap')
        
        if is_operator:
            command, args = parse_operator_command(entry.behavior, True)
            args_are_valid = (not args) or isinstance(eval_operator_args(args), dict)
            icon = ('NONE' if args_are_valid else 'ERROR')
            row = layout.row()
            row.alert = not args_are_valid
            row.operator('nsolve.nflow_edit_behavior_preset_entry_operator_args', icon=icon)
        elif is_behavior:
            options_descriptor = entry.gather_options()
            
            option_infos = options_descriptor['option_infos']
            
            option_infos = [option_info for option_info in option_infos if option_info['option']]
            
            if option_infos:
                box = layout.box()
                options_draw = options_descriptor['options_draw']
                if options_draw:
                    options_draw(box, context)
                else:
                    for option_info in option_infos:
                        option = option_info['option']
                        name = option_info['name']
                        value = option_info['value']
                        items = option_info.get('items')
                        event = option_info.get('event')
                        row = box.row()
                        option.draw(row, name, value, items, event)
            
            settings_draw = options_descriptor['settings_draw']
            if settings_draw:
                draw = settings_draw(option_infos)
                if draw:
                    box = layout.box()
                    draw(box, context)


class NSOLVE_PT_NFlow_Config_Options(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_Config_Options'
    bl_label = 'Options'
    bl_space_type = 'CONSOLE'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        layout.ui_units_x = 7
        self.draw_body(layout, context)

    @classmethod
    def draw_body(cls, layout, context):
        nflow_prefs = NFlowPrefs.prefs()
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        def draw_scroll(layout):
            row = layout.row(align=True)
            row.prop(nflow_prefs, 'behavior_preset_scroll_enable', text='', icon='MOUSE_MMB')
            subrow = row.row(align=True)
            subrow.alignment = 'LEFT'
            subrow.active = nflow_prefs.behavior_preset_scroll_enable
            parts = [mod.capitalize() for mod in nflow_prefs.behavior_preset_scroll_modifiers]
            text = '+'.join(parts)
            subrow.prop_menu_enum(nflow_prefs, 'behavior_preset_scroll_modifiers', text=text)
            subrow.prop(nflow_prefs, 'behavior_preset_scroll_invert', text='', icon='UV_SYNC_SELECT')
        
        def draw_preset_buttons(layout):
            row = layout.row()
            
            subrow = row.row(align=True)
            subrow.operator('nsolve.nflow_copy_config', text='', icon='COPYDOWN')
            subrow.operator('nsolve.nflow_paste_config', text='', icon='PASTEDOWN')
            subrow.operator('nsolve.nflow_export_config', text='', icon='EXPORT')
            subrow.operator('nsolve.nflow_import_config', text='', icon='IMPORT')
            subrow.menu('NSOLVE_MT_NFlow_Import_Default_Config', text='', icon='PRESET')
            
            subrow = row.row(align=True)
            UIMetadata.set(subrow, {'import_mode': 'OVERRIDE'})
            subrow.alignment = 'RIGHT'
            subrow.popover('NSOLVE_PT_NFlow_Preset_Colors', text='', icon='COLOR')
            subrow.prop_menu_enum(nflow_prefs, 'topbar_extras_display', text='', icon='TOPBAR')
            subrow.prop_menu_enum(nflow_config_workspace, 'behavior_entry_display', text='', icon='INFO')
        
        def draw_color(layout):
            row = layout.row(align=True)
            row.alignment = 'RIGHT'
            
            behavior_presets_config = NFlowBehaviorPresetsConfig.get()
            behavior_preset = behavior_presets_config.get_active_preset()
            if behavior_preset is None:
                return
            
            row.prop(behavior_preset, 'use_override_color', text='')
            subrow = row.row(align=True)
            subrow.ui_units_x = 1
            subrow.prop(behavior_preset, 'override_color', text='')
        
        draw_preset_buttons(layout)
        
        row = layout.row()
        draw_scroll(row)
        # draw_color(row)


class NSOLVE_PT_NFlow_Config_Popover(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_Config_Popover'
    bl_label = 'nFlow' + ' ' + get_addon_version()
    bl_space_type = 'CONSOLE'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        self.layout.ui_units_x = 16
        draw_presets = NFlowPrefs.get('draw_presets')
        draw_presets(self.layout, context, place='POPOVER')


class NSOLVE_PT_NFlow_Preset_Colors(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_Preset_Colors'
    bl_label = 'Preset colors'
    bl_space_type = 'CONSOLE'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        
        layout.ui_units_x = 2
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get()
        behavior_preset = behavior_presets_config.get_active_preset()
        if behavior_preset is None:
            return
        
        row = layout.row()
        row.prop(behavior_preset, 'use_override_color', text='')
        row.prop(behavior_preset, 'override_color', text='')
        
        # for item in behavior_preset.bl_rna.properties['color_overrides'].enum_items:
        #     row = layout.row()
        #     row.prop_enum(behavior_preset, 'color_overrides', item.identifier)
            
        #     color_attr_name = f'color_{item.identifier.lower()}'
        #     if hasattr(behavior_preset, color_attr_name):
        #         row.prop(behavior_preset, color_attr_name, text='')


class NSOLVE_PT_NFlow_Global_Options(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_Global_Options'
    bl_label = 'nFlow options'
    bl_space_type = 'CONSOLE'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        layout.ui_units_x = 10.5
        
        workspace = context.workspace
        
        nflow_prefs = NFlowPrefs.prefs()
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        def grouped_layout(text, align=False, fold=True):
            return foldable_layout(layout, workspace, self.bl_idname, text, align=align, fold=fold)
        
        NSOLVE_PT_NFlow_Config_Options.draw_body(layout, context)
        
        layout.separator()
            
        sublayout = grouped_layout('Display')
        if sublayout:
            sublayout.separator()
            col = sublayout.column()
            row = col.row()
            row.prop(nflow_prefs, 'presets_width_limit', text='Width')
            row.prop_menu_enum(nflow_config_workspace, 'behavior_entry_display', text='Behavior UI')
            row = col.row()
            row.prop(nflow_prefs, 'behavior_shorten_name')
            row.prop_menu_enum(nflow_prefs, 'help_text_show_all', text='Shortcuts')
            row = col.row()
            row.prop(nflow_prefs, 'hover_text_enabled', text='Hover text')
            row.prop(nflow_prefs, 'hover_text_size', text='Size')
            # draw_vector_items_row(col, nflow_prefs, 'hover_text_anchor', text=['X:', 'Y:'])
            col = sublayout.column()
            row = col.row()
            row.prop(nflow_prefs, 'help_text_enabled', text='Help text')
            row.prop(nflow_prefs, 'help_text_size', text='Size')
            # draw_vector_items_row(col, nflow_prefs, 'help_text_anchor', text=['X:', 'Y:'])
            col.prop(nflow_prefs, 'help_text_anchor', index=0, text='Anchor X:')
            col.prop(nflow_prefs, 'help_text_spacing', text='Spacing:')
            col = sublayout.column()
            row = col.row()
            row.prop(nflow_config_workspace, 'show_vertex_overlay', text='Vert overlay')
            row.prop(nflow_prefs, 'vertex_overlay_radius', text='')
        
        sublayout = grouped_layout('Detection')
        if sublayout:
            sublayout.separator()
            sublayout.prop(nflow_config_workspace, 'use_hover_occlusion')
            # sublayout.prop(nflow_prefs, 'edge_loop_fraction')
            sublayout.prop(nflow_prefs, 'vert_radius_base')
            # sublayout.prop(nflow_prefs, 'edge_radius_base')
            # sublayout.prop(nflow_prefs, 'edge_radius_ext')
        
        sublayout = grouped_layout('Snapping')
        if sublayout:
            sublayout.separator()
            NSOLVE_PT_NFlow_Snapping_Options.draw_options(sublayout, context)
        
        sublayout = grouped_layout('Input')
        if sublayout:
            sublayout.separator()
            sublayout.prop(nflow_prefs, 'behavior_preset_use_number_shortcuts')
        
        layout.separator()
        layout.separator()
        
        row = layout.row()
        row.operator_context = 'INVOKE_DEFAULT'
        row.alignment = 'RIGHT'
        row.operator('nsolve.help_link', text='', icon='QUESTION')


class NSOLVE_PT_NFlow_Global_Options_Contextual(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_Global_Options_Contextual'
    bl_label = 'Tool settings'
    bl_space_type = 'CONSOLE'
    bl_region_type = 'WINDOW'

    @classmethod
    def gather_settings(cls, context=None):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        behavior_preset = behavior_presets_config.get_active_preset()
        
        command_infos = {}
        
        if behavior_preset:
            for entry in behavior_preset.entries:
                options_descriptor = entry.gather_options()
                
                if options_descriptor is None:
                    continue
                
                if not options_descriptor['settings_draw']:
                    continue
                
                command = options_descriptor['command']
                command_info = command_infos.get(command)
                if command_info is None:
                    command_infos[command] = options_descriptor
                else:
                    command_info['option_infos'].extend(options_descriptor['option_infos'])
        
        sorted_infos = []
        for command, command_info in command_infos.items():
            settings_draw = command_info['settings_draw']
            draw = settings_draw(command_info['option_infos'])
            if draw:
                order = command_info['settings_order']
                label = command_info['settings_label']
                fold = command_info['settings_draw_fold']
                sorted_infos.append((order, label, draw, fold))
        sorted_infos.sort()
        
        return [(label, draw, fold) for _, label, draw, fold in sorted_infos]

    @classmethod
    def poll(cls, context):
        return bool(cls.gather_settings(context))

    def draw(self, context):
        layout = self.layout
        
        workspace = context.workspace
        
        def grouped_layout(text, align=False, fold=False):
            return foldable_layout(layout, workspace, self.bl_idname, text, align=align, fold=fold)
        
        for label, draw, fold in self.gather_settings(context):
            sublayout = grouped_layout(label, fold=fold)
            if sublayout:
                draw(sublayout, context)


class NSOLVE_PT_NFlow_View3D_Sidebar(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_NFlow_View3D_Sidebar'
    bl_label = 'nFlow' + ' ' + get_addon_version()
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'nFlow'

    @classmethod
    def poll(cls, context):
        return NFlowPrefs.get('show_panel')

    def draw_header(self, context):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        layout = self.layout
        
        def draw_space(layout):
            row = layout.row(align=True)
            row.scale_x = 0.1
            row.separator()
        
        draw_space(layout)
        layout.prop(nflow_config_workspace, 'is_active', text='', icon_value=get_icon_id('nflow'))
        layout.prop(nflow_config_workspace, 'behavior_entry_display_toggle', text='', icon='INFO')
        draw_space(layout)

    def draw(self, context):
        draw_presets = NFlowPrefs.get('draw_presets')
        draw_presets(self.layout, context, place='SIDEBAR')


class NSOLVE_OT_NFlow_Copy_Config(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_copy_config'
    bl_label = 'Copy preset(s)'
    bl_description = 'Click: active, Shift+Click: all'
    bl_options = {'INTERNAL'}

    mode: bpy.props.EnumProperty(
        name='Mode',
        description='Which preset(s) should be copied',
        items=[
            ('ALL', 'All', 'Copy all preset(s)'),
            ('ACTIVE', 'Active', 'Copy only the active preset'),
        ],
        default='ALL',
    )

    def invoke(self, context, event):
        self.mode = ('ALL' if event.shift else 'ACTIVE')
        return self.execute(context)

    def execute(self, context):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        data = behavior_presets_config.serialize(mode=self.mode)
        context.window_manager.clipboard = repr(data)
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Paste_Config(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_paste_config'
    bl_label = 'Paste preset(s)'
    bl_description = 'Click: add, Shift+Click: override'
    bl_options = {'INTERNAL'}

    mode: bpy.props.EnumProperty(
        name='Mode',
        description='How the preset(s) should be pasted',
        items=[
            ('ADD', 'Add', 'Add preset(s) to the existing list'),
            ('OVERRIDE', 'Override', 'Replace the existing list with the pasted preset(s)'),
        ],
        default='ADD',
    )

    def invoke(self, context, event):
        self.mode = ('OVERRIDE' if event.shift else 'ADD')
        return self.execute(context)

    def execute(self, context):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        try:
            data = ast.literal_eval(context.window_manager.clipboard)
        except Exception as exc:
            self.report({'ERROR'}, 'Invalid or corrupted data')
            return {'CANCELLED'}
        
        try:
            behavior_presets_config.deserialize(data, mode=self.mode)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        
        context.area.tag_redraw()
        
        return {'FINISHED'}


class NSOLVE_OT_NFlow_Export_Config(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_export_config'
    bl_label = 'Export config'
    bl_description = 'Export preset(s) to file'
    bl_options = {'INTERNAL'}

    filepath: bpy.props.StringProperty(
        name='File Path',
        description='Filepath used for exporting the file',
        maxlen=1024,
        subtype='FILE_PATH',
    )
    check_existing: bpy.props.BoolProperty(
        name='Check Existing',
        description='Check and warn on overwriting existing files',
        default=True,
        options={'HIDDEN'},
    )

    filename_ext = '.ntx'

    filter_glob: bpy.props.StringProperty(
        default='*.ntx',
        options={'HIDDEN'},
        maxlen=255, # blender's max filter length?
    )

    mode: bpy.props.EnumProperty(
        name='Mode',
        description='Which preset(s) should be exported',
        items=[
            ('ALL', 'All', 'Export all preset(s)'),
            ('ACTIVE', 'Active', 'Export only the active preset'),
        ],
        default='ALL',
    )

    check_extension = True

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def check(self, context):
        change_ext = False
        
        filepath = self.filepath
        if os.path.basename(filepath):
            filepath = bpy.path.ensure_ext(os.path.splitext(filepath)[0], self.filename_ext)
            if filepath != self.filepath:
                self.filepath = filepath
                change_ext = True

        return change_ext

    def execute(self, context):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        data = behavior_presets_config.serialize(mode=self.mode)
        with open(self.filepath, 'w', encoding='utf-8') as file:
            file.write(repr(data))
        return {'FINISHED'}


class NFlow_Import_Config_Preset_Options(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(name='Enabled', description='Import this preset', default=True)


class NSOLVE_OT_NFlow_Import_Config(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_import_config'
    bl_label = 'Import config'
    bl_description = 'Import preset(s) from file(s)'
    bl_options = {'INTERNAL'}

    filepath: bpy.props.StringProperty(
        name='File Path',
        description='Filepath used for importing the file',
        maxlen=1024,
        subtype='FILE_PATH',
    )

    directory: bpy.props.StringProperty(
        default='',
        subtype='FILE_PATH',
        options={'HIDDEN'},
        maxlen=1024,
    )
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN'})

    filename_ext = '.ntx'

    filter_glob: bpy.props.StringProperty(
        default='*.ntx',
        options={'HIDDEN'},
        maxlen=255, # blender's max filter length?
    )

    mode: bpy.props.EnumProperty(
        name='Mode',
        description='How the preset(s) should be imported',
        items=[
            ('ADD', 'Add', 'Add preset(s) to the existing list'),
            ('OVERRIDE', 'Override', 'Replace the existing list with the imported preset(s)'),
        ],
        default='OVERRIDE',
    )

    preset_options: bpy.props.CollectionProperty(type=NFlow_Import_Config_Preset_Options)

    last_paths = None
    path_infos = None

    def get_paths(self):
        return [os.path.join(self.directory, item.name) for item in self.files if item.name]

    def invoke(self, context, event):
        self.filepath = self.directory # use the last opened directory
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, 'mode')
        
        if not self.last_paths:
            return
        
        index = 0
        
        for path in self.last_paths:
            names = self.path_infos[path]
            
            box = layout.box()
            col = box.column(align=True)
            
            filename = os.path.basename(path)
            if isinstance(names, list):
                icon_kwargs = dict(icon_value=get_icon_id('nflow'))
            else:
                icon_kwargs = dict(icon='ERROR')
            col.label(text=filename, **icon_kwargs)
            
            if not isinstance(names, list):
                col.label(text=names, icon='BLANK1')
                continue
            
            for name in names:
                preset_option = self.preset_options[index]
                col.prop(preset_option, 'enabled', text=name, icon='BLANK1')
                index += 1

    def check(self, context):
        paths = self.get_paths()
        
        if paths == self.last_paths:
            return False
        
        self.preset_options.clear()
        
        infos = {}
        
        def read(path):
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    data = ast.literal_eval(file.read())
            except Exception as exc:
                data = None
            
            names = NFlowBehaviorPresetsConfig.read_preset_names(data)
            if names is None:
                infos[path] = 'Invalid or corrupted data'
            else:
                infos[path] = names
                for name in names:
                    preset_option = self.preset_options.add()
                    preset_option.name = name
                    preset_option.enabled = True
        
        for path in paths:
            read(path)
        
        self.last_paths = paths
        self.path_infos = infos
        
        return True

    def execute(self, context):
        paths = self.get_paths()
        if not paths: return {'CANCELLED'}
        
        behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
        
        preset_filter = None
        if len(self.preset_options) > 0:
            preset_filter_data = {'index': 0}
            def preset_filter(presets):
                result = []
                for preset in presets:
                    index = preset_filter_data['index']
                    preset_option = self.preset_options[index]
                    preset_filter_data['index'] = index + 1
                    if preset_option.enabled:
                        result.append(preset)
                return result
        
        errors = self.load(behavior_presets_config, paths, self.mode, preset_filter)
        
        context.area.tag_redraw()
        
        if errors:
            self.report({'ERROR'}, '\n'.join(errors))
        
        return {'FINISHED'}

    @classmethod
    def load(cls, behavior_presets_config, paths, mode='OVERRIDE', preset_filter=None):
        errors = []
        
        def load(path, mode):
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    data = ast.literal_eval(file.read())
            except Exception as exc:
                errors.append(f'{path}\n* Invalid or corrupted data')
                return
            
            try:
                behavior_presets_config.deserialize(data, mode=mode, preset_filter=preset_filter)
            except Exception as exc:
                errors.append(f'{path}\n* {str(exc)}')
                return
        
        for path in paths:
            load(path, mode)
            mode = 'ADD'
        
        return errors


class NSOLVE_MT_NFlow_Import_Default_Config(bpy.types.Menu):
    bl_idname = 'NSOLVE_MT_NFlow_Import_Default_Config'
    bl_label = 'Import a default config'

    def draw(self, context):
        layout = self.layout
        
        layout.operator_context = 'EXEC_DEFAULT'
        
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        behavior_entry_display = nflow_config_workspace.behavior_entry_display
        
        is_configurable = (behavior_entry_display not in ('TOUR', 'HELP'))
        
        if is_configurable:
            layout.operator('nsolve.nflow_paste_config', icon='PASTEDOWN')
        
        metadata = UIMetadata.get(context)
        import_mode = metadata.get('import_mode', 'ADD')
        
        paths = NFlowBehaviorPresetsConfig.get_default_paths()
        
        for path in paths:
            directory, filename = os.path.split(path)
            text = os.path.splitext(filename)[0]
            op = layout.operator('nsolve.nflow_import_config', text=text)
            op.directory = directory
            op.files.clear()
            file = op.files.add()
            file.name = filename
            op.mode = import_mode
            op.preset_options.clear()


class NSOLVE_OT_NFlow_Reinit_Config(bpy.types.Operator):
    bl_idname = 'nsolve.nflow_reinit_config'
    bl_label = 'Load default config'
    bl_description = 'Load default config'
    bl_options = {'INTERNAL'}

    def execute(self, context):
        NFlowBehaviorPresetsConfig.initialize(reset=True)
        return {'FINISHED'}


def rna_enum_items(container, prop_name):
    return container.bl_rna.properties[prop_name].enum_items


def color_property(name, description, default):
    return bpy.props.FloatVectorProperty(name=name, description=description,
        size=len(default), subtype='COLOR', default=default, min=0.0, max=1.0)


class NFlowBehaviorPresetEntryOption(bpy.types.PropertyGroup):
    bool_value: bpy.props.BoolProperty(name='Option', description='Option')
    int_value: bpy.props.IntProperty(name='Option', description='Option')
    float_value: bpy.props.FloatProperty(name='Option', description='Option')
    string_value: bpy.props.StringProperty(name='Option', description='Option')

    def key_value_get(self):
        return event_key_map.get(self.string_value, 0)
    def key_value_set(self, value):
        self.string_value = event_key_map.get(value, 'NONE')
    key_value: bpy.props.EnumProperty(
        name='Option',
        description='Option',
        items=event_key_items,
        get=key_value_get,
        set=key_value_set,
    )

    def copy(self, other):
        self.name = other.name
        self.bool_value = other.bool_value
        self.int_value = other.int_value
        self.float_value = other.float_value
        self.string_value = other.string_value

    def serialize(self):
        data = {
            'name': self.name,
            'bool_value': self.bool_value,
            'int_value': self.int_value,
            'float_value': self.float_value,
            'string_value': self.string_value,
        }
        return data

    def deserialize(self, data):
        if not isinstance(data, dict):
            return
        
        def try_assign(name):
            try:
                setattr(self, name, data[name])
            except Exception:
                pass
        
        try_assign('name')
        try_assign('bool_value')
        try_assign('int_value')
        try_assign('float_value')
        try_assign('string_value')

    def initialize(self, idname, default):
        self.name = idname
        if isinstance(default, bool):
            self.bool_value = default
        elif isinstance(default, int):
            self.int_value = default
        elif isinstance(default, float):
            self.float_value = default
        elif isinstance(default, str):
            self.string_value = default

    def get_value(self, default, items=None):
        if items:
            if any((self.string_value == item[0]) for item in items):
                return self.string_value
        elif isinstance(default, bool):
            return self.bool_value
        elif isinstance(default, int):
            return self.int_value
        elif isinstance(default, float):
            return self.float_value
        elif isinstance(default, str):
            return self.string_value
        return default

    def draw(self, layout, label, default, items=None, event=False):
        if items:
            row = layout.row()
            
            subrow = row.row()
            subrow.alignment = 'LEFT'
            subrow.label(text=label+':')
            
            # Metadata values are converted to strings anyway
            UIMetadata.set(row, {'option_enum_items': json.dumps(items), 'option_idname': self.name})
            
            def find_name(idname):
                return next(iter(item[1] for item in items if item[0] == idname), None)
            item_name = find_name(self.string_value) or find_name(default)
            
            row.menu('NSOLVE_MT_NFlow_Choose_Behavior_Preset_Entry_Option_Enum', text=item_name)
        elif event:
            row = layout.row()
            row.label(text=label)
            row.prop(self, 'key_value', text='', event=True)
        elif isinstance(default, bool):
            layout.prop(self, 'bool_value', text=label)
        elif isinstance(default, int):
            layout.prop(self, 'int_value', text=label)
        elif isinstance(default, float):
            layout.prop(self, 'float_value', text=label)
        elif isinstance(default, str):
            layout.prop(self, 'string_value', text=label)


class NFlowBehaviorPresetEntry(bpy.types.PropertyGroup):
    option_names = [
        'highlight',
        'select_push_undo',
        'select_after',
        'select_lock_element_type',
        'selection_mode',
        'select_first_vertex',
        'select_last_vertex',
        'ensure_element_selection',
        'cursor_3d_snap',
    ]

    enable: bpy.props.BoolProperty(
        name='Enable',
        description='Quickly toggle on/off this behavior',
        default=True,
    )

    is_expanded: bpy.props.BoolProperty(
        name='Fold/expand',
        description='Click to show additional properties',
        default=False,
    )

    highlight: bpy.props.BoolProperty(
        name='Highlight',
        description='Highlight mesh elements when this behavior is active',
        default=True,
    )

    select_push_undo: bpy.props.BoolProperty(
        name='Record undo',
        description='Record an Undo step before invoking the operator',
        default=True,
    )

    select_after: bpy.props.BoolProperty(
        name='Select after',
        description='Select elements after releasing the mouse button',
        default=False,
    )

    select_lock_element_type: bpy.props.BoolProperty(
        name='Lock element type',
        description='Select only the same type of elements',
        default=True,
    )

    selection_mode: bpy.props.EnumProperty(name='Selection mode', description='Selection mode',
        items=[
            ('OVERRIDE', 'Override', 'Override the existing selection'),
            ('SEMI_OVERRIDE', 'Semi-override', 'Override if elements are not in the existing selection'),
            ('ADD', 'Add', 'Add elements to the existing selection'),
            ('TOGGLE', 'Toggle', 'Toggle the selection state of elements'),
            ('REMOVE', 'Remove', 'Remove elements from the existing selection'),
            ('KEEP', 'Keep', 'Keep the existing selection'),
        ],
    )

    select_first_vertex: bpy.props.BoolProperty(
        name='Ensure first vertex',
        description='Make sure the first item in selection history is a vertex',
        default=False,
    )

    select_last_vertex: bpy.props.BoolProperty(
        name='Ensure last vertex',
        description='Make sure the last item in selection history is a vertex',
        default=False,
    )

    ensure_element_selection: bpy.props.EnumProperty(
        name='Ensure selection mode',
        description='Make sure the selection mode for the corresponding element(s) is enabled',
        items=[
            ('VERT', 'Vertex', 'Enable vertex selection mode', 'VERTEXSEL', 1 << 0),
            ('EDGE', 'Edge', 'Enable edge selection mode', 'EDGESEL', 1 << 1),
            ('FACE', 'Face', 'Enable face selection mode', 'FACESEL', 1 << 2),
            ('ADDITIVE', 'Additive', 'Expand the selection mode (rather than override)', 'PLUS', 1 << 3),
        ],
        default=set(),
        options={'ENUM_FLAG'},
    )

    cursor_3d_snap: bpy.props.BoolProperty(
        name='Snap 3D Cursor',
        description='Snap 3D cursor to the surface',
        default=False,
    )

    event: bpy.props.EnumProperty(name='Event', description='Invocation event',
        items=[
            ('LEFTMOUSE', 'LMB', 'Left mouse button', 'MOUSE_LMB', 0),
            ('MIDDLEMOUSE', 'MMB', 'Middle mouse button', 'MOUSE_MMB', 1),
            ('RIGHTMOUSE', 'RMB', 'Right mouse button', 'MOUSE_RMB', 2),
        ],
    )

    modifiers: bpy.props.EnumProperty(name='Modifiers', description='Invocation modifiers',
        items=[
            ('SHIFT', 'Shift', 'Shift', 'EVENT_SHIFT', 1 << 0),
            ('CTRL', 'Ctrl', 'Ctrl', 'EVENT_CTRL', 1 << 1),
            ('ALT', 'Alt', 'Alt', 'EVENT_ALT', 1 << 2),
        ],
        options={'ENUM_FLAG'},
    )

    elements: bpy.props.EnumProperty(name='Elements', description='Target elements',
        items=[
            ('NONE', 'Empty', 'Empty (no elements are highlighted)', 'RADIOBUT_OFF', 1 << 0),
            ('VERTEX', 'Vertex', 'Vertex', 'VERTEXSEL', 1 << 1),
            ('EDGE', 'Edge', 'Edge', 'EDGESEL', 1 << 2),
            ('EDGE_LOOP', 'Edge loop', 'Edge loop', 'SNAP_MIDPOINT', 1 << 3),
            ('BOUNDARY', 'Boundary loop', 'Boundary loop', 'MESH_GRID', 1 << 4),
            ('PERIMETER', 'Face perimeter', 'Face perimeter', 'OUTLINER_OB_MESH', 1 << 5),
            ('FACE', 'Face', 'Face', 'FACESEL', 1 << 6),
        ],
        options={'ENUM_FLAG'},
        default={'NONE', 'VERTEX', 'EDGE', 'EDGE_LOOP', 'BOUNDARY', 'PERIMETER', 'FACE'},
    )

    def on_behavior_update(self, context):
        BehaviorPresetEntryItems.add_recent(self.behavior)
        
        self.options.clear()
        
        command, args = parse_operator_command(self.behavior)
        behavior_info = NFlow.behaviors.get(command)
        
        if not behavior_info:
            return
        
        options = behavior_info.get('options')
        if not isinstance(options, list):
            return
        
        for option_info in options:
            idname = option_info['idname']
            value = option_info['default']
            option = self.options.add()
            option.initialize(idname, value)

    behavior: bpy.props.StringProperty(
        name='Behavior',
        description='Which tool / behavior to invoke',
        update=on_behavior_update,
        maxlen=4096, # operator arguments may potentially get really long
    )

    name: bpy.props.StringProperty(
        name='Custom name',
        description='If not empty, will be used instead of the default name',
    )

    options: bpy.props.CollectionProperty(type=NFlowBehaviorPresetEntryOption)

    def gather_options(self):
        command, args = parse_operator_command(self.behavior)
        behavior_info = NFlow.behaviors.get(command)
        if not behavior_info:
            return None
        
        eval_options = []
        
        options = behavior_info.get('options')
        if isinstance(options, list):
            for option_info in options:
                idname = option_info['idname']
                value = option_info['default']
                option = self.find_option(idname)
                if option is not None:
                    value = option.get_value(value, option_info.get('items'))
                else:
                    option = self.options.add()
                    option.initialize(idname, value)
                eval_options.append(dict(value=value, option=option, **option_info))
        
        options_descriptor = dict(
            command=command,
            option_infos=eval_options,
            options_draw=behavior_info.get('options_draw'),
            settings_label=behavior_info.get('settings_label', ''),
            settings_draw=behavior_info.get('settings_draw'),
            settings_draw_fold=behavior_info.get('settings_draw_fold', False),
            settings_order=behavior_info.get('settings_order', 0),
        )
        
        return options_descriptor

    def find_option(self, idname):
        for option in self.options:
            if option.name == idname:
                return option
        return None

    def is_operator(self):
        command, args = parse_operator_command(self.behavior, True)
        op = get_operator(command)
        return (op is not None)

    def is_behavior(self):
        command, args = parse_operator_command(self.behavior)
        behavior_info = NFlow.behaviors.get(command)
        return bool(behavior_info) and (not args)

    def copy(self, other):
        self.enable = other.enable
        self.event = other.event
        self.modifiers = other.modifiers
        self.elements = other.elements
        self.behavior = other.behavior
        self.name = other.name
        
        for option_name in self.option_names:
            setattr(self, option_name, getattr(other, option_name))
        
        for other_option in other.options:
            self_option = self.options.add()
            self_option.copy(other_option)

    def serialize(self):
        data = {
            'name': self.name,
            'enable': self.enable,
            'event': self.event,
            'modifiers': self.modifiers,
            'elements': self.elements,
            'behavior': self.behavior,
        }
        for option_name in self.option_names:
            data[option_name] = getattr(self, option_name)
        data['options'] = [option.serialize() for option in self.options]
        return data

    def deserialize(self, data):
        if not isinstance(data, dict):
            return
        
        def try_assign(name):
            try:
                setattr(self, name, data[name])
            except Exception:
                pass
        
        try_assign('name')
        try_assign('enable')
        try_assign('event')
        try_assign('modifiers')
        try_assign('elements')
        try_assign('behavior')
        
        for option_name in self.option_names:
            try_assign(option_name)
        
        options = data.get('options')
        if options:
            def find_option(name):
                for option in self.options:
                    if option.name == name:
                        return option
            
            for option_data in options:
                option = find_option(option_data['name'])
                if option is not None:
                    option.deserialize(option_data)

    def draw(self, layout, index, shortcuts):
        context = bpy.context
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        behavior_entry_display = nflow_config_workspace.behavior_entry_display
        
        is_configurable = (behavior_entry_display not in ('TOUR', 'HELP'))
        
        box = None
        
        if not is_configurable:
            full_name = not NFlowPrefs.get('behavior_shorten_name')
            
            command, args = parse_operator_command(self.behavior, True)
            info = NFlow.behaviors.get(command, None) or get_operator(command)
            
            if not info:
                return
            
            is_active = True
            if behavior_entry_display == 'HELP':
                help_state = self.get_help_state()
                if help_state is None:
                    return
                is_active = help_state
            
            text = NFlow.get_behavior_name(self, info, full_name)
            
            box = layout.box()
            box.active = self.enable
            
            row = box.row()
            row.active = is_active
            row.use_property_decorate = False
            row.use_property_split = False
            
            subrow = row.row()
            subrow.alignment = 'LEFT'
            if behavior_entry_display == 'HELP':
                subrow.label(text=text)
            else:
                subrow.prop(self, 'is_expanded', text=text, toggle=True, emboss=False)
            
            subrow = row.row(align=True)
            subrow.alignment = 'RIGHT'
            self.draw_elements(subrow, index, locked=True)
            self.draw_shortcut(subrow, index, locked=True)
            
            if (not self.is_expanded) or (behavior_entry_display == 'HELP'):
                return
        
        single_line = (not self.enable) or (behavior_entry_display != 'FULL')
        
        is_behavior = self.is_behavior()
        is_operator = (not is_behavior) and self.is_operator()
        
        behavior_info = NFlow.behaviors.get(self.behavior, {})
        elements = behavior_info.get('elements', ())
        
        is_overridden = False
        if self.enable:
            shortcut_key = (tuple(sorted(self.modifiers)), self.event)
            shortcut_elements = shortcuts.setdefault(shortcut_key, set())
            shortcut_elements_count = len(shortcut_elements)
            total_count = 0
            for item in rna_enum_items(self, 'elements'):
                element_usable = is_operator or (is_behavior and (item.identifier in elements))
                if element_usable and (item.identifier in self.elements):
                    shortcut_elements.add(item.identifier)
                    total_count += 1
            count_added = len(shortcut_elements) - shortcut_elements_count
            is_overridden = (total_count > 0) and (count_added == 0)
        
        is_error = bool(self.behavior) and (not (is_behavior or is_operator))
        is_error |= is_overridden
        
        self['is_error'] = is_error
        
        if box is None:
            box = layout.box()
        
        # It was requested that 'alert' state should be shown only if entry is enabled
        box.alert = is_error and self.enable
        
        row_main = box.row()
        
        if is_configurable:
            col_main = row_main.column(align=True)
            if single_line:
                col_main.scale_y = 0.5
            op = col_main.operator('nsolve.nflow_move_behavior_preset_entry', text='', icon='TRIA_UP')
            op.index = index
            op.new_index = index - 1
            op = col_main.operator('nsolve.nflow_move_behavior_preset_entry', text='', icon='TRIA_DOWN')
            op.index = index
            op.new_index = index + 1
        
        col_main = row_main.column(align=True)
        
        col_main.context_pointer_set('nflow_preset_entry', self)
        
        UIMetadata.set(col_main, {'index': index})
        
        main_row = col_main.row()
        main_row.use_property_decorate = False
        main_row.use_property_split = False
        
        row = main_row.row(align=True)
        row.alignment = 'LEFT'
        
        row.prop(self, 'enable', text='')
        
        if single_line:
            row = main_row.row()
            row.enabled = self.enable
            
            if self.enable:
                if not is_configurable:
                    row.popover('NSOLVE_PT_NFlow_Preset_Entry_Options', text='', icon='TOOL_SETTINGS')
                
                self.draw_command(row, can_edit=is_configurable)
                
                if behavior_entry_display == 'SHORTCUT':
                    self.draw_shortcut(main_row, index)
                
                if is_configurable:
                    row.popover('NSOLVE_PT_NFlow_Preset_Entry_Options', text='', icon='TOOL_SETTINGS')
            else:
                row.prop(self, 'behavior', text='')
            
            if is_configurable:
                row = main_row.row()
                row.alignment = 'RIGHT'
                op = row.operator('nsolve.nflow_remove_behavior_preset_entry', text='', icon='X')
                op.index = index
            else:
                # This is slightly shorter than separator.
                # scale_y and ui_units_y have no effect here, for some reason.
                box.row(align=True)
            
            return
        
        self.draw_shortcut(main_row, index)
        
        self.draw_elements(main_row, index)
        
        self.draw_extras(main_row, index)
        
        row = main_row.row()
        op = row.operator('nsolve.nflow_remove_behavior_preset_entry', text='', icon='X')
        op.index = index
        
        main_row = col_main.row()
        main_row.use_property_decorate = False
        main_row.use_property_split = False
        
        self.draw_command(main_row, can_edit=is_configurable)
        
        row = main_row.row()
        row.popover('NSOLVE_PT_NFlow_Preset_Entry_Options', text='', icon='TOOL_SETTINGS')

    def get_help_state(self):
        if not NFlow.ui_cheatsheet:
            return
        
        active_entry = None
        active_info = NFlow.ui_cheatsheet['active']
        if active_info:
            active_entry = active_info['entry']
            if not is_valid(active_entry):
                active_entry = None
        
        for info in NFlow.ui_cheatsheet['infos']:
            entry = info['entry']
            if is_valid(entry) and (entry == self):
                return (active_entry is None) or (active_entry == self)

    def draw_command(self, layout, can_edit=True):
        row = layout.row()
        row.active = self.enable
        
        cmd_row = row.row(align=True)
        
        if can_edit:
            cmd_row.menu('NSOLVE_MT_NFlow_Choose_Behavior_Preset_Entry', text='', icon='DOWNARROW_HLT')
        
        cmd_subrow = cmd_row.row(align=True)
        cmd_subrow.enabled = can_edit
        
        if can_edit:
            wm = bpy.context.window_manager
            cmd_subrow.prop_search(self, 'behavior',
                wm.nsolve.ops.nflow, 'behavior_search_candidates',
                text='', results_are_suggestions=True)
        else:
            cmd_subrow.prop(self, 'behavior', text='')

    def draw_shortcut(self, layout, index, alignment='LEFT', locked=False):
        row = layout.row(align=True)
        row.alignment = alignment
        row.active = self.enable
        
        if locked:
            for item in rna_enum_items(self, 'modifiers'):
                if item.identifier in self.modifiers:
                    row.label(icon=item.icon)
            for item in rna_enum_items(self, 'event'):
                if item.identifier == self.event:
                    row.label(icon=item.icon)
            return
        
        for item in rna_enum_items(self, 'modifiers'):
            row.prop_enum(self, 'modifiers', item.identifier, text='')
        
        row.prop(self, 'event', text='', icon_only=True)

    def draw_elements(self, layout, index, alignment='CENTER', locked=False):
        behavior_info = NFlow.behaviors.get(self.behavior, {})
        
        is_behavior = self.is_behavior()
        is_operator = (not is_behavior) and self.is_operator()
        
        elements = behavior_info.get('elements', ())
        
        def has_element(element):
            return is_operator or (is_behavior and (element in elements))
        
        row = layout.row(align=True)
        row.alignment = alignment
        row.active = self.enable
        
        if locked:
            for item in rna_enum_items(self, 'elements'):
                if has_element(item.identifier) and (item.identifier in self.elements):
                    row.label(icon=item.icon)
            return
        
        for item in rna_enum_items(self, 'elements'):
            subrow = row.row(align=True)
            subrow.active = has_element(item.identifier)
            subrow.prop_enum(self, 'elements', item.identifier, text='')

    def draw_extras(self, layout, index, alignment='RIGHT', locked=False):
        row = layout.row()
        row.alignment = alignment
        
        row.prop(self, 'highlight', text='', icon='HIDE_OFF')
        
        if not locked:
            op = row.operator('nsolve.nflow_duplicate_behavior_preset_entry', text='', icon='DUPLICATE')
            op.index = index


class NFlowBehaviorPreset(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name='Preset name')

    use_override_color: bpy.props.BoolProperty(
        name='Override',
        description='Override the color',
        default=False,
    )
    override_color: color_property('Override color', 'Override color', (1,1,1))

    # color_overrides: bpy.props.EnumProperty(
    #     name='Color overrides',
    #     description='Override',
    #     items=[
    #         ('ENABLE', 'Enable', 'Use overridden colors'),
    #         ('VERTEX', 'Vertex', 'Override vertex color'),
    #         ('EDGE', 'Edge', 'Override edge color'),
    #         ('EDGE_LOOP', 'Edge Loop', 'Override edge loop color'),
    #         ('BOUNDARY', 'Boundary', 'Override boundary color'),
    #         ('PERIMETER', 'Perimeter', 'Override perimeter color'),
    #         ('FACE', 'Face', 'Override face color'),
    #     ],
    #     default={'ENABLE'},
    #     options={'ENUM_FLAG'},
    # )
    # color_vertex: color_property('Vertex', 'Vertex highlight color', (1,0,0,1))
    # color_edge: color_property('Edge', 'Edge highlight color', (0,1,0,1))
    # color_edge_loop: color_property('Edge loop', 'Edge loop highlight color', (1,1,0,1))
    # color_boundary: color_property('Boundary loop', 'Boundary loop highlight color', (0.75,0.0,0.75,1))
    # color_perimeter: color_property('Face perimeter', 'Face perimeter highlight color', (0,0.75,0.75,1))
    # color_face: color_property('Face', 'Face highlight color', (0,0,1,0.5))

    entries: bpy.props.CollectionProperty(type=NFlowBehaviorPresetEntry)

    def get_index(self):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get()
        
        behavior_presets = behavior_presets_config.behavior_presets
        for i, behavior_preset in enumerate(behavior_presets):
            if behavior_preset == self:
                return i
        return -1

    def set_index(self, value):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get()
        
        behavior_presets = behavior_presets_config.behavior_presets
        value = min(max(value, 0), len(behavior_presets)-1)
        index = self.index
        behavior_presets.move(index, value)
        if index == behavior_presets_config.behavior_preset_active:
            behavior_presets_config.behavior_preset_active = value

    index: bpy.props.IntProperty(
        name='Index',
        description='Order in the list',
        get=get_index,
        set=set_index,
    )

    def get_is_active(self):
        behavior_presets_config = NFlowBehaviorPresetsConfig.get()
        return (self == behavior_presets_config.get_active_preset())

    def set_is_active(self, value):
        if value:
            behavior_presets_config = NFlowBehaviorPresetsConfig.get()
            behavior_presets_config.set_active_preset(self)

    is_active: bpy.props.BoolProperty(
        name='Activate',
        description='Activate this preset',
        get=get_is_active,
        set=set_is_active,
    )

    def serialize(self):
        data = {}
        data['name'] = self.name
        data['entries'] = [entry.serialize() for entry in self.entries]
        data['use_override_color'] = self.use_override_color
        data['override_color'] = tuple(self.override_color)
        return data

    def deserialize(self, data, mode='OVERWRITE'):
        if not isinstance(data, dict):
            return
        
        name = data.get('name')
        entries = data.get('entries')
        use_override_color = data.get('use_override_color')
        override_color = data.get('override_color')
        
        if isinstance(use_override_color, bool):
            self.use_override_color = use_override_color
        else:
            self.use_override_color = False
        
        if isinstance(override_color, (list, tuple)) and (len(override_color) == 3):
            self.override_color = tuple(override_color)
        else:
            self.override_color = (1, 1, 1)
        
        self.name = (name if isinstance(name, str) else '<No name>')
        
        if mode != 'ADD':
            self.entries.clear()
        
        if entries and isinstance(entries, list):
            for entry_data in entries:
                entry = self.entries.add()
                entry.deserialize(entry_data)

    @classmethod
    def read_name_and_count(cls, data):
        if not isinstance(data, dict):
            return None, 0
        
        name = data.get('name')
        entries = data.get('entries')
        
        name = (name if isinstance(name, str) else '<No name>')
        count = (len(entries) if entries and isinstance(entries, list) else 0)
        
        return name, count


class NFlowBehaviorFilter(bpy.types.PropertyGroup):
    show: bpy.props.BoolProperty(
        name='Show',
        description='Show this category in the list',
        default=True,
    )

    name: bpy.props.StringProperty(name='Category name',
        description='Name of the operator category this filter would apply to')

    filter: bpy.props.StringProperty(name='Filter',
        description='Name patterns to include (or exclude, if starting with !)')


class NFlowBehaviorPresetsConfig(bpy.types.PropertyGroup):
    @classmethod
    def get(cls, context=None):
        if context is None:
            context = bpy.context
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        return nflow_config_workspace.behavior_presets_config

    is_initialized: bpy.props.BoolProperty(
        default=False,
        options={'HIDDEN'},
    )

    def on_behavior_preset_active_update(self, context):
        if context is None:
            return
        
        if context.area is not None:
            context.area.tag_redraw()
        
        wm = context.window_manager
        if wm is not None:
            for window in wm.windows:
                for area in window.screen.areas:
                    area.tag_redraw()

    behavior_preset_active: bpy.props.IntProperty(
        update=on_behavior_preset_active_update,
    )

    behavior_presets: bpy.props.CollectionProperty(type=NFlowBehaviorPreset)

    behavior_default_enable: bpy.props.BoolProperty(
        name='All elements',
        description='Enable all elements by default',
        default=True,
    )

    def clamp_active_index(self):
        active_index = min(max(self.behavior_preset_active, 0), len(self.behavior_presets)-1)
        self.behavior_preset_active = active_index
        return active_index

    def get_active_preset(self):
        active_index = min(max(self.behavior_preset_active, 0), len(self.behavior_presets)-1)
        return (self.behavior_presets[active_index] if active_index >= 0 else None)

    def set_active_preset(self, active_preset):
        for index, behavior_preset in enumerate(self.behavior_presets):
            if behavior_preset == active_preset:
                self.behavior_preset_active = index
                return
        self.behavior_preset_active = -1

    def serialize(self, mode='ALL'):
        active_preset = self.get_active_preset()
        
        data = {'version': (1, 0, 0)}
        
        if mode == 'ALL':
            data['presets'] = [preset.serialize() for preset in self.behavior_presets]
            data['active'] = self.behavior_preset_active
        elif active_preset:
            data['presets'] = [active_preset.serialize()]
            data['active'] = 0
        
        return data

    def deserialize(self, data, mode='ADD', preset_filter=None):
        if not isinstance(data, dict):
            return
        
        presets = data.get('presets')
        if not (presets and isinstance(presets, list)):
            return
        
        if preset_filter:
            presets = preset_filter(presets)
        
        if mode == 'ADD':
            self.clamp_active_index()
            for preset_data in presets:
                behavior_preset = self.behavior_presets.add()
                behavior_preset.deserialize(preset_data)
        else:
            self.behavior_presets.clear()
            for preset_data in presets:
                behavior_preset = self.behavior_presets.add()
                behavior_preset.deserialize(preset_data)
            
            active_index = data.get('active')
            if not isinstance(active_index, int):
                active_index = 0
            self.behavior_preset_active = active_index
        
        self.is_initialized = True

    @classmethod
    def read_preset_names(cls, data):
        if not isinstance(data, dict):
            return None
        
        presets = data.get('presets')
        if not (presets and isinstance(presets, list)):
            return None
        
        result = []
        
        for preset_data in presets:
            name, count = NFlowBehaviorPreset.read_name_and_count(preset_data)
            if name is not None:
                result.append(name)
        
        return result

    @classmethod
    def get_default_paths(cls, single=False):
        presets_path = NFlowPrefs.get('default_presets_path')
        presets_path = bpy.path.abspath(presets_path)
        
        default_dir = (Path(__file__).parent.parent.parent.parent / 'config').as_posix()
        default_file = 'Defaults.ntx'
        
        if os.path.isfile(presets_path):
            presets_dir, presets_file = os.path.split(presets_path)
        elif os.path.isdir(presets_path):
            presets_dir, presets_file = presets_path, ''
        else:
            presets_dir, presets_file = default_dir, default_file
        
        if single:
            preset_path = os.path.join(presets_dir, presets_file)
            if not os.path.isfile(preset_path):
                preset_path = os.path.join(default_dir, default_file)
            return ([preset_path] if os.path.isfile(preset_path) else [])
        
        if not os.path.isdir(presets_dir):
            presets_dir = default_dir
        
        pattern = os.path.join(presets_dir, '*.ntx')
        return (glob.glob(pattern) if os.path.isdir(presets_dir) else [])

    @classmethod
    def initialize(cls, reset=False):
        paths = cls.get_default_paths(single=True)
        
        if not paths:
            return
        
        for workspace in bpy.data.workspaces:
            nflow_config_workspace = workspace.nsolve.ops.nflow
            behavior_presets_config = nflow_config_workspace.behavior_presets_config
            
            if not reset:
                if behavior_presets_config.is_initialized:
                    continue
                
                if len(behavior_presets_config.behavior_presets) > 0:
                    continue
            
            errors = NSOLVE_OT_NFlow_Import_Config.load(behavior_presets_config, paths)
            
            if errors:
                print('\n'.join(errors))

    @classmethod
    def on_load(cls, scene):
        cls.initialize()

    def draw_add_preset(self, layout, text, copy_active=False, menu_only=False):
        op_name = 'nsolve.nflow_add_behavior_preset'
        menu_name = 'NSOLVE_MT_NFlow_Import_Default_Config'
        
        if menu_only:
            layout.menu(menu_name, text=text, icon='ADD')
            return
        
        if copy_active:
            op = layout.operator(op_name, text=text, icon='DUPLICATE')
        else:
            op = layout.operator_menu_hold(op_name, text=text, icon='ADD', menu=menu_name)
        op.copy_active = copy_active

    def draw(self, layout, place=None):
        main_col = layout.column(align=True)
        
        active_index = min(max(self.behavior_preset_active, 0), len(self.behavior_presets)-1)
        behavior_preset = (self.behavior_presets[active_index] if active_index >= 0 else None)
        
        context = bpy.context
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        behavior_entry_display = nflow_config_workspace.behavior_entry_display
        
        is_configurable = (behavior_entry_display not in ('TOUR', 'HELP'))
        
        row = main_col.row()
        
        if behavior_preset is None:
            subrow = row.row(align=True)
            subrow.operator('nsolve.nflow_reinit_config', text='Load defaults', icon='AUTO')
            text = ('New preset' if is_configurable else 'Add a preset')
            self.draw_add_preset(subrow, text=text, menu_only=(not is_configurable))
            # row.popover('NSOLVE_PT_NFlow_Config_Options', text='', icon='PREFERENCES')
            row.popover('NSOLVE_PT_NFlow_Global_Options', text='', icon='PREFERENCES')
            return
        
        self.draw_add_preset(row, text='', menu_only=(not is_configurable))
        
        subrow = row.row(align=True)
        subrow.use_property_decorate = False
        subrow.use_property_split = False
        subrow.menu('NSOLVE_MT_NFlow_Select_Behavior_Preset', text='', icon='DOWNARROW_HLT')
        subrow.prop(behavior_preset, 'name', text='')
        
        op = subrow.operator('nsolve.nflow_remove_behavior_preset', text='', icon='X')
        op.index = active_index
        
        subrow.popover('NSOLVE_PT_NFlow_Preset_Colors', text='', icon='COLOR')
        
        if is_configurable:
            subrow = row.row(align=True)
            self.draw_add_preset(subrow, text='', copy_active=True)
            
            subrow = row.row(align=True)
            subrow.use_property_decorate = False
            subrow.use_property_split = False
            subrow.ui_units_x = 2
            subrow.prop(behavior_preset, 'index', text='')
        
        if place in ('HELPER', 'POPOVER'):
            row.prop(nflow_config_workspace, 'behavior_entry_display_toggle', text='', icon='INFO')
        
        # row.popover('NSOLVE_PT_NFlow_Config_Options', text='', icon='PREFERENCES')
        row.popover('NSOLVE_PT_NFlow_Global_Options', text='', icon='PREFERENCES')
        
        main_col.separator()
        
        shortcuts = {}
        
        for i, entry in enumerate(behavior_preset.entries):
            entry.draw(main_col, i, shortcuts)
        
        if is_configurable:
            row = main_col.row(align=True)
            row.alignment = 'CENTER'
            row.operator('nsolve.nflow_add_behavior_preset_entry', text='Add behavior', icon='ADD')
            row.prop(self, 'behavior_default_enable', text='', icon='MESH_DATA')


class NFlowBehaviorSearchCandidate(bpy.types.PropertyGroup):
    pass # we just need a name, which is automatically added


class types():
    class preferences(bpy.types.PropertyGroup):
        current_tab: bpy.props.EnumProperty(
            name='Tab',
            description='Which settings to display',
            items=[
                ('UI', 'UI', ''),
                ('VIEWPORT', 'Viewport', ''),
                ('PRESETS', 'Presets', ''),
                ('INPUT', 'Input', ''),
            ],
            default='UI',
        )

        default_presets_path: bpy.props.StringProperty(
            name='Default presets path',
            description='Path to the default preset directory or file\n' +
                '(if not found, will use a built-in one)',
            default='',
            maxlen=4096,
            subtype='FILE_PATH',
        )

        snap_radius: bpy.props.IntProperty(
            name='Snapping radius',
            description='Limit the screen-space distance within which snapping would happen',
            default=32,
            min=0,
            subtype='PIXEL',
        )

        merge_radius: bpy.props.FloatProperty(
            name='Merging radius',
            description='Vertex merging radius (in the local space of the mesh)',
            default=1e-5,
            min=0,
            step=1,
            precision=6,
        )

        use_specialized_cursors: bpy.props.BoolProperty(
            name='Use specialized cursors',
            description='Use specialized cursors to indicate the type of current behavior. WARNING: may persist outside of the tool',
            default=False,
        )

        hover_text_enabled: bpy.props.BoolProperty(
            name='Show hover text',
            description='Show hover text next to the mouse',
            default=True,
        )
        hover_text_anchor: bpy.props.FloatVectorProperty(
            name='Hover text anchor',
            description='Relative offset of the hover text from the mouse position',
            default=(0.5, 4.0),
            size=2,
        )
        hover_text_size: bpy.props.IntProperty(
            name='Hover text size',
            description='Size of the hover text in viewport',
            default=15,
            min=10,
            max=100,
        )

        help_text_enabled: bpy.props.BoolProperty(
            name='Show help text',
            description='Show help text in the 3D viewport',
            default=True,
        )
        help_text_anchor: bpy.props.FloatVectorProperty(
            name='Help text anchor',
            description='Relative offset of the help text from the viewport edges',
            default=(0.94, 0.97),
            size=2,
        )
        help_text_size: bpy.props.IntProperty(
            name='Help text size',
            description='Size of the help text in viewport',
            default=15,
            min=10,
            max=100,
        )
        help_text_spacing: bpy.props.IntProperty(
            name='Help text spacing',
            description='Distance between individual lines',
            default=8,
            min=0,
        )

        text_color: color_property('Text color', 'Hover text color', (1,1,1,1))
        text_background: color_property('Text background', 'Hover text background', (0,0,0,0.5))

        edge_loop_fraction: bpy.props.FloatProperty(
            name='Edge loop fraction',
            description='Fraction of an edge beyond which an edge loop gets highlighted instead',
            default=1.0/3.0,
            min=0,
            max=1,
        )

        vert_radius_base: bpy.props.FloatProperty(
            name='Vertex radius',
            description='Radius of vertex highlight (in pixels)',
            default=10,
            min=1,
            step=100,
            subtype='PIXEL',
        )

        vert_outline_width: bpy.props.FloatProperty(
            name='Vertex outline',
            description='Thickness of vertex outline (if 0, will be drawn as solid)',
            default=3,
            min=0,
        )

        edge_radius_base: bpy.props.FloatProperty(
            name='Edge thickness',
            description='Thickness of edge highlight (in pixels)',
            default=4,
            min=1,
            step=100,
            subtype='PIXEL',
        )

        edge_radius_ext: bpy.props.FloatProperty(
            name='Boundary thickness',
            description='Thickness of boundary detection (relative to edge thickness)',
            default=2,
            min=1,
        )

        occluded_alpha: bpy.props.FloatProperty(
            name='Occluded alpha',
            description='Draw highlight with this alpha when it\'s occluded by scene geometry',
            default=0.5,
            min=0,
            max=1,
        )

        color_vertex: color_property('Vertex', 'Vertex highlight color', (1,0,0,1))
        color_edge: color_property('Edge', 'Edge highlight color', (0,1,0,1))
        color_edge_loop: color_property('Edge loop', 'Edge loop highlight color', (1,1,0,1))
        color_boundary: color_property('Boundary loop', 'Boundary loop highlight color', (0.75,0.0,0.75,1))
        color_perimeter: color_property('Face perimeter', 'Face perimeter highlight color', (0,0.75,0.75,1))
        color_face: color_property('Face', 'Face highlight color', (0,0,1,0.2))

        vertex_overlay_use_custom_colors: bpy.props.BoolProperty(
            name='Vertex overlay custom colors',
            description='Use custom colors for vertex overlay',
            default=False,
        )
        vertex_overlay_unselected: color_property('Vertex overlay (unselected)', 'Overlay color', (0,0,0,1))
        vertex_overlay_selected: color_property('Vertex overlay (selected)', 'Overlay color', (1,0.5,0,1))
        vertex_overlay_radius: bpy.props.FloatProperty(
            name='Vertex overlay radius',
            description='Radius of vertex overlay (in pixels)',
            default=4,
            min=1,
            step=100,
            subtype='PIXEL',
        )
        vertex_overlay_depth_bias: bpy.props.FloatProperty(
            name='Vertex overlay depth bias',
            description='Extra offset used to draw vertex overlay in front of other geometry',
            default=0.01,
            min=0,
        )

        default_color_retopology: color_property('Retopology', 'Default color for the Retopology mode', (0.314, 0.784, 1.0, 0.06))
        
        use_color_retopology: bpy.props.BoolProperty(
            name='Override Retopology color',
            description='Use custom colors for Retopology mode',
            default=True,
        )
        color_retopology: color_property('Retopology',
            'Default color for the Retopology mode', (0.314, 0.784, 1.0, 0.06))

        show_panel: bpy.props.BoolProperty(
            name='Show panel in 3D View',
            description='Enable the panel in the 3D View sidebar',
            default=True,
        )

        behavior_shorten_name: bpy.props.BoolProperty(
            name='Shorter names',
            description='Display a more compact version of behavior names in the hover text',
            default=True,
        )
        help_text_show_all: bpy.props.EnumProperty(
            name='Shortcuts',
            description='Whether the help text should display all shortcuts, or only the currently relevant ones',
            items=[
                ('ALL', 'All', 'Always show all shortcuts'),
                ('APPLICABLE', 'Applicable', 'Show all shortcuts applicable in the current context'),
                ('MODIFIERS', 'Modifiers', 'Relevant only if modifier(s) are held, applicable otherwise'),
                ('RELEVANT', 'Relevant', 'Always show only relevant shortcuts'),
            ],
            default='MODIFIERS',
        )

        behavior_preset_use_number_shortcuts: bpy.props.BoolProperty(
            name='Use numeric shortcuts',
            description='Use the number keys to switch between presets',
            default=False,
        )

        behavior_preset_scroll_enable: bpy.props.BoolProperty(
            name='Scroll behaviors',
            description='Enable scrolling through presets via mousewheel + modifier(s)',
            default=True,
        )
        behavior_preset_scroll_modifiers: bpy.props.EnumProperty(
            name='Modifiers',
            description='Which modifiers should be used for preset scrolling',
            items=[
                ('shift', 'Shift', 'Shift'),
                ('ctrl', 'Ctrl', 'Ctrl'),
                ('alt', 'Alt', 'Alt'),
            ],
            default={'alt'},
            options={'ENUM_FLAG'},
        )
        behavior_preset_scroll_invert: bpy.props.BoolProperty(
            name='Invert scroll',
            description='Invert the direction of preset scrolling',
            default=False,
        )

        presets_width_limit: bpy.props.FloatProperty(
            name='Presets width limit',
            description='Max width of presets in tool header (relative to area width)',
            default=45,
            min=0,
            max=100,
            subtype='PERCENTAGE',
            precision=0,
        )

        topbar_extras_display: bpy.props.EnumProperty(
            name='Topbar extras',
            description='Which additional items to display in the tool header',
            items=[
                ('SCROLL', 'Scroll', 'Show the preset scroll toggle'),
                ('OVERLAY', 'Overlay', 'Show the overlay controls'),
                ('SNAPPING', 'Snapping', 'Show the snapping / auto-shrinkwrap controls'),
            ],
            default={'SCROLL', 'OVERLAY', 'SNAPPING'},
            options={'ENUM_FLAG'},
        )

        behavior_entry_display: bpy.props.EnumProperty(
            name='Default display mode',
            description='Initial mode for how behaviors will be shown in Blender UI',
            items=[
                ('TOUR', 'Tour', 'A mode for those who use only pre-defined configs'),
                ('SIMPLE', 'Simple', 'Show behavior name (command)'),
                ('SHORTCUT', 'Shortcut', 'Show behavior name (command) and its shortcut'),
                ('FULL', 'Full', 'Show full UI'),
                ('HELP', 'Help', 'Show the currently applicable configuration (non-editable)'),
            ],
            default='TOUR',
        )

        behavior_filters_initialized: bpy.props.BoolProperty()
        behavior_filter_all: bpy.props.BoolProperty(
            name='Show by default',
            description='Show all by default, unless explicitly filtered',
            default=True,
        )
        behavior_filters: bpy.props.CollectionProperty(type=NFlowBehaviorFilter)

        def draw(self, layout, context):
            row = layout.row()
            row.use_property_decorate = False
            row.use_property_split = False
            row.prop(self, 'current_tab', expand=True)
            
            col = layout.column()
            
            subcol = col.column()
            subcol.scale_y = 0.5
            subcol.separator()
            
            if self.current_tab == 'UI':
                self.draw_ui_settings(col)
            elif self.current_tab == 'VIEWPORT':
                self.draw_viewport_settings(col)
            elif self.current_tab == 'PRESETS':
                self.draw_presets(col, context, options={'SHOW_DEFAULTS'}, place='PREFS')
            elif self.current_tab == 'INPUT':
                self.draw_input_settings(col)

        def draw_ui_settings(self, layout):
            layout.prop(self, 'show_panel')
            layout.prop(self, 'use_specialized_cursors')
            layout.prop(self, 'presets_width_limit')
            layout.prop(self, 'behavior_entry_display')
            
            text = ', '.join(item.name
                for item in self.bl_rna.properties['topbar_extras_display'].enum_items
                if item.identifier in self.topbar_extras_display)
            text = text or '-'
            
            row = layout.row(align=True)
            split = row.split(factor=0.4)
            subrow = split.row()
            subrow.alignment = 'RIGHT'
            subrow.label(text='Topbar extras')
            split.prop_menu_enum(self, 'topbar_extras_display', text=text)
            row.label(icon='BLANK1')
            
            layout.separator()
            
            col = layout.column(align=True)
            col.prop(self, 'hover_text_enabled')
            col.prop(self, 'behavior_shorten_name')
            col.prop(self, 'hover_text_anchor')
            col.prop(self, 'hover_text_size')
            
            layout.separator()
            
            col = layout.column(align=True)
            col.prop(self, 'help_text_enabled')
            col.prop(self, 'help_text_show_all')
            col.prop(self, 'help_text_anchor')
            col.prop(self, 'help_text_size')
            col.prop(self, 'help_text_spacing')
            
            layout.separator()
            
            col = layout.column(align=True)
            col.prop(self, 'text_color')
            col.prop(self, 'text_background')

        def draw_viewport_settings(self, layout):
            col = layout.column(align=True)
            col.prop(self, 'snap_radius')
            col.prop(self, 'merge_radius')
            
            col = layout.column(align=True)
            col.prop(self, 'edge_loop_fraction')
            col.prop(self, 'vert_radius_base')
            col.prop(self, 'vert_outline_width')
            col.prop(self, 'edge_radius_base')
            col.prop(self, 'edge_radius_ext')
            
            col = layout.column(align=True)
            col.prop(self, 'occluded_alpha', slider=True)
            col.prop(self, 'color_vertex')
            col.prop(self, 'color_edge')
            col.prop(self, 'color_edge_loop')
            col.prop(self, 'color_boundary')
            col.prop(self, 'color_perimeter')
            col.prop(self, 'color_face')
            
            col = layout.column(align=True)
            col.prop(self, 'vertex_overlay_use_custom_colors')
            col.prop(self, 'vertex_overlay_unselected')
            col.prop(self, 'vertex_overlay_selected')
            col.prop(self, 'vertex_overlay_radius')
            col.prop(self, 'vertex_overlay_depth_bias')
            
            col = layout.column(align=True)
            col.prop(self, 'use_color_retopology')
            col.prop(self, 'color_retopology')

        def draw_presets(self, layout, context=None, options=(), place=None):
            if context is None:
                context = bpy.context
            
            if 'SHOW_DEFAULTS' in options:
                row = layout.row()
                row.use_property_decorate = False
                row.use_property_split = False
                subrow = row.row()
                subrow.alignment = 'LEFT'
                subrow.label(text='Defaults:')
                row.prop(self, 'default_presets_path', text='')
                
                layout.separator()
            
            behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
            behavior_presets_config.draw(layout, place=place)

        def draw_input_settings(self, layout):
            layout.prop(self, 'behavior_preset_use_number_shortcuts')

        def draw_tool_header(self, layout, context=None, multiline=False, show_config=True):
            if context is None:
                context = bpy.context
            
            space_data = context.space_data
            
            nflow_config_workspace = context.workspace.nsolve.ops.nflow
            nflow_config_scene = context.scene.nsolve.ops.nflow
            behavior_presets_config = nflow_config_workspace.behavior_presets_config
            
            behavior_presets_config = NFlowBehaviorPresetsConfig.get(context)
            behavior_preset = behavior_presets_config.get_active_preset()
            capabilities = NFlow.gather_capabilities(behavior_preset)
            
            topbar_extras_display = NFlowPrefs.get('topbar_extras_display')
            
            def draw_left_options(layout):
                main_row = layout.row()
                main_row.prop(nflow_config_workspace, 'enable', text='')
                row = ui_row(main_row, align=True, active=nflow_config_workspace.enable)
                row.popover('NSOLVE_PT_NFlow_Global_Options_Contextual', text='', icon='TOOL_SETTINGS')
            
            def draw_right_options(layout):
                main_row = layout.row()
                
                if 'SCROLL' in topbar_extras_display:
                    main_row.prop(self, 'behavior_preset_scroll_enable', text='', icon='MOUSE_MMB')
                
                if 'OVERLAY' in topbar_extras_display:
                    row = ui_row(main_row, align=True, active=nflow_config_workspace.enable)
                    row.prop(nflow_config_workspace, 'show_vertex_overlay', toggle=True, text='', icon='SNAP_VERTEX')
                    row.prop(nflow_config_scene, 'show_in_front', toggle=True, text='', icon='XRAY')
                    if hasattr(space_data.overlay, 'show_retopology'): # does not exist in Blender 3.3
                        row.prop(space_data.overlay, 'show_retopology', toggle=True, text='', icon='GHOST_ENABLED')
                
                if 'SNAPPING' in topbar_extras_display:
                    row = ui_row(main_row, align=True, active=nflow_config_workspace.enable)
                    # ui_prop(row, nflow_config_scene, 'projection_target', text='', placeholder='Target')
                    subrow = row.row(align=True)
                    subrow.alignment = 'RIGHT'
                    subrow.active = ('SHRINKWRAP' in capabilities)
                    subrow.prop(nflow_config_workspace, 'use_auto_shrinkwrap', text='', icon='MOD_SHRINKWRAP')
                    subrow.popover('NSOLVE_PT_NFlow_Snapping_Options', text='')
                
                if not multiline:
                    main_row.popover('NSOLVE_PT_NFlow_Global_Options', text='', icon='PREFERENCES')
            
            def draw_presets(layout):
                row = ui_row(layout, align=True, active=nflow_config_workspace.enable)
                
                if show_config:
                    row.popover('NSOLVE_PT_NFlow_Config_Popover', text='')
                
                behavior_presets = behavior_presets_config.behavior_presets
                
                behavior_entry_display = nflow_config_workspace.behavior_entry_display
                is_configurable = (behavior_entry_display not in ('TOUR', 'HELP'))
                
                if not behavior_presets:
                    row.operator('nsolve.nflow_reinit_config', text='Load defaults', icon='AUTO')
                    
                    subrow = row.row(align=True)
                    subrow.scale_x = (1.0 if is_configurable else 1.1)
                    text = ('New preset' if is_configurable else 'Add a preset')
                    behavior_presets_config.draw_add_preset(subrow, text=text, menu_only=(not is_configurable))
                    
                    if multiline:
                        layout.prop(nflow_config_workspace, 'behavior_entry_display_toggle', text='', icon='INFO')
                        
                        layout.popover('NSOLVE_PT_NFlow_Global_Options', text='', icon='PREFERENCES')
                else:
                    clamped_width = None
                    if not multiline:
                        dpi_scale = bpy.context.preferences.system.dpi / 72
                        ui_scale = bpy.context.preferences.view.ui_scale
                        icon_size = 20
                        default_font_size = 20
                        blf_size(0, default_font_size)
                        # This is just a quick empirical formula, I'm not completely sure
                        # right now what would be the fully correct formula
                        text_scale = 1 / (icon_size * dpi_scale)
                        area_scale = 1 / (icon_size * dpi_scale * ui_scale)
                        accum_width = sum(blf.dimensions(0, behavior_preset.name)[0] * text_scale + 1.5
                            for behavior_preset in behavior_presets)
                        area_w = context.area.width * area_scale
                        clamped_width = min(accum_width, area_w * (self.presets_width_limit/100))
                        clamped_width = (clamped_width if clamped_width < accum_width else None)
                    
                    subrow = row.row(align=True)
                    
                    if clamped_width is not None:
                        subrow.ui_units_x = clamped_width
                    
                    for index, behavior_preset in enumerate(behavior_presets):
                        subrow.prop(behavior_preset, 'is_active', text=behavior_preset.name, toggle=True)
                    
                    behavior_presets_config.draw_add_preset(row, text='', menu_only=(not is_configurable))
            
            if multiline:
                col = layout.column()
                
                if topbar_extras_display:
                    row = col.row()
                    row.alignment = 'RIGHT'
                    draw_right_options(row)
                
                row = col.row()
                draw_left_options(row)
                draw_presets(row)
                
                subcol = col.column()
                subcol.scale_y = 0.5
                subcol.separator()
            else:
                row = layout.row()
                draw_left_options(row)
                draw_presets(row)
                draw_right_options(row)

    class window_manager(bpy.types.PropertyGroup):
        behavior_search_candidates: bpy.props.CollectionProperty(type=NFlowBehaviorSearchCandidate)

    class workspace(bpy.types.PropertyGroup):
        is_initialized: bpy.props.BoolProperty()

        def on_enable_update(self, context):
            NFlow.cleanup()
            NFlow.hover_text = ''
            NFlow.show_highlight = False

        enable: bpy.props.BoolProperty(
            name='Use NFlow',
            description='Quickly switch between NFlow and Blender\'s default behavior',
            default=True,
            update=on_enable_update,
        )

        def get_is_active(self):
            behavior_presets_config = NFlowBehaviorPresetsConfig.get()
            
            if not (self.enable and behavior_presets_config.get_active_preset()):
                return False
            
            context = bpy.context
            tool = context.workspace.tools.from_space_view3d_mode(context.mode)
            if context.mode == 'OBJECT':
                return bool(tool) and (tool.idname == 'nsolve.nflow_object_mode')
            elif context.mode == 'EDIT_MESH':
                return bool(tool) and (tool.idname == 'nsolve.nflow_edit_mode')
            return False

        def set_is_active(self, value):
            context = bpy.context
            if context.mode == 'OBJECT':
                bpy.ops.wm.tool_set_by_id(name='nsolve.nflow_object_mode', space_type='VIEW_3D')
            elif context.mode == 'EDIT_MESH':
                bpy.ops.wm.tool_set_by_id(name='nsolve.nflow_edit_mode', space_type='VIEW_3D')
            else:
                return
            
            self.enable = value
            
            behavior_presets_config = NFlowBehaviorPresetsConfig.get()
            
            if not self.is_initialized:
                self.initialize()
            
            if not behavior_presets_config.is_initialized:
                NFlowBehaviorPresetsConfig.initialize()
            
            if len(behavior_presets_config.behavior_presets) == 0:
                bpy.ops.nsolve.nflow_add_behavior_preset()

        is_active: bpy.props.BoolProperty(
            name='Activate nFlow',
            description='Activate the nFlow tool',
            get=get_is_active,
            set=set_is_active,
        )

        behavior_presets_config: bpy.props.PointerProperty(type=NFlowBehaviorPresetsConfig)

        def on_behavior_entry_display_update(self, context):
            if self.behavior_entry_display in ('TOUR', 'HELP'):
                self.behavior_entry_display_tour_like = self.behavior_entry_display
            else:
                self.behavior_entry_display_full_like = self.behavior_entry_display
            self.is_initialized = True

        behavior_entry_display: bpy.props.EnumProperty(
            name='Behavior display',
            description='How behaviors will be shown in Blender UI',
            items=[
                ('TOUR', 'Tour', 'A mode for those who use only pre-defined configs'),
                ('SIMPLE', 'Simple', 'Show behavior name (command)'),
                ('SHORTCUT', 'Shortcut', 'Show behavior name (command) and its shortcut'),
                ('FULL', 'Full', 'Show full UI'),
                ('HELP', 'Help', 'Show the currently applicable configuration (non-editable)'),
            ],
            default='TOUR',
            update=on_behavior_entry_display_update,
        )
        behavior_entry_display_full_like: bpy.props.StringProperty(default='SIMPLE')
        behavior_entry_display_tour_like: bpy.props.StringProperty(default='TOUR')

        def get_behavior_entry_display_toggle(self):
            return self.behavior_entry_display in ('TOUR', 'HELP')

        def set_behavior_entry_display_toggle(self, value):
            if value:
                if self.behavior_entry_display_tour_like in ('TOUR', 'HELP'):
                    self.behavior_entry_display = self.behavior_entry_display_tour_like
                else:
                    self.behavior_entry_display = 'TOUR'
            else:
                if self.behavior_entry_display_full_like in ('FULL', 'SHORTCUT', 'SIMPLE'):
                    self.behavior_entry_display = self.behavior_entry_display_full_like
                else:
                    self.behavior_entry_display = 'SIMPLE'

        behavior_entry_display_toggle: bpy.props.BoolProperty(
            name='Toggle between tour (or help) and other modes',
            description='Toggle between Tour/Help and Simple/Shortcut/Full (depending on what was last chosen)',
            get=get_behavior_entry_display_toggle,
            set=set_behavior_entry_display_toggle,
        )

        show_vertex_overlay: bpy.props.BoolProperty(
            name='Draw vertex overlay',
            description='Display vertices regardless of the current selection mode',
            default=False,
        )

        use_hover_occlusion: bpy.props.BoolProperty(
            name='Use hover occlusion',
            description='Highlight only elements which are not occluded by the scene geometry',
            default=True,
        )

        use_auto_shrinkwrap: bpy.props.BoolProperty(
            name='Use Auto Shrinkwrap',
            description='Auto shrinkwrap when using nFlow behaviors',
            default=True,
        )
        auto_shrinkwrap_mode: bpy.props.EnumProperty(
            name='Auto Shrinkwrap mode',
            description='Auto Shrinkwrap mode',
            items=[
                ('NEAREST_SURFACE', 'Nearest (surface)', 'Snap to nearest surface'),
                ('PROJECT', 'Project (normals)', 'Project along the initial normals'),
                ('PROJECT_VIEW', 'Project (view)', 'Project along the view rays'),
            ],
            default='PROJECT',
        )

        snap_key: bpy.props.EnumProperty(
            name='Snap key',
            description='Use this key during some nFlow operations to snap vertices',
            items=event_key_items,
            default='LEFT_CTRL',
        )
        snap_to: bpy.props.EnumProperty(
            name='Snap To',
            description='Which positions to consider when snapping to scene geometry',
            items=[
                ('VERTS', 'Vertices', 'Snap to vertices', 'SNAP_VERTEX', 1 << 0),
                ('EDGES', 'Edges', 'Snap to edges', 'SNAP_EDGE', 1 << 1),
                ('FACES', 'Faces', 'Snap to faces', 'SNAP_FACE', 1 << 2),
                ('EDGES_MID', 'Edge centers', 'Snap to edge centers', 'SNAP_MIDPOINT', 1 << 3),
                ('FACES_MID', 'Face centers', 'Snap to face centers', 'SNAP_FACE_CENTER', 1 << 4),
            ],
            default={'VERTS'},
            options={'ENUM_FLAG'},
        )

        use_mirror_clipping: bpy.props.BoolProperty(
            name='Use Mirror Clipping',
            description='\n'.join([
                'Prevent vertices from going through mirror plane(s)',
                '(for Mirror modifier(s) that have Clipping enabled)',
            ]),
            default=True,
        )

        poly_type: bpy.props.EnumProperty(name='Polygon type(s)', description='Which polygons to prefer',
            items=[
                ('QUADS', 'Quads', 'Always prefer quads'),
                ('TRIS', 'Tris', 'Always prefer triangles'),
                ('BOTH', 'Both', 'Quads or triangles, depending on heuristics'),
            ],
            default='QUADS',
        )

        ignore_occluded_verts: bpy.props.BoolProperty(
            name='Ignore occluded verts',
            description='Ignore the occluded vertices when considering polygon candidates',
            default=False,
        )

        poly_search: bpy.props.EnumProperty(name='Polygon search', description='Polygon suggestion method',
            items=[
                ('WORLD', 'World-space', 'Detect based on world-space proximity'),
                ('SCREEN', 'Screen-space', 'Detect based on screen-space proximity'),
                ('STABLE', 'Stable', 'Detect based on screen-space tesselation'),
            ],
            default='SCREEN',
        )

        suggest_poly_roll: bpy.props.BoolProperty(
            name='Use rolling',
            description='Enable rolling (via mousewheel) through polygon candidates or algorithms',
            default=True,
        )
        suggest_poly_roll_mode: bpy.props.EnumProperty(
            name='What to roll',
            description='Decide what rolling will do',
            items=[
                ('SUGGESTIONS', 'Polygons', 'Roll through polygon candidates'),
                ('ALGORITHM', 'Algorithm', 'Change the polygon suggestion algorithm'),
            ],
            default='ALGORITHM',
        )

        relax_speed: bpy.props.FloatProperty(
            name='Relax factor',
            description='Speed of vertex smoothing',
            default=0.2,
            min=0,
            max=1,
            step=1,
        )

        draw_verts_min_distance_pixels: bpy.props.IntProperty(
            name='Min distance (pixels)',
            description='Minimal distance between the adjacent vertices in a vertex strip',
            default=32,
            min=1,
            subtype='PIXEL',
        )

        draw_verts_resampling: bpy.props.FloatProperty(
            name='Resampling',
            description='Proportionality between segment count and the number of selected elements',
            default=1,
            min=0,
            step=100,
        )

        def initialize(self):
            if self.is_initialized:
                return
            
            self.behavior_entry_display = NFlowPrefs.get('behavior_entry_display')
            self.is_initialized = True

    class scene(bpy.types.PropertyGroup):
        def get_show_in_front(self):
            return any(obj.show_in_front for obj in EditableMeshes.objs())

        def set_show_in_front(self, value):
            for obj in EditableMeshes.objs():
                obj.show_in_front = value

        show_in_front: bpy.props.BoolProperty(
            name='In Front',
            description='Display mesh(es) over everything else in the scene',
            get=get_show_in_front,
            set=set_show_in_front,
        )

        def projection_target_poll(self, obj):
            return (obj.type in Raycaster.obj_types) and (obj.mode == 'OBJECT')

        projection_target: bpy.props.PointerProperty(
            name='Projection target',
            description='Projection target (\'live\' object to which vertices will snap)',
            type=bpy.types.Object,
            poll=projection_target_poll,
        )

        store_data: bpy.props.BoolProperty(
            name='Store data',
            description='Store data for the current session',
            default=True,
        )


types_classes = (
    NFlow_Import_Config_Preset_Options,
    NFlowBehaviorPresetEntryOperatorArgument,
    NFlowBehaviorPresetEntryOption,
    NFlowBehaviorPresetEntry,
    NFlowBehaviorPreset,
    NFlowBehaviorFilter,
    NFlowBehaviorPresetsConfig,
    NFlowBehaviorSearchCandidate,
    types.preferences,
    types.window_manager,
    types.workspace,
    types.scene,
)


classes = (
    NSOLVE_OT_NFlow,
    NSOLVE_OT_NFlow_Shrinkwrap,
    NSOLVE_PT_NFlow_Snapping_Options,
    NSOLVE_MT_NFlow_Select_Behavior_Preset,
    NSOLVE_OT_NFlow_Select_Behavior_Preset,
    NSOLVE_OT_NFlow_Activate_Behavior_Preset,
    NSOLVE_OT_NFlow_Add_Behavior_Preset,
    NSOLVE_OT_NFlow_Remove_Behavior_Preset,
    NSOLVE_OT_NFlow_Add_Behavior_Preset_Entry,
    NSOLVE_OT_NFlow_Remove_Behavior_Preset_Entry,
    NSOLVE_OT_NFlow_Duplicate_Behavior_Preset_Entry,
    NSOLVE_OT_NFlow_Move_Behavior_Preset_Entry,
    NSOLVE_OT_NFlow_Select_Behavior_Preset_Entry,
    NSOLVE_OT_NFlow_Search_Behavior_Preset_Entry,
    NSOLVE_OT_NFlow_Add_Behavior_Filter,
    NSOLVE_OT_NFlow_Remove_Behavior_Filter,
    NSOLVE_OT_NFlow_Reset_Behavior_Filters,
    NSOLVE_PT_NFlow_Filter_Behavior_Preset_Entries,
    NSOLVE_MT_NFlow_Choose_Behavior_Preset_Entry,
    NSOLVE_OT_NFlow_Clear_Behavior_Preset_Entry_Command,
    NSOLVE_MT_NFlow_Choose_Behavior_Preset_Entry_Option_Enum,
    NSOLVE_OT_NFlow_Set_Behavior_Preset_Entry_Option_Enum,
    NSOLVE_OT_NFlow_Edit_Behavior_Preset_Entry_Operator_Args,
    NSOLVE_PT_NFlow_Preset_Entry_Options,
    NSOLVE_PT_NFlow_Config_Options,
    NSOLVE_PT_NFlow_Config_Popover,
    NSOLVE_PT_NFlow_Preset_Colors,
    NSOLVE_PT_NFlow_Global_Options,
    NSOLVE_PT_NFlow_Global_Options_Contextual,
    NSOLVE_PT_NFlow_View3D_Sidebar,
    NSOLVE_OT_NFlow_Copy_Config,
    NSOLVE_OT_NFlow_Paste_Config,
    NSOLVE_OT_NFlow_Export_Config,
    NSOLVE_OT_NFlow_Import_Config,
    NSOLVE_MT_NFlow_Import_Default_Config,
    NSOLVE_OT_NFlow_Reinit_Config,
)


draw_handlers = []


def add_draw_handler(callback, args, region_type, event):
    handler = bpy.types.SpaceView3D.draw_handler_add(callback, args, region_type, event)
    draw_handlers.append((handler, region_type))


def register_draw_handlers():
    add_draw_handler(NFlow.draw_2d, (), 'WINDOW', 'POST_PIXEL')
    add_draw_handler(NFlow.draw_3d, (), 'WINDOW', 'POST_VIEW')


def unregister_draw_handlers():
    for handler, region_type in draw_handlers:
        bpy.types.SpaceView3D.draw_handler_remove(handler, region_type)

    draw_handlers.clear()


event_handlers = []


def add_event_handler(event_name, callback, persistent=True):
    if persistent:
        @bpy.app.handlers.persistent
        def persistent_callback(scene):
            callback(scene)
        actual_callback = persistent_callback
    else:
        actual_callback = callback

    getattr(bpy.app.handlers, event_name).append(actual_callback)
    event_handlers.append((event_name, actual_callback))


def register_event_handlers():
    add_event_handler('load_post', NFlow.on_load)
    
    add_event_handler('load_post', BehaviorPresetEntryItems.on_load)
    
    # Immediately modifying a file upon load is probably not a good idea
    # add_event_handler('load_post', NFlowBehaviorPresetsConfig.on_load)


def setup_default_behavior_filters():
    nflow_prefs = NFlowPrefs.prefs()
    
    if nflow_prefs.behavior_filters_initialized:
        return
    
    path = (Path(__file__).parent.parent.parent.parent / 'config' / 'default_filters.json').as_posix()
    
    try:
        with open(path, 'r', encoding='utf-8') as file:
            data = json.loads(file.read())
        
        nflow_prefs.behavior_filter_all = data['behavior_filter_all']
        
        nflow_prefs.behavior_filters.clear()
        for filter_data in data['behavior_filters']:
            behavior_filter = nflow_prefs.behavior_filters.add()
            behavior_filter.show = filter_data['show']
            behavior_filter.name = filter_data['name']
            behavior_filter.filter = filter_data['filter']
    except Exception as exc:
        print('Could not load default behavior filters:', repr(exc))
        return
    
    nflow_prefs.behavior_filters_initialized = True


def unregister_event_handlers():
    for event_name, callback in event_handlers:
        getattr(bpy.app.handlers, event_name).remove(callback)
    event_handlers.clear()


def register():
    register_event_handlers()
    register_draw_handlers()
    setup_default_behavior_filters()


def unregister():
    unregister_draw_handlers()
    unregister_event_handlers()
