import bpy, numpy

from . object import smooth_batch_set


def shade_smooth():

    if bpy.app.version[:2] >= (4, 2):
        smooth_batch_set(bpy.context.selected_objects, True)

    elif bpy.app.version[:2] > (3, 2):
        dic = {}
        for obj in bpy.context.selected_objects:
            if obj.type != 'MESH': continue
            dic[obj] = (obj.data.use_auto_smooth, obj.data.auto_smooth_angle)
        bpy.ops.object.shade_smooth()
        for obj, val in dic.items():
            obj.data.use_auto_smooth = val[0]
            obj.data.auto_smooth_angle = val[1]
    else:
        bpy.ops.object.shade_smooth()
