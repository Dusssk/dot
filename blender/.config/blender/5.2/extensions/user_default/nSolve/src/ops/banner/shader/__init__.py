import os
import bpy
import gpu
import blf

from time import time

from gpu.shader import from_builtin
from gpu.types import GPUBatch, GPUIndexBuf, GPUVertBuf, GPUShader, GPUUniformBuf
from mathutils import Vector

from .. utils import safe_call

running = []
handles = {}
textures = {}

timer = False # app_timer arg
timer_users = 0

time_event = None
time_event_users = 0


def load_texture(path):
    image = bpy.data.images.load(path)
    texture = gpu.texture.from_image(image)
    bpy.data.images.remove(image)

    return texture


def app_timer_tag_redraw(): #XXX: limited support
    tagged = []
    for pixels in running:
        if not pixels.app_timer:
            continue

        pixels.update(force=True)

        if pixels.area not in tagged and not pixels.pause_redraw:
            pixels.area.tag_redraw()
            tagged.append(pixels.area)

        if any([e.anim_fade or e.anim_xform for e in pixels.elements]):
            pixels.pause_redraw = False
            pixels.pause_redraw_init = time()
            continue

        pixels.pause_redraw = time() - pixels.pause_redraw_init > 1/60

    return 1/60


class Frame:
    _exit = False
    _location = Vector((0, 0))
    _size = Vector((0, 0))

    icon = None
    icon_width = 0
    icon_height = 0

    text = ''

    single_area = True

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
    def location(self):
        return self._location


    @location.setter
    def location(self, value):
        self.anim_xform = True
        self.init_xform_time = time()
        self._location = value


    @property
    def size(self):
        return self._size


    @size.setter
    def size(self, value):
        self.anim_xform = True
        self.init_xform_time = time()
        self._size = value


    def __init__(self, area_size, icon='', text='', font=0, loc=(0, 0), size=(0, 0), clip_location=(0, 0), clip_size=(0, 0), bg=(0, 0, 0, 0), fg=(1, 1, 1, 1), border=(0, 0, 0, 0), border_size=1, corner_radius=3, icon_size=16, icon_loc=(0, 0), font_size=12, speed=0.05, anim='LINEAR', bounce=1):

        self.size = Vector((size[0], size[1]))
        self.init_size = self.size.copy()
        self.icon_size = icon_size
        self.area_size = Vector((area_size[0], area_size[1]))
        self.clip_size = Vector((clip_size[0], clip_size[1]))

        self.location = Vector((loc[0], loc[1]))
        self.init_location = self.location.copy()
        self.icon_location = Vector((icon_loc[0], icon_loc[1]))
        self.clip_location = Vector((clip_location[0], clip_location[1]))

        self.fade_speed = 0
        self.anim_speed = 0

        if isinstance(speed, int) or isinstance(speed, float):
            self.fade_speed = speed
            self.anim_speed = speed

        elif isinstance(speed, dict):
            if 'fade' in speed:
                self.fade_speed = speed['fade']
            if 'anim' in speed:
                self.anim_speed = speed['anim']

        self.alpha = 1 if not self.fade_speed else 0

        self.anim_type = anim
        self.bounces = bounce
        self.bounce_count = 0

        self.init_time = time()
        self.init_fade_time = self.init_time
        self.init_xform_time = self.init_time

        self.anim_fade = bool(self.fade_speed)
        self.anim_xform = bool(self.anim_speed)

        self.background = Vector(bg)
        self.foreground = Vector(fg)

        self.border = Vector(border)
        self.border_size = border_size
        self.corner_radius = corner_radius

        self.styled_frame = bool(bg[-1])
        self.styled_border = bool(border[-1])

        if not self.styled_border:
            self.border_size = 0

        if self.styled_frame or self.styled_border:
            if icon and not self.size.x:
                self.size.x = self.icon_size

            if icon and not self.size.y:
                self.size.y = self.icon_size

            self.shader = new('frame.vert', 'frame.frag', script=True)
            self.batch(frame=True)

        self.styled_icon = bool(icon)

        if self.styled_icon:
            #XXX: add user consideration
            if icon not in textures:
                textures[icon] = load_texture(icon) # should store user count as well

            self.icon = textures[icon] # should remove icon on exit (if 0 users)

            self.icon_shader = new('icon.vert', 'icon.frag', script=True)
            self.batch(icon=True)

        self.styled_text = bool(text)

        if self.styled_text:
            self.font_id = font
            self.text = text
            self.font_size = font_size


    def anim(self):
        lerp = lambda a, b, t: a + (b - a) * t
        sqrd = lambda a, b, t: lerp(a, b, t * t)
        expo = lambda a, b, t: lerp(a, b, 1 - (1 - t) ** 2)
        smooth = lambda a, b, t: lerp(sqrd(a, b, t), expo(a, b, t), t)
        bounce = lambda a, b, t: smooth(a, b, t * 2 if t * 2 < 1 else 1 - (t - 0.5) if 1 - (t - 0.5) > 0.75 else t)
        if self.anim_type == 'SMOOTHSTEP':
            return lambda a, b, t: Vector(smooth(a.copy(), b.copy(), t))
        elif self.anim_type == 'BOUNCE':
            return lambda a, b, t: Vector(bounce(a.copy(), b.copy(), t))
        else: # self.anim_type == 'LINEAR':
            return lambda a, b, t: Vector(lerp(a.copy(), b.copy(), t))


    def batch(self, frame=False, icon=False, loc=Vector()):
        from gpu_extras.batch import batch_for_shader
        if frame:
            attributes = {
                'pos': self.vertices,
            }

            self.frame_batch = batch_for_shader(self.shader, 'TRIS', attributes, indices=self.indices)

        if icon:
            w = self.icon.width
            h = self.icon.height

            diff = 1.0
            if self.icon_size < h:
                diff = h/self.icon_size

            elif h < self.icon_size:
                diff = h/self.icon_size

            w /= diff
            h /= diff

            x = self.location.x
            y = self.location.y# - self.icon_size/2

            if loc:
                x = loc.x
                y = loc.y

            xn = 0
            if x:
                xn = 1/(self.area_size.x/x)

            yn = 0
            if y:
                yn = 1/(self.area_size.y/y)

            ixn = 1/(self.area_size.x/(x+w))
            iyn = 1/(self.area_size.y/(y+h))

            attributes = {
                'pos': ((xn, yn), (1*ixn, yn), (1*ixn, 1*iyn), (xn, 1*iyn)),
                'coord': self.vertices,
            }

            self.icon_batch = batch_for_shader(self.icon_shader, 'TRI_FAN', attributes)


    def draw_frame(self, time):
        if not self.styled_frame and not self.styled_border:
            return

        loc = self.location.copy()
        size = self.size.copy()

        if not self.anim_finished and self.anim_speed:
            loc = self.anim()(self.init_location, loc, min((time - self.init_xform_time) / self.anim_speed, 1))
            size = self.anim()(self.init_size, size, min((time - self.init_xform_time) / self.anim_speed, 1))

        bg = self.background.copy()
        bg[-1] *= self.alpha

        border = self.border.copy()
        border[-1] *= self.alpha

        self.shader.uniform_float('color', bg)
        self.shader.uniform_float('edge', border)

        self.shader.uniform_float('loc', loc)
        self.shader.uniform_float('size', size)

        self.shader.uniform_float('border', Vector((self.border_size, self.corner_radius)))

        gpu.state.blend_set('ALPHA')
        self.frame_batch.draw(self.shader)


    def draw_icon(self, time):
        if not self.styled_icon:
            return

        loc = self.location.copy()
        size = self.size.copy()

        if not self.anim_finished and self.anim_speed:
            loc = self.anim()(self.init_location, loc, min((time - self.init_xform_time) / self.anim_speed, 1))
            size = self.anim()(self.init_size, size, min((time - self.init_xform_time) / self.anim_speed, 1))

            self.batch(icon=True, loc=loc)

        # self.icon_shader.uniform_float('loc', loc)
        # self.icon_shader.uniform_float('size', size)

        fg = self.foreground.copy()
        fg[-1] *= self.alpha

        self.icon_shader.uniform_sampler('icon', self.icon)

        self.icon_shader.uniform_float('loc', loc)
        self.icon_shader.uniform_float('size', size)

        self.icon_shader.uniform_float('alpha', fg[-1])

        gpu.state.blend_set('ALPHA')
        self.icon_batch.draw(self.icon_shader)


    def draw_text(self, time):
        if not self.styled_text:
            return

        loc = self.location.copy()
        clip_loc = self.clip_location.copy()
        clip_size = self.clip_size.copy()
        size = self.size.copy()

        if not self.anim_finished and self.anim_speed:
            loc = self.anim()(self.init_location, loc, min((time - self.init_xform_time) / self.anim_speed, 1))
            size = self.anim()(self.init_size, size, min((time - self.init_xform_time) / self.anim_speed, 1))

        fg = self.foreground.copy()
        fg[-1] *= self.alpha
        isclip = any([self.clip_location.x, self.clip_location.y, self.clip_size.x, self.clip_size.y])
        issize = any([self.size.x, self.size.y])

        blf.color(self.font_id, *fg)
        blf.size(self.font_id, self.font_size)

        w, h = blf.dimensions(self.font_id, self.text)

        x = loc.x
        y = loc.y

        if self.icon:
            x += self.icon_size + self.font_size/2
            y += self.icon_size/2 - h/2# + self.font_size/8

            if w > self.size.x:
                self.size.x = w + self.icon_size + self.font_size/2

        if isclip:
            blf.enable(self.font_id, blf.CLIPPING)
            blf.clipping(self.font_id, clip_loc.x, clip_loc.y, clip_loc.x + clip_size.x, clip_loc.y + clip_size.y)
        elif issize:
            blf.enable(self.font_id, blf.CLIPPING)
            blf.clipping(self.font_id, loc.x, loc.y, loc.x + size.x, loc.y + size.y)

        blf.position(self.font_id, x, y, 0)

        #XXX: trim
        # while (self.text and blf.dimensions(self.font_id, self.text)[0] > self.size.x - pos_x - self.border_size - self.font_size/4):
        #     self.text = self.text[:-1]

        blf.disable(self.font_id, blf.SHADOW)

        blf.draw(self.font_id, self.text)

        blf.disable(self.font_id, blf.CLIPPING)


    def draw(self, area, time):
        if self.single_area and area != bpy.context.area:
            return

        self.anim_finished = not any((self.anim_fade, self.anim_xform))

        if self.exit and self.anim_finished:
            return

        if self.fade_speed:
            if self.anim_fade:
                if time - self.init_fade_time >= self.fade_speed:
                    self.anim_fade = False

                self.alpha = min(1, (time - self.init_fade_time)/self.fade_speed) if not self.exit else max(0, 1-(time-self.init_fade_time)/self.fade_speed)

        elif self.anim_fade:
            self.anim_fade = False

        if self.anim_speed:
            if self.anim_xform and time - self.init_xform_time >= self.anim_speed:
                self.anim_xform = False

        elif self.anim_xform:
            self.anim_xform = False

        self.draw_frame(time)
        self.draw_icon(time)
        self.draw_text(time)


