import os
import bpy
import gpu
import blf

from time import time

from gpu.shader import from_builtin
from gpu.types import GPUBatch, GPUIndexBuf, GPUVertBuf, GPUShader, GPUUniformBuf
from mathutils import Vector

from .. utils import safe_call

handlers = []
fonts = {'default': 0}
textures = {}

time_event = None
time_event_users = 0


def load(shader):
    path = os.path.realpath(os.path.join(__file__, '..'))

    file = open(os.path.join(path, shader), 'r')
    data = file.read()
    file.close()

    return data


def load_texture(path):
    image = bpy.data.images.load(path)
    texture = gpu.texture.from_image(image)
    bpy.data.images.remove(image)

    return texture


def new(*stubs, script=False): #XXX: wip
    import bpy

    if bpy.app.version < (3, 4):
        return GPUShader(*(load(s) if script else s for s in stubs))

    import gpu
    from gpu.types import GPUStageInterfaceInfo, GPUShaderCreateInfo
    from uuid import uuid4

    from random import choice
    from string import ascii_lowercase

    interfaces = []
    constants = []

    #XXX: multi vert out
    vert_out = GPUStageInterfaceInfo(F'{"".join(choice(ascii_lowercase) for _ in range(16))}')

    shader_info = GPUShaderCreateInfo()

    new.collect = False
    new.source = ''
    new.step = 0


    def parse(line, vertex=False, fragment=False):
        _type = 'vertex' if vertex else 'fragment'

        if ' ' not in line or line.startswith('//'):
            return

        t = line.split(' ')[1].upper()
        v = line.split(' ')[2][:-1]

        if new.collect:
            new.source += line + '\n'

        elif line.startswith('uniform'):
            if v in constants:
                return

            constants.append(v)

            if line.strip('uniform ').startswith('sampler2D'):
                shader_info.sampler(0, 'FLOAT_2D', v)
                # new.step += 1

                return

            shader_info.push_constant(t, v)

        elif line.startswith('in'):
            if vertex:
                getattr(shader_info, F'{_type}_in')(new.step, t, v)
                new.step += 1
                return

            return

        elif line.startswith('out'):
            if fragment:
                getattr(shader_info, F'{_type}_out')(new.step, t, v)
                new.step += 1
                return

            # if v in interfaces:
            #     return

            # vert_out = GPUStageInterfaceInfo(v)
            # vert_out.smooth(t, v)
            # interfaces.append(v)
            # getattr(shader_info, F'{_type}_out')(vert_out)

            if any(v == i[0] for i in interfaces):
                return

            interfaces.append((v, vert_out.smooth(t, v)))
            getattr(shader_info, F'{_type}_out')(vert_out)

        elif '{' in line:
            new.collect = True
            new.source += line + '\n'

    for i, stub in enumerate(stubs):
        stub = load(stub) if script else stub
        lines = stub.splitlines()

        new.collect = False
        new.source = ''
        new.step = 0

        for line in lines:
            if not line.strip():
                continue

            if i > 1:
                raise ValueError('Shader stubs must be vertex, fragment (WIP)')

            parse(line, vertex=not i, fragment=i)

        if script:
            new.source += '\n}'

        if not i:
            shader_info.vertex_source(new.source)
            continue

        shader_info.fragment_source(new.source)

    return gpu.shader.create_from_info(shader_info)


def handler(idname=''):
    _handlers = [h for h in handlers if h.idname == idname]
    return _handlers[0] if len(_handlers) == 1 else _handlers


def remove_handlers(idname='', force=True):
    for handler in handlers[:]:
        if idname and handler.idname != idname:
            continue

        handler.remove(force=force)


