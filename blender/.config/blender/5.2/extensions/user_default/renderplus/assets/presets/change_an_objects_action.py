import bpy

batch = bpy.context.scene.renderplus.batch
jobs = batch.jobs
current = jobs[batch.index]

current.custom_overrides.clear()
item_sub_1 = current.custom_overrides.add()
item_sub_1.name = "Change an object's action"
item_sub_1.path = "bpy.context.scene.objects['MY OBJECT'].animation_data.action"
item_sub_1.data = "bpy.data.actions['MY ACTION']"
item_sub_1.enabled = True
