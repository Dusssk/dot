import bpy

keys = []


def register():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    # Create Mesh keymap
    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi = km.keymap_items.new('wm.call_menu', 'FOUR', 'PRESS', alt=True)
    kmi.properties.name = 'NSOLVE_MT_MainMenu'
    keys.append((km, kmi))

    # Create Object Mode keymap
    km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
    kmi = km.keymap_items.new('wm.call_menu', 'FOUR', 'PRESS', alt=True)
    kmi.properties.name = 'NSOLVE_MT_ObjectMenu'
    keys.append((km, kmi))

    # Create 3D View keymap
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new('wm.call_menu_pie', 'ONE', 'PRESS', alt=True)
    kmi.properties.name = 'NSOLVE_MT_gizmo_pie'
    keys.append((km, kmi))


def unregister():
    for km, kmi in keys:
        km.keymap_items.remove(kmi)
    keys.clear()