class Frame:
    _exit = False
    _init_location = Vector((0, 0))
    _init_size = Vector((0, 0))

    _location = Vector((0, 0))
    _size = Vector((0, 0))
    _background = Vector((0, 0, 0, 0))
    _foreground = Vector((0, 0, 0, 0))
    _border = Vector((0, 0, 0, 0))
    _corner_radius = Vector((0, 0, 0, 0))
    _corner_chamfer = Vector((0, 0, 0, 0))
    _clipping = Vector((0, 0, 0, 0))

    _image = ''

    delta = 0
    time = 0

    # image = ''
    text = ''
    font = ''

    init_location = (0, 0)
    init_size = (0, 0)

    anim_finished = False

    vertices = ((0, 0), (1, 0), (1, 1), (0, 1))
    indices = ((0, 1, 2), (0, 2, 3))


    @property
    def exit(self):
        return self._exit


    @exit.setter
    def exit(self, value):
        self.anim_finished = False

        self.anim_fade = bool(self.fade_speed)
        self.init_fade_time = time()

        location = self.location.copy()
        self.location = self.init_location.copy()
        self.init_location = location

        size = self.size.copy()
        self.size = self.init_size.copy()
        self.init_size = size

        self._exit = value


    @property
    def init_location(self):
        return self._init_location


    @init_location.setter
    def init_location(self, value):
        self._init_location = Vector(value)


    @property
    def init_size(self):
        return self._init_size


    @init_size.setter
    def init_size(self, value):
        self._init_size = Vector(value)


    @property
    def location(self):
        return self._location


    @location.setter
    def location(self, value):
        self.anim_transform = True
        self.init_transform_time = time()
        self._location = Vector(value)


    @property
    def size(self):
        return self._size


    @size.setter
    def size(self, value):
        self.anim_transform = True
        self.init_transform_time = time()
        self._size = Vector(value)


    @property
    def background(self):
        return self._background


    @background.setter
    def background(self, value):
        self._background = Vector(value)


    @property
    def foreground(self):
        return self._foreground


    @foreground.setter
    def foreground(self, value):
        self._foreground = Vector(value)


    @property
    def corner_radius(self):
        return self._corner_radius


    @corner_radius.setter
    def corner_radius(self, value):
        if not isinstance(value, tuple):
            value = (value, )*4

        self._corner_radius = Vector([int(v) for v in value])


    @property
    def corner_chamfer(self):
        return self._corner_chamfer


    @corner_chamfer.setter
    def corner_chamfer(self, value):
        if not isinstance(value, tuple):
            value = (value, )*4

        self._corner_chamfer = Vector([int(v) for v in value])


    @property
    def border(self):
        return self._border


    @border.setter
    def border(self, value):
        self._border = Vector(value)


    @property
    def clipping(self):
        return self._clipping


    @clipping.setter
    def clipping(self, value):
        if not isinstance(value, tuple):
            value = (value, )*3

        self._clipping = Vector([int(v) for v in value])


    @property
    def image(self):
        return self._image


    @image.setter
    def image(self, value):
        if value not in textures:
            textures[value] = load_texture(value)

        self._image = textures[value]


    def text_dimensions(self):
        blf.size(self.font_id, self.font_size)
        return blf.dimensions(self.font_id, self.text)


    def __init__(self, handler, text='', image='', font='', font_size=12, location=(32, 32), size=(32, 32), foreground=(1, 1, 1, 1), background=(1, 0, 1, 1), border=(1, 1, 0, 1), border_size=2, corner_radius=4, corner_chamfer=False, smoothing=2, clipping=0, anim_speed=0.1, anim_blend='SMOOTHSTEP'):
        self.handler = handler

        self.location = location
        self.init_location = self.location.copy()

        self.size = size
        self.init_size = self.size.copy()

        if isinstance(anim_speed, dict):
            if 'fade' in anim_speed:
                self.fade_speed = anim_speed['fade']
            if 'transform' in anim_speed:
                self.anim_speed = anim_speed['transform']

        else: # isinstance(anim_speed, int) or isinstance(anim_speed, float):
            self.fade_speed = anim_speed
            self.anim_speed = anim_speed

        self.alpha = 1 if not self.fade_speed else 0

        self.anim_blend = anim_blend

        self.init_time = time()
        self.init_fade_time = self.init_time
        self.init_transform_time = self.init_time

        self.anim_fade = bool(self.fade_speed)
        self.anim_transform = bool(self.anim_speed)

        self.background = background
        self.foreground = foreground

        self.border = border if border_size else background
        self.border_size = border_size
        self.corner_radius = corner_radius
        self.corner_chamfer = corner_chamfer
        self.smoothing = int(smoothing)/2
        self.clipping = clipping

        self.styled_frame = bool(background[-1])
        self.styled_border = bool(border[-1])

        if not self.styled_border:
            self.border_size = 0

        if self.styled_frame or self.styled_border:
            self.shader = new('frame.vert', 'frame.frag', script=True)
            self.batch(frame=True)

        self.styled_image = bool(image)

        if self.styled_image:
            self.image = image
            self.image_shader = new('texture.vert', 'texture.frag', script=True)
            self.batch(image=True)

        self.styled_text = bool(text)

        if self.styled_text:
            self.text = text
            self.font = font
            self.font_size = font_size

            if not self.font:
                self.font = 'default'

            elif self.font and self.font not in fonts:
                fonts[self.font] = blf.load(self.font)

            self.font_id = fonts[self.font]


    def anim(self):
        lerp = lambda a, b, t: a + (b - a) * t
        sqrd = lambda a, b, t: lerp(a, b, t * t)
        expo = lambda a, b, t: lerp(a, b, 1 - (1 - t) ** 2)
        smooth = lambda a, b, t: lerp(sqrd(a, b, t), expo(a, b, t), t)
        bounce = lambda a, b, t: smooth(a, b, t * 2 if t * 2 < 1 else 1 - (t - 0.5) if 1 - (t - 0.5) > 0.75 else t)
        if self.anim_blend == 'SMOOTHSTEP':
            return lambda a, b, t: Vector(smooth(a.copy(), b.copy(), t))
        elif self.anim_blend == 'BOUNCE':
            return lambda a, b, t: Vector(bounce(a.copy(), b.copy(), t))
        else: # self.anim_blend == 'LINEAR':
            return lambda a, b, t: Vector(lerp(a.copy(), b.copy(), t))


    def batch(self, frame=False, image=False):
        from gpu_extras.batch import batch_for_shader
        attributes = {
            'pos': self.vertices,
        }

        if frame:
            self.frame_batch = batch_for_shader(self.shader, 'TRIS', attributes, indices=self.indices)

        if image:
            self.image_batch = batch_for_shader(self.image_shader, 'TRIS', attributes, indices=self.indices)


    def draw_frame(self, time):
        if not self.styled_frame and not self.styled_border:
            return

        loc = self.location.copy()
        size = self.size.copy()

        bg = self.background.copy()
        bg[-1] *= self.alpha

        border = self.border.copy()
        border[-1] *= self.alpha

        if not self.anim_finished and self.anim_speed:
            loc = self.anim()(self.init_location, loc, min((time - self.init_transform_time) / self.anim_speed, 1))
            size = self.anim()(self.init_size, size, min((time - self.init_transform_time) / self.anim_speed, 1))

        self.shader.uniform_float('loc', loc)
        self.shader.uniform_float('size', size)

        self.shader.uniform_float('smoothing', self.smoothing)

        self.shader.uniform_float('color', bg)

        self.shader.uniform_float('border', border)
        self.shader.uniform_float('border_size', self.border_size)

        self.shader.uniform_float('corner_radius', self.corner_radius)
        self.shader.uniform_float('corner_chamfer', self.corner_chamfer)

        self.shader.uniform_float('clipping', self.clipping)

        gpu.state.blend_set('ALPHA')
        self.frame_batch.draw(self.shader)


    def draw_image(self, time):
        if not self.styled_image:
            return

        loc = self.location.copy()
        size = self.size.copy()

        fg = self.foreground.copy()
        fg[-1] *= self.alpha

        if not self.anim_finished and self.anim_speed:
            loc = self.anim()(self.init_location, loc, min((time - self.init_transform_time) / self.anim_speed, 1))
            size = self.anim()(self.init_size, size, min((time - self.init_transform_time) / self.anim_speed, 1))

        self.image_shader.uniform_sampler('image', self.image)

        self.image_shader.uniform_float('loc', loc)
        self.image_shader.uniform_float('size', size)

        self.image_shader.uniform_float('smoothing', self.smoothing)

        self.image_shader.uniform_float('corner_radius', self.corner_radius)
        self.image_shader.uniform_float('corner_chamfer', self.corner_chamfer)

        self.image_shader.uniform_float('clipping', self.clipping)

        self.image_shader.uniform_float('alpha', fg[-1])

        gpu.state.blend_set('ALPHA')
        self.image_batch.draw(self.image_shader)


    def draw_text(self, time):
        if not self.styled_text:
            return

        loc = self.location.copy()
        size = self.size.copy()

        fg = self.foreground.copy()
        fg[-1] *= self.alpha

        if not self.anim_finished and self.anim_speed:
            loc = self.anim()(self.init_location, loc, min((time - self.init_transform_time) / self.anim_speed, 1))
            size = self.anim()(self.init_size, size, min((time - self.init_transform_time) / self.anim_speed, 1))

        blf.position(self.font_id, loc.x, loc.y, 0)
        blf.size(self.font_id, self.font_size)

        blf.enable(self.font_id, blf.CLIPPING)
        blf.clipping(self.font_id, loc.x, loc.y, loc.x + size.x, loc.y + size.y)

        blf.disable(self.font_id, blf.SHADOW)

        blf.color(self.font_id, *fg)
        blf.draw(self.font_id, self.text)

        blf.disable(self.font_id, blf.CLIPPING)


    def draw(self, time):
        if self.handler.area != bpy.context.area:
            return

        self.anim_finished = not any((self.anim_fade, self.anim_transform))

        if not self.anim_finished:
            self.delta = time - self.time

        self.time = time

        if self.exit and self.anim_finished:
            return

        if self.fade_speed:
            if self.exit and self.anim_transform and time - self.init_transform_time <= self.anim_speed - self.fade_speed:
                self.init_fade_time = time

            elif self.anim_fade:
                if time - self.init_fade_time >= self.fade_speed:
                    self.anim_fade = False

                fade_value = (time - self.init_fade_time)/self.fade_speed
                self.alpha = max(0, 1 - fade_value) if self.exit else min(1, fade_value)

        elif self.anim_fade:
            self.anim_fade = False

        if self.anim_speed:
            if self.anim_transform and time - self.init_transform_time >= self.anim_speed:
                self.anim_transform = False

        elif self.anim_transform:
            self.anim_transform = False

        self.draw_frame(time)
        self.draw_image(time)
        self.draw_text(time)


