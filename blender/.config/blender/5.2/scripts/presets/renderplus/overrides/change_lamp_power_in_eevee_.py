import bpy

batch = bpy.context.scene.renderplus.batch
jobs = batch.jobs
current = jobs[batch.index]

current.custom_overrides.clear()
item_sub_1 = current.custom_overrides.add()
item_sub_1.name = "Change lamp power in Eevee"
item_sub_1.path = "bpy.context.scene.objects['MY LAMP'].data.energy"
item_sub_1.data = "20"
item_sub_1.enabled = True
