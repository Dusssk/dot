import bpy

batch = bpy.context.scene.renderplus.batch
jobs = batch.jobs
current = jobs[batch.index]

current.custom_overrides.clear()
item_sub_1 = current.custom_overrides.add()
item_sub_1.name = "Hide an object"
item_sub_1.path = "bpy.context.scene.objects['MY OBJECT'].hide_render"
item_sub_1.data = "True"
item_sub_1.enabled = True