class View3DPixel2D:
    area = None
    region = None
    space = None

    timer = None

    elements = []


    def delta(self):
        count = len(self.elements) if self.elements else 1
        return sum((e.delta for e in self.elements)) / count


    def safe_dimensions(self, ignore=''):
        x = 0 # self.region.x
        y = 0 # self.region.y
        w = self.region.width
        h = self.region.height

        min_size = 10
        regions = {}

        for region in self.area.regions:
            if region.width < min_size or region.height < min_size:
                continue

            regions[region.type] = region

        for region_type in regions:
            if region_type == ignore:
                continue

            if region_type == 'TOOL_HEADER':
                h -= regions[region_type].height

            if region_type == 'HEADER':
                h -= regions[region_type].height

            if region_type == 'TOOLS':
                x += regions[region_type].width # - 6
                w -= regions[region_type].width

            if region_type == 'UI':
                w -= regions[region_type].width # - (12 if tpanel.width > 10 else 6)

            if region_type == 'ASSET_SHELF':
                y += regions[region_type].height
                h -= regions[region_type].height

            if region_type == 'ASSET_SHELF_HEADER' and 'ASSET_SHELF' in regions:
                y += regions[region_type].height
                h -= regions[region_type].height

        return x, y, w, h


    def animating_elements(self):
        return any((not e.anim_finished for e in self.elements))


    def add_element(self, element):
        self.elements.append(element)

        return element


    def add_timer(self):
        global time_event, time_event_users

        time_event_users += 1

        if not time_event:
            time_event = bpy.context.window_manager.event_timer_add(1/60, window=bpy.context.window) #XXX: self.window

        self.timer = True


    def remove_element(self, element):
        self.elements.remove(element)


    def remove_timer(self):
        global time_event, time_event_users

        if time_event_users > 0:
            time_event_users -= 1

        if time_event and not time_event_users:
            time_event = bpy.context.window_manager.event_timer_remove(time_event)


    def __init__(self, screen, idname=''):
        handlers.append(self)
        self.idname = idname

        for a in reversed(sorted(screen.areas, key=lambda a: a.width)):
            if a.type != 'VIEW_3D':
                continue

            self.area = a
            break

        if not self.area:
            return

        for r in self.area.regions:
            if r.type != 'WINDOW':
                continue

            self.region = r
            break

        for s in self.area.spaces:
            if s.type != 'VIEW_3D':
                continue

            self.space = s
            break

        self.pause_redraw = False
        self.pause_redraw_init = 0

        self.canvas = self.space.draw_handler_add(self.draw, (), 'WINDOW', 'POST_PIXEL')

        self.add_timer()


    def update(self, event=None, force=False):
        _time = time()

        if force or (event and event.type == 'TIMER') or (not event and not force):
            if not self.pause_redraw:
                self.area.tag_redraw()

            if self.animating_elements():
                self.pause_redraw = False
                self.pause_redraw_init = _time
                return

            self.pause_redraw = _time - self.pause_redraw_init > 1/60


    @safe_call
    def draw(self):
        _time = time()

        for element in self.elements[:]:
            element.draw(_time)

            if element.exit and element.anim_finished:
                self.remove_element(element)

        if not self.elements:
            self.remove()


    def remove(self, force=False):
        if force:
            for element in self.elements[:]:
                self.remove_element(element)

            if self.canvas:
                self.space.draw_handler_remove(self.canvas, 'WINDOW')

            self.remove_timer()

            if self in handlers:
                handlers.remove(self)

            return

        for element in self.elements:
            if element.exit:
                continue

            element.exit = True

        if not self.elements and self.canvas:
            self.space.draw_handler_remove(self.canvas, 'WINDOW')
            self.canvas = None

            self.remove_timer()

            if self in handlers:
                handlers.remove(self)

