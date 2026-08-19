import os
import bpy
import blf

from time import time
from mathutils import Vector

from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty, IntVectorProperty, StringProperty, FloatProperty
from . import font
from . types import DrawCleanup
from . shader import View3DPixel2D, Frame
# from .... fonts import get_font_path
from . utils import safe_call
from .... utils import addon

hold = False
busy = False


def calculate_corner_positions(context, interface_options):
    from ... handlers import handlers as animation
    left_fix, right_fix, usable_width, area_height, top_offset, bottom_offset = animation.get_viewport_dimensions(context)

    # Calculate UI scale factors
    ui_scale = context.preferences.view.ui_scale
    pixel_scale = context.preferences.system.pixel_size
    dpi_factor = ui_scale * pixel_scale

    # Calculate dimensions
    line_length = interface_options.animation_line_length * dpi_factor
    line_width = interface_options.animation_line_width * dpi_factor
    base_margin = interface_options.margin * dpi_factor
    margin = base_margin

    # Calculate positions
    left_x = left_fix + margin
    right_x = left_fix + usable_width - margin
    top_y = area_height - margin - top_offset
    bottom_y = margin + bottom_offset

    return left_x, right_x, top_y, bottom_y, line_length, line_width


class NSOLVE_OT_banner(Operator, DrawCleanup):
    bl_idname = 'nsolve.banner'
    bl_label = 'Generic Banner Operator'
    bl_description = 'Display a common banner style in the viewport'
    bl_options = {'INTERNAL'}
    bl_cursor_pending = 'DEFAULT'

    hold: BoolProperty(default=False) # keep banner onscreen (preferences)
    busy: BoolProperty(default=False)
    operator: StringProperty(default='')


    def init_theme(self, context):
        from ... handlers import handlers as animation

        nsolve_prefs = addon.pref().tools.nsolve
        color_options = nsolve_prefs.BannerColor
        interface_options = nsolve_prefs.InterfaceOptions
        interface_color = nsolve_prefs.InterfaceColor

        ui_scale = context.preferences.view.ui_scale
        pixel_scale = context.preferences.system.pixel_size
        dpi_factor = ui_scale * pixel_scale

        self.bc = (0, 0, 0.0, 0.8) # border color
        self.bs = int(0 * dpi_factor) # border size
        self.br = int(0 * dpi_factor)# border radius

        self.fg1 = color_options.bg_text_color # fg low
        self.fg2 = color_options.fg_text_color # fg high

        text_size = interface_options.banner_text_size
        self.fs = int(text_size * dpi_factor) # font size
        # font_size = int(text_size * dpi_factor)
        # self.fid = blf.load(get_font_path(interface_options.font_type))
        self.fid = font.load('Genos-Bold.ttf')
        # self.fid = 0

        self.text_bg = color_options.bg_color

        self.text_frame_anim_speed = interface_options.banner_frame_time
        self.text_frame_anim_type = 'SMOOTHSTEP'

        active_tool, nsolve_prefs, current_operator = animation.get_active_tool_info()
        tool_color = animation.get_tool_color(active_tool, interface_color, self.operator)
        self.bar_bg = color_options.tick_color if not color_options.tick_color_use_tool else tool_color
        self.bar_frame_anim_speed = interface_options.banner_tick_time
        self.bar_frame_anim_type = 'SMOOTHSTEP'

        self.bar_highlight_bg = color_options.highlight_color
        self.bar_highlight_fade_speed = interface_options.banner_highlight_time

        self.text_anim_speed = interface_options.banner_bg_text_time
        self.text_anim_type = 'SMOOTHSTEP'

        self.upper_text_anim_speed = interface_options.banner_fg_text_time
        self.upper_text_anim_type = 'BOUNCE'

        self.lower_text_anim_speed = interface_options.banner_fg_text_time
        self.lower_text_anim_type = 'BOUNCE'


    def init_max(self):
        size=Vector()
        for region in self.pixels.area.regions:
            if region.type != 'UI' or region.width == 1:
                continue

            size.x -= region.width

        _width = 58
        tool_width = _width
        for region in self.pixels.area.regions:
            if region.type == 'TOOLS' and region.width > 1:
                tool_width = region.width
                break

        self.loc_max = Vector((tool_width*1.5, tool_width/2 + self.bs))
        self.size_max = Vector((self.pixels.size.x - 125 - tool_width + size.x, self.pixels.size.y - 100 - tool_width))


    def init_location(self, w, h): #TODO: consider init_max?
        area = (self.pixels.size.x, self.pixels.size.y)
        if self.anchor == 'TOPLEFT':
            return (
                self.offset[0],
                area[1] - self.offset[1] - h - self.fp * 2)
        elif self.anchor == 'TOPMIDDLE':
            return (
                self.offset[0] + area[1]/2 - w/2,
                area[1] - self.offset[1] - h - self.fp * 2)
        elif self.anchor == 'TOPRIGHT':
            return (
                area[0] - w - self.offset[0] - self.fmr - self.fp - self.fs/10,
                area[1] - h - self.offset[1] - self.fp * 2)
        elif self.anchor == 'MIDDLE':
            return (
                area[0]/2 - w/2 + self.offset[0],
                area[1]/2 - h/2 - self.offset[1])
        elif self.anchor == 'MIDDLELEFT':
            return (
                self.offset[0],
                area[1]/2 - self.offset[1] - h/2)
        elif self.anchor == 'MIDDLERIGHT':
            return (
                area[0] - w - self.offset[0] - self.fmr - self.fp - self.fs/10,
                area[1]/2 - h/2 - self.offset[1] - self.fp * 2)
        elif self.anchor == 'BOTTOMLEFT':
            return (
                self.offset[0],
                self.offset[1])
        elif self.anchor == 'BOTTOMMIDDLE':
            return (
                self.offset[0] + area[0]/2 - w/2,
                self.offset[1])
        else: # elif self.anchor == 'BOTTOMRIGHT':
            return (
                area[0] - w - self.offset[0] - self.fmr - self.fp - self.fs/10,
                self.offset[1])


    def init_pixels(self, context):
        self.pixels = View3DPixel2D(context.screen, idname=self.bl_idname)

        self.finish_time = 0
        self.init_transit = False
        self.exit_transit = False

        self.init_max()


    def add_frame(self, *args, **kwargs):
        return self.pixels.add_element(Frame(self.pixels.size, *args, **kwargs))


    def init_draw_pixels(self, context, event):
        self.fp = self.fs/20 # font padding
        self.fmr = self.fp/4 * self.fat

        blf.size(self.fid, self.fs)
        w, h = blf.dimensions(self.fid, self.bg_text)
        size = (w, h)
        loc = self.init_location(w, h)

        # icon frame
        self.icon_frame = self.add_frame(
            loc = (loc[0] - size[1] - self.fmr * 6 - self.bs * 2, loc[1] + h/2),
            size = (size[1] + self.fp * 2 + self.bs * 2, self.bs * 2),
            icon = self.icon,
            icon_size = size[1] + self.fp * 2 + self.bs * 2,
            bg = self.text_bg,
            border_size = self.bs,
            corner_radius = self.br,
            anim = self.text_frame_anim_type,
            speed = {'anim': self.text_frame_anim_speed})

        self.icon_frame.location = Vector((self.icon_frame.location.x, loc[1]))
        self.icon_frame.size = Vector((self.icon_frame.size[0], size[1] + self.fp * 2 + self.bs * 2))

        # text frame
        self.text_frame = self.add_frame(
            loc = (loc[0], loc[1] + h/2),
            size = (size[0] + self.fmr + self.bs * 2, self.bs * 2),
            bg = self.text_bg,
            border = self.bc,
            border_size = self.bs,
            corner_radius = self.br,
            anim = self.text_frame_anim_type,
            speed = {'anim': self.text_frame_anim_speed})

        self.text_frame.location = Vector((self.text_frame.location.x, loc[1]))
        self.text_frame.size = Vector((self.text_frame.size[0], size[1] + self.fp * 2 + self.bs * 2))

        self.bar_frame = None
        self.bar_highlight = None
        self.text = None
        self.upper_text = None
        self.lower_text = None

        context.window_manager.modal_handler_add(self)


    def draw_pixels(self, context, event):
        global busy
        self.pixels.update(event)

        if self.pixels.exit or self.init_mode != bpy.context.active_object.mode or self.pixels.area.type == 'EMPTY': # event.type == 'ESC':
            busy = False
            return self.exit(context, force=self.pixels.area.type == 'EMPTY') # , force=event.type == 'ESC')

        # bg text addin (when frame anim finished)
        if not self.text and not self.text_frame.exit and self.text_frame.anim_finished:
            blf.size(self.fid, self.fs)
            wt, ht = blf.dimensions(self.fid, self.bg_text)
            loc = (self.text_frame.location.x + self.bs, self.text_frame.location.y + self.fp + self.bs)
            self.text = self.add_frame(
                loc = (loc[0], loc[1]),
                size = (0, ht),
                text = self.bg_text,
                fg = self.fg1,
                font = self.fid,
                font_size = self.fs,
                anim = self.text_anim_type,
                speed = {'anim': self.text_anim_speed})

            self.text.size.x = wt

        # bar frame addin (when text anim finished)
        elif not self.bar_frame and self.text and not self.text.exit and self.text.anim_finished:
            bar_loc = self.text_frame.location.copy()
            bar_loc.x += self.text_frame.size[0] + self.fp
            bar_loc.y += self.text_frame.size[1]/2
            self.bar_frame = self.add_frame(
                loc = bar_loc,
                size = (self.fs/10, 0),
                bg = self.bar_bg,
                border = self.bc,
                border_size = self.bs,
                corner_radius = self.br,
                anim = self.bar_frame_anim_type,
                speed = {'anim': self.bar_frame_anim_speed})

            self.bar_frame.location = Vector((self.bar_frame.location.x, self.text_frame.location.y))
            self.bar_frame.size = Vector((self.bar_frame.size.x, self.text_frame.size[1]))

        # pulse bar and upper text addin (when bar frame anim finished)
        elif not self.upper_text and self.bar_frame and not self.bar_frame.exit and self.bar_frame.anim_finished:
            self.bar_highlight = self.add_frame(
                loc = self.bar_frame.location.copy(),
                size = self.bar_frame.size.copy(),
                bg = self.bar_highlight_bg,
                border = self.bc,
                border_size = self.bs,
                corner_radius = self.br,
                speed = {'fade': self.bar_highlight_fade_speed})

            blf.size(self.fid, self.fs if self.single_line else self.fs/2 - self.fp)
            wt, ht = blf.dimensions(self.fid, self.top_text)
            w = self.text_frame.size[0]
            h = self.text_frame.size[1]
            loc = (self.text_frame.location.x + w, self.text_frame.location.y + h - ht)
            self.upper_text = self.add_frame(
                loc = (loc[0] - self.bs, loc[1] - self.fp - self.bs),
                clip_location = self.text_frame.location.copy(),
                clip_size = self.text_frame.size.copy(),
                text = self.top_text,
                fg = self.fg2,
                font = self.fid,
                font_size = self.fs if self.single_line else self.fs/2 - self.fp,
                anim = self.upper_text_anim_type,
                bounce = 2,
                speed = {'anim': self.upper_text_anim_speed})

            self.upper_text.location.x = loc[0] - w/2 - self.bs - (wt - w/2 + self.fs/8 if wt > w/2 else 0)

        # lower text addin (when upper text anim finished)
        elif not self.single_line and not self.lower_text and self.upper_text and not self.upper_text.exit and self.upper_text.anim_finished:
            blf.size(self.fid, self.fs/2 - self.fp)
            wt, ht = blf.dimensions(self.fid, self.bottom_text)
            w = self.text_frame.size[0]
            h = self.text_frame.size[1]
            loc = (self.text_frame.location.x - wt - (self.fp/self.fat if self.fat else 0), self.text_frame.location.y)

            self.lower_text = self.add_frame(
                loc = (loc[0] - self.bs, loc[1] + self.fp + self.bs),
                clip_location = self.text_frame.location.copy(),
                clip_size = (self.text_frame.size.x + wt, self.text_frame.size.y),
                text = self.bottom_text,
                fg = self.fg2,
                font = self.fid,
                font_size = self.fs/2 - self.fp,
                anim = self.lower_text_anim_type,
                bounce = 2,
                speed = {'anim': self.lower_text_anim_speed})

            self.lower_text.location.x = loc[0] + w - self.fp - self.bs + self.fs/100

        # when all anim finished: (wait 1 second)
        elif not self.anim_finished and self.upper_text and (self.single_line or (self.lower_text and not self.lower_text.exit and self.lower_text.anim_finished)):

            if not self.finish_time:
                self.finish_time = time()

            # first bg text remove
            if not hold and not self.anim_finished and time() - self.finish_time > 1:
                self.pixels.pause_redraw = False
                self.anim_finished = True
                self.text.exit = True

        # then upper, lower and text frame remove (at the same time)
        elif self.text and self.text.exit and not self.text_frame.exit and self.text.anim_finished:
            self.bar_highlight = self.add_frame(
                loc = self.bar_frame.location.copy(),
                size = self.bar_frame.size.copy(),
                bg = self.bar_highlight_bg,
                border = self.bc,
                border_size = self.bs,
                corner_radius = self.br,
                speed = {'fade': self.bar_highlight_fade_speed})

            self.text_frame.exit = True
            self.upper_text.exit = True
            if not self.single_line:
                self.lower_text.exit = True

        # finally bar remove
        elif (self.single_line and self.upper_text and self.upper_text.exit and self.upper_text.anim_finished or self.lower_text and self.lower_text.exit and self.lower_text.anim_finished) and not self.bar_frame.exit:
            self.bar_highlight = self.add_frame(
                loc = self.bar_frame.location.copy(),
                size = self.bar_frame.size.copy(),
                bg = self.bar_highlight_bg,
                border = self.bc,
                border_size = self.bs,
                corner_radius = self.br,
                speed = {'fade': self.bar_highlight_fade_speed})

            self.bar_frame.exit = True
            self.pixels.exit = True #XXX: shouldnt have to do this here

        if self.bar_highlight and not self.bar_highlight.exit and self.bar_highlight.anim_finished:
            self.bar_highlight.exit = True
            self.bar_highlight = None

        return {'PASS_THROUGH'}


    @safe_call
    def invoke(self, context, event):
        from ... handlers import handlers as animation
        from . import shader

        global hold, busy
        hold = self.hold

        if busy and not self.busy:
            return {'CANCELLED'}

        active_tool, nsolve_prefs, current_operator = animation.get_active_tool_info()
        if not nsolve_prefs.InterfaceOptions.enable_banner:
            return {'CANCELLED'}

        if not active_tool:
            return {'CANCELLED'}

        if not current_operator:
            return {'CANCELLED'}

        self.init_mode = bpy.context.active_object.mode

        # for pixels in shader.running:
        #     if pixels.idname != self.bl_idname:
        #         continue
        #     if any([e.text and e.text == self.operator for e in pixels.elements]):
        #         return {'CANCELLED'}

        for pixels in shader.running:
            if pixels.idname != self.bl_idname:
                continue
            for element in pixels.elements:
                element.exit = True

        region = context.region

        interface_options = nsolve_prefs.InterfaceOptions
        props = nsolve_prefs.main

        dpi_factor = context.preferences.view.ui_scale * context.preferences.system.pixel_size

        _, right_x, top_y, _, _, line_width = calculate_corner_positions(context, interface_options)

        # if not interface_options.extra_animation and (animation.state.last_tool != active_tool.idname or (animation.state.last_operator != current_operator and active_tool.idname == 'nsolve.nsolvetool')):
        #     return {'CANCELLED'}

        upper_text = self.operator
        lower_text = 'VERT'
        bg_text = 'NSOLVE'

        if upper_text == 'SELECT':
            upper_text = 'BOX'
            lower_text = 'SELECT'
            bg_text = 'SWAP'

        elif upper_text == 'LINE':
            lower_text = 'KNIFE'

        elif upper_text == 'KNIFE':
            upper_text = 'KNIFE'
            #lower_text = 'TOOL'

        elif upper_text == 'DISSOLVE':
            lower_text = 'EDGE' if not props.dissolve_use_verts else 'VERTS'

        elif upper_text == 'OFFSET':
            lower_text = 'EDGE'
            bg_text = 'SWAP'

        elif upper_text == 'HIDE':
            bg_text = 'NSOLVE'
            ...
            # upper_text = 'SHOW'
            # lower_text = '/HIDE'
        elif upper_text == 'HARD LOOP CUT':
            upper_text = 'HARD'
            lower_text = 'LOOP CUT'
            bg_text = 'NSUITE'

        elif upper_text == 'MESH LOOP CUT':
            upper_text = 'MESH'
            lower_text = 'LOOP CUT'
            bg_text = 'NSUITE'

        elif upper_text == 'HARD EDGE SLIDE':
            upper_text = 'HARD'
            lower_text = 'EDGE SLIDE'
            bg_text = 'NSUITE'

        elif upper_text == 'HARD BEVEL':
            upper_text = 'HARD'
            lower_text = 'BEVEL'
            bg_text = 'NSUITE'

        elif upper_text == 'MESH CUT':
            upper_text = 'MESH'
            lower_text = 'CUT'
            bg_text = 'NSUITE'

        elif upper_text == 'MESH MULTI CUT':
            upper_text = 'MESH'
            lower_text = 'MULTI CUT'
            bg_text = 'NSUITE'

        elif upper_text == 'PROJECT LOOP':
            upper_text = 'PROJECT'
            lower_text = 'LOOP'
            bg_text = 'NSUITE'

        elif upper_text == 'PROJECT CIRCLE':
            upper_text = 'PROJECT'
            lower_text = 'CIRCLE'
            bg_text = 'NSUITE'

        elif upper_text == 'PROJECT GRID':
            upper_text = 'PROJECT'
            lower_text = 'GRID'
            bg_text = 'NSUITE'

        # single_line: BoolProperty(default=False)
        # self.single_line = False
        icons_dir = os.path.abspath(os.path.join(__file__, '..', '..', '..', '..', 'icons', 'buttons'))
        icon =  F'{self.operator.lower()}.png'
        if self.operator in {'CIRCLE', 'GRID', 'LINE', 'LOOP', 'STAMP'}:
            icon = 'project '+icon
        if self.operator in {'COLLAPSE'}:
            icon = 'collapse verts.png'
        if self.operator in {'OFFSET'}:
            icon = 'offset edges.png'
        if self.operator == 'MESH LOOP CUT':
            icon = 'loop_cut.png'
        if self.operator == 'HARD BEVEL':
            icon = 'bevel.png'
        if self.operator == 'MESH CUT':
            icon = 'cut.png'
        icon = icon.replace(' ', '_')
        self.icon = os.path.join(icons_dir, icon)
        self.single_line = upper_text in {'JOIN', 'MERGE', 'SLIDE', 'LINE', 'KNIFE', 'HIDE'}

        self.anchor = 'TOPRIGHT'
        self.offset = (int(region.width - right_x + (line_width * 1.5)), int(region.height - top_y + (line_width * 1.5)))
        self.bg_text = bg_text
        self.top_text = upper_text
        self.bottom_text = lower_text
        self.fat = 2

        self.anim_finished = False

        self.init_theme(context)
        self.init_pixels(context)
        if not hasattr(self, 'pixels'):
            return {'CANCELLED'}

        busy = self.busy

        self.init_draw_pixels(context, event)

        return {'RUNNING_MODAL'}


    @safe_call
    def modal(self, context, event):
        return self.draw_pixels(context, event)