class View3DPixel2D:
    exit = False

    area = None
    region = None
    space = None

    timer = None

    elements = []


    def __init__(self, screen, idname='', app_timer=False):
        running.append(self)
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

        self.size = Vector((self.area.width, self.area.height))

        for s in self.area.spaces:
            if s.type != 'VIEW_3D':
                continue

            self.space = s
            break

        # for region in self.area.regions:
        #     if region.type != 'HEADER' or region.height == 1:
        #         continue

        #     self.size.y -= region.height
        # self.size.y -= 1

        self.pause_redraw = False
        self.pause_redraw_init = 0
        if self.idname in handles:
            self.handle = handles[self.idname][0]
            handles[self.idname][1] += 1
        else:
            self.handle = self.space.draw_handler_add(self.draw, (), 'WINDOW', 'POST_PIXEL')
            handles[self.idname] = [self.handle, 1]

        self.add_timer(app_timer)


    def add_element(self, element):
        self.elements.append(element)

        return element


    def remove_element(self, element):
        self.elements.remove(element)


    def update(self, event=None, force=False): # if driving with event timers
        if force or (event and event.type == 'TIMER') or (not event and not force):
            if not self.pause_redraw:
                self.area.tag_redraw()

            if any([e.anim_fade or e.anim_xform for e in self.elements]):
                self.pause_redraw = False
                self.pause_redraw_init = time()
                return

            self.pause_redraw = time() - self.pause_redraw_init > 1/60


    @safe_call
    def draw(self):
        _time = time()

        for element in self.elements[:]:
            element.draw(self.area, _time)

            if element.exit and element.anim_finished:
                self.remove_element(element)

        if not self.elements:
            self.remove()


    def add_timer(self, app_timer):
        global timer, timer_users
        global time_event, time_event_users

        self.app_timer = app_timer

        if app_timer:
            timer_users += 1

            if not timer:
                bpy.app.timers.register(app_timer_tag_redraw, first_interval=1/60, persistent=True)

                timer = True
                self.timer = True

            return

        time_event_users += 1

        if not time_event:
            time_event = bpy.context.window_manager.event_timer_add(1/60, window=bpy.context.window) #XXX: self.window

        self.timer = True


    def remove_timer(self):
        global timer, timer_users
        global time_event, time_event_users

        if self.app_timer:
            self.app_timer = False

            if timer_users > 0:
                timer_users -= 1

            if not timer_users and bpy.app.timers.is_registered(app_timer_tag_redraw):
                bpy.app.timers.unregister(app_timer_tag_redraw)
                timer = False
                self.timer = False

            return

        if time_event_users > 0:
            time_event_users -= 1

        if time_event and not time_event_users:
            time_event = bpy.context.window_manager.event_timer_remove(time_event)


    def remove(self, force=False):
        if self in running:
            running.remove(self)

        if force or not self.elements and self.timer:
            self.remove_timer()

        if force and self.handle:
            handles[self.idname][1] -= 1
            if handles[self.idname][1] == 0:
                del handles[self.idname]
                self.space.draw_handler_remove(self.handle, 'WINDOW')

            for element in self.elements[:]:
                self.remove_element(element)

            self.exit = True
            self.handle = None

            self.remove_timer()
            return

        for element in self.elements[:]:
            if not element.exit:
                element.exit = True

        if not self.elements and self.handle:
            handles[self.idname][1] -= 1
            if handles[self.idname][1] == 0:
                del handles[self.idname]
                self.space.draw_handler_remove(self.handle, 'WINDOW')

            self.exit = True
            self.handle = None

            self.remove_timer()


def load(shader):
    path = os.path.realpath(os.path.join(__file__, '..'))

    file = open(os.path.join(path, shader), 'r')
    data = file.read()
    file.close()

    return data


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

