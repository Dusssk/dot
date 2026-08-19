from os import listdir
from os.path import abspath, join

from re import split

import bpy

from bpy.types import Operator

from . import shader
from . utils import safe_call
from .... utility import addon
from .... utils.toggle_view3d_panels import collapse_3D_view_panels


class HOPS_OT_release_log(Operator):
    bl_idname = 'hops.release_log'
    bl_label = 'Release Log'
    bl_description = 'Display a release log in the viewport'
    bl_options = {'INTERNAL'}
    bl_cursor_pending = 'DEFAULT'

    index = 0


    @staticmethod
    def dpi_factored(value):
        # return value
        ui_scale = bpy.context.preferences.view.ui_scale
        pixel_scale = bpy.context.preferences.system.pixel_size
        dpi_factor = ui_scale * pixel_scale

        return value * dpi_factor


    def safe_dimensions(self):
        preference = addon.preference()
        x, y, w, h = self.shader_handler.safe_dimensions(ignore='UI' if preference.ui.Hops_auto_hide_n_panel else '')

        dpi = self.dpi_factored

        margin = 32
        x += dpi(margin)
        y += dpi(margin)
        w -= dpi(margin*2)
        h -= dpi(margin*2)

        s = min(w/self.image.width, h/self.image.height)

        x = x + w - self.image.width * s
        y = y + h - self.image.height * s

        w = self.image.width * s
        h = self.image.height * s

        border = 10

        return x, y, w, h, margin, border


    def init_theme(self, context):
        preference = addon.preference()
        dpi = self.dpi_factored

        # font = ''
        # font_size = 12
        # foreground = (1, 1, 1, 1)
        # background = (1, 0, 1, 1)
        # border = (1, 1, 0, 1)
        # border_size = 2
        # corner_radius = 4
        # corner_chamfer = False
        # smoothing = True
        # anim_speed = 0.05
        # anim_blend = 'SMOOTHSTEP'

        self.theme_font = abspath(join(__file__, '..', 'font', 'Genos-Bold.ttf')),

        shadow_offset = preference.ui.Hops_modal_drop_shadow_offset
        self.theme_shadow_size = abs(shadow_offset[0]) + abs(shadow_offset[0])

        self.theme_fade_time = preference.ui.Hops_release_log_fade_time
        self.theme_anim_time = preference.ui.Hops_release_log_anim_time

        self.theme_frame_background = preference.color.Hops_UI_cell_background_color


    def init_shader_handler(self, context):
        self.shader_handler = shader.View3DPixel2D(context.screen, idname=self.bl_idname)


    def init_paths(self):
        self.directory = abspath(join(__file__, '..', '..', '..', '..', 'release_logs'))

        supported_formats = {'jpeg', 'jpg', 'png', 'webp'}
        files = [f for f in listdir(self.directory) if f.lower().split('.')[-1] in supported_formats]
        sorted_files = sorted(files, reverse=True, key=lambda x: [int(t) if t.isdigit() else t.lower() for t in split(r'(\d+)', x)])

        self.paths = [join(self.directory, file) for file in sorted_files]


    def init_frames(self):
        self.update_image()

        x, y, w, h, margin, border = self.safe_dimensions()
        dpi = self.dpi_factored

        # shadow
        self.shadow_size = dpi(self.theme_shadow_size)
        self.shadow_smooth = dpi(0)
        self.shadow_border = dpi(2)

        self.shadow1 = self.shader_handler.add_element(
            shader.Frame(self.shader_handler,
                location = (x+self.shadow_border, y-self.shadow_size),
                size = (0, h),
                background = (0, 0, 0, min(self.theme_frame_background[-1]*2, 0.9)),
                border_size = 0,
                corner_radius = 0,
                smoothing = self.shadow_smooth,
                clipping = (0, 0, self.shadow_smooth, 0),
                anim_speed = {
                    'fade': self.theme_fade_time,
                    'transform' : self.theme_anim_time*2},
                anim_blend = 'BOUNCE'))

        self.shadow1.location = (x-self.shadow_size+self.shadow_border, y-self.shadow_size)
        self.shadow1.size = (self.shadow_size, h)

        self.shadow2 = self.shader_handler.add_element(
            shader.Frame(self.shader_handler,
                location = (x+self.shadow_border, y-self.shadow_size),
                size = (0, self.shadow_size+self.shadow_border),
                background = (0, 0, 0, min(self.theme_frame_background[-1]*2, 0.9)),
                border_size = 0,
                corner_radius = 0,
                smoothing = self.shadow_smooth,
                clipping = (self.shadow_smooth, self.shadow_smooth, 0, 0),
                anim_speed = {
                    'fade': self.theme_fade_time,
                    'transform' : self.theme_anim_time},
                anim_blend = 'SMOOTHSTEP'))

        self.shadow2.location = (x+self.shadow_border, y-self.shadow_size)
        self.shadow2.size = (w-self.shadow_size+self.shadow_smooth-self.shadow_border, self.shadow_size+self.shadow_border)

        # frame
        self.frame = self.shader_handler.add_element(
            shader.Frame(self.shader_handler,
                location = (x, y),
                size = (0, h),
                background = self.theme_frame_background,
                border = (0, 0, 0, min(self.theme_frame_background[-1]*2, 0.9)),
                border_size = self.shadow_border,
                corner_radius = 0,
                smoothing = self.shadow_border,
                anim_speed = {
                    'fade': self.theme_fade_time,
                    'transform' : self.theme_anim_time},
                anim_blend = 'SMOOTHSTEP'))

        self.frame.location = (x, y)
        self.frame.size = (w, h)

        # content
        self.content = self.shader_handler.add_element(
            shader.Frame(self.shader_handler,
                image = self.path,
                location = (x + dpi(border), y + dpi(border) + h/2),
                size = (w - dpi(border*2), 0),
                background = (0, 0, 0, 0),
                border_size = 0,
                corner_radius = 0,
                smoothing = dpi(0),
                anim_speed = {
                    'fade': self.theme_fade_time,
                    'transform' : self.theme_anim_time*2},
                anim_blend = 'BOUNCE'))

        self.content.location = (x + dpi(border), y + dpi(border))
        self.content.size = (w - dpi(border*2), h - dpi(border*2))


    def update_image(self):
        self.path = self.paths[self.index]
        self.image = shader.load_texture(self.path)

        if self.path not in shader.textures:
            shader.textures[self.path] = self.image

        if not hasattr(self, 'content'):
            return

        x, y, w, h, margin, border = self.safe_dimensions()
        dpi = self.dpi_factored

        self.content.image = self.path

        self.shadow1.location = (x-self.shadow_size+self.shadow_border, y-self.shadow_size)
        self.shadow1.size = (self.shadow_size, h)

        self.shadow2.location = (x+self.shadow_border, y-self.shadow_size)
        self.shadow2.size = (w-self.shadow_size+self.shadow_smooth-self.shadow_border, self.shadow_size+self.shadow_border)

        self.frame.location = (x, y)
        self.frame.size = (w, h)

        self.content.location = (x + dpi(border), y + dpi(border))
        self.content.size = (w - dpi(border*2), h - dpi(border*2))


    @safe_call
    def invoke(self, context, event):
        if shader.handler(self.bl_idname):
            shader.handler(self.bl_idname).remove()
            return {'CANCELLED'}

        self.init_theme(context)
        self.init_shader_handler(context)

        if not hasattr(self, 'shader_handler'):
            return {'CANCELLED'}

        preference = addon.preference()

        self.original_t_panel, self.original_n_panel = collapse_3D_view_panels()

        self.init_paths()
        self.init_frames()

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


    @safe_call
    def modal(self, context, event):
        self.shader_handler.update(event)

        if not self.shader_handler.elements:
            return {'FINISHED'}

        if event.type in {'ESC', 'LEFTMOUSE'}:
            self.shader_handler.remove()
            collapse_3D_view_panels(self.original_t_panel, self.original_n_panel)

        if event.type == 'WHEELUPMOUSE':
            self.index += 1
            if self.index + 1 > len(self.paths):
                self.index = 0

            self.update_image()

            return {'RUNNING_MODAL'}

        elif event.type == 'WHEELDOWNMOUSE':
            self.index -= 1
            if self.index < 0:
                self.index = len(self.paths) - 1

            self.update_image()

            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}


    def remove(self, force=False): # include force kwarg for safe_call compatibility
        if not hasattr(self, 'shader_handler'):
            return

        self.shader_handler.remove(force=True) # always force if this remove is called

