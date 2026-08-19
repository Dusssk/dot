import bpy
import bmesh
from mathutils import Vector, Matrix
from ... utils.objects import set_active
from ... material import assign_material, blank_cutting_mat, get_active_material
from ... utility import addon, version
from ... utility import collections, modifier, geometry_nodes, object, ct_modifier
from ... utility.renderer import cycles
from . editmode_knife import edit_bool_knife

# TODO: Add KNIFE

def add(context, operation='DIFFERENCE', collection='Cutters', boolshape=True, sort=True, outset=False, thickness=0.5, keep_bevels=False, parent=False, inset_active=True, inset_slice=False, transfer_normals=False, weld=False, merge_threshold=0.0001, stitch_distance=0.0001):

    selection = context.selected_objects
    active_object = context.active_object
    cutters = [object for object in selection if object != active_object and object.type in { "MESH", 'FONT', 'CURVE', 'SURFACE', 'META'}]

    solidify_list = []
    nodes_list = []

    nodes = addon.preference().property.workflow_modifier == 'NODES'

    if not nodes:
        cutters = [swap_cutter(context, o) if o.type!='MESH' else o  for o in cutters ]

    col = collections.hops_col_get(context)
    collections.view_layer_unhide(col, enable=True)

    #do separate nodes workflow
    if nodes:
        auto_smooth_pref = addon.preference().behavior.auto_smooth and addon.preference().property.workflow == "NONDESTRUCTIVE"
        active_auto_smooth = object.get_auto_smooth(context.active_object)[0]
        cutter_auto_smooth = False

        for c in cutters:
            if c.type != 'FONT': continue

            # check if we already added decimate
            decimates = [mod for mod in c.modifiers if mod.type == 'DECIMATE']

            if not decimates:
                decimate = c.modifiers.new("Decimate",type='DECIMATE')
                decimate.decimate_type = 'DISSOLVE'

        if auto_smooth_pref:
            # for transfer automsooth cutters regardless of active object's smoothing
            # TODO: pref to not affect shading at all?
            if transfer_normals:
                object.smooth_batch_set(cutters, True)
                cutter_auto_smooth = True

            # match classic
            elif active_auto_smooth:
                object.smooth_batch_set(cutters, True)
                cutter_auto_smooth = False


        for cutter in cutters:
            cutter_shared(context, collection, boolshape, parent, active_object, cutter)

            boolean = geometry_nodes.NodeBoolean.from_object(active_object)
            boolean.name = 'Boolean'
            nodes_list.append(boolean)

            boolean.object = cutter
            boolean.solver = addon.preference().property.boolean_solver
            boolean.show_in_editmode = True

            if cutter.type !='META':
                object.set_auto_smooth(cutter, cutter_auto_smooth)

            if operation == 'SLASH':
                boolean.operation = 'DIFFERENCE'

            else:
                boolean.operation = operation

            boolean.inset_thickness = thickness
            boolean.transfer_normals = transfer_normals
            boolean.weld = weld
            boolean.merge_threshold = merge_threshold
            boolean.stitch_distance = stitch_distance

            mat = get_active_material(context)
            if mat:
                boolean.material_cut = True
                boolean.material = mat

            set_active(cutter, select=True, only_select=True)


        if sort:
            modifier.user_sort(active_object)

        if operation == 'SLASH' or (operation == 'INSET' and inset_slice):
            for node_mod in nodes_list:
                name = node_mod.name

                new_obj = active_object.copy()
                new_obj.data = active_object.data.copy()

                for col in active_object.users_collection:
                    if col not in new_obj.users_collection:
                        col.objects.link(new_obj)

                new_obj_bool = geometry_nodes.NodeBoolean.new_unchecked(new_obj.modifiers[name])
                new_obj_bool.material = node_mod.material
                node_mod.material = None

                if operation == 'SLASH':
                    new_obj_bool.operation = 'INTERSECT'

                else:
                    new_obj_bool.inset_slice = inset_slice

        if addon.preference().property.workflow == "DESTRUCTIVE":
            for node in nodes_list:
                mod = node.modifier

                modifier.apply(mod.id_data, mod=mod)

            nodes_list.clear()
            for cutter in cutters:
                bpy.data.objects.remove(cutter, do_unlink=True)

            set_active(active_object, select=True, only_select=True)

        return nodes_list

    if addon.preference().behavior.auto_smooth and addon.preference().property.workflow == "NONDESTRUCTIVE":
        use_smooth = object.get_auto_smooth(context.active_object)[0]

        for cutter in cutters:
            if use_smooth:
                if bpy.app.version[:2] < (4, 1):
                    cutter.data.use_auto_smooth = True

                else:
                    object.set_auto_smooth(cutter, False)

                for f in cutter.data.polygons:
                    f.use_smooth = True


    for cutter in cutters:
        cutter_shared(context, collection, boolshape, parent, active_object, cutter)

        data = cutter.data
        if bpy.app.version[:2] < (3, 4):
            data.use_customdata_edge_bevel = True

        if operation in {'SLASH', 'INSET'}:
            # TODO: material setup to be moved away

            new_obj = active_object.copy()
            new_obj.data = active_object.data.copy()

            for col in active_object.users_collection:
                if col not in new_obj.users_collection:
                    col.objects.link(new_obj)

            modifier_new_obj = new_obj.modifiers.new(name="Boolean", type="BOOLEAN")

            if bpy.app.version >= (2, 91, 0):
                modifier_new_obj.show_in_editmode = True

            modifier_new_obj.operation = "INTERSECT"
            if hasattr(modifier_new_obj, 'solver'):
                modifier_new_obj.solver = addon.preference().property.boolean_solver
            modifier_new_obj.object = cutter

            if operation == 'INSET':
                new_obj.display_type = 'WIRE'
                new_obj.hops.status = "BOOLSHAPE"
                new_obj.hide_render = True
                cycles.hide_preview(context, new_obj)

                option = context.window_manager.Hard_Ops_material_options

                index = 0

                if option.material_mode == 'BLANK':
                    blank_cutting_mat()

                if option.active_material:
                    mat = bpy.data.materials[option.active_material ]
                    mats = [slot.material for slot in active_object.material_slots]

                    if mat not in mats:
                        active_object.data.materials.append(mat)
                        new_obj.data.materials.append( mat )

                    index = active_object.material_slots.find (mat.name)


                collections.unlink_obj(context, new_obj)
                collections.link_obj(context, new_obj, collection)

                if parent:
                    if cutter.parent != active_object:
                        new_obj.parent = active_object
                        new_obj.matrix_parent_inverse = active_object.matrix_world.inverted()

                if sort:
                    modifier.user_sort(new_obj)

                #only keep mods below active boolean
                for mod in reversed(new_obj.modifiers):
                    if mod == modifier_new_obj:
                        break

                    new_obj.modifiers.remove(mod)

                for mod in new_obj.modifiers:
                    if mod.type == 'BEVEL' and not keep_bevels:
                        if mod.limit_method not in {'VGROUP', 'WEIGHT'}:
                            mod.show_render = mod.show_viewport = False
                    elif mod.type == 'WEIGHTED_NORMAL' or geometry_nodes.SmoothByAngle.is_valid_modifier(mod):
                        new_obj.modifiers.remove(mod)

                solidify = new_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
                solidify.show_expanded = True
                solidify.use_even_offset = True
                solidify.thickness = thickness
                solidify.offset = 0.0
                solidify.material_offset = index
                solidify_list.append(solidify)

                ct_modifier.mod_move_up(solidify)

                if inset_slice and not outset:
                    slice_inset = active_object.copy()
                    slice_inset.data = active_object.data.copy()

                    for col in active_object.users_collection:
                            col.objects.link(slice_inset)

                    mod = slice_inset.modifiers.new(name="Boolean", type="BOOLEAN")
                    mod.operation = 'INTERSECT'
                    mod.object = new_obj

                    # if addon.preference().property.workflow == "DESTRUCTIVE":
                    #     override = {'object': slice_inset, 'active_object': slice_inset}
                    #     bpy.ops.object.modifier_apply(override, modifier = mod.name)


            if operation == 'SLASH':
                if addon.preference().property.workflow == "DESTRUCTIVE":
                    set_active(new_obj)
                    modifier.apply(new_obj, types={"BOOLEAN"})

                assign_material(context, new_obj , csplit=True)

                new_obj.select_set(False)

        if operation in {'DIFFERENCE', 'UNION', 'INTERSECT', 'SLASH', 'INSET'}:
            boolean = active_object.modifiers.new("Boolean", "BOOLEAN")

            if bpy.app.version >= (2, 91, 0):
                boolean.show_in_editmode = True

            if hasattr(boolean, 'solver'):
                boolean.solver = addon.preference().property.boolean_solver
            if operation in {'SLASH', 'INSET'}:

                boolean.operation = 'DIFFERENCE'

                if operation == 'INSET':
                    if outset:
                        boolean.operation = 'UNION'
                    boolean.object = new_obj
                else:
                    boolean.object = cutter

            else:
                boolean.operation = operation
                boolean.object = cutter
                assign_material(context, cutter)

            boolean.show_expanded = False

        if sort:
            if operation == 'SLASH':
                modifier.user_sort(new_obj)

    if sort:
        modifier.user_sort(active_object)

    if operation == 'SLASH':
        modifier.sort(new_obj, types=['WEIGHTED_NORMAL'], last=True)
    modifier.sort(active_object, types=['WEIGHTED_NORMAL'], last=True)

    if addon.preference().property.workflow == "DESTRUCTIVE":
        if operation == 'INSET':
            set_active(new_obj, select=True, only_select=True)
        else:
            set_active(active_object, select=True, only_select=True)
            modifier.apply(active_object, types={"BOOLEAN"})
            for cutter in cutters:
                bpy.data.objects.remove(cutter, do_unlink=True)

        # for col in bpy.data.collections:
        #     if col.name == 'Cutters' and not col.objects[:]:
        #         bpy.data.collections.remove(col)

        col = collections.hops_col_get(context)

        if not col.objects:
            bpy.data.collections.remove(col)

    elif addon.preference().property.workflow == "NONDESTRUCTIVE":
        to_select = new_obj if operation == 'INSET' and inset_active else cutters[0]
        set_active(to_select, select=True, only_select=True)

    #pass modifiers to modal bool
    return solidify_list

def cutter_shared(context, collection, boolshape, parent, active_object, cutter):
    if cutter.rigid_body:
        set_active(cutter)
        bpy.ops.rigidbody.object_remove()

    if boolshape:
        cutter.display_type = 'WIRE'
        cutter.hops.status = "BOOLSHAPE"
        cutter.hide_render = True
        cycles.hide_preview(context, cutter)

        collections.unlink_obj(context, cutter)
        collections.link_obj(context, cutter, collection)

    if parent:
        if cutter.parent != active_object:
            eval_obj = cutter.evaluated_get(context.evaluated_depsgraph_get())
            temp_matrix = eval_obj.matrix_world.copy()
            cutter.parent = active_object
            cutter.matrix_parent_inverse = active_object.matrix_world.inverted()
            cutter.matrix_world = temp_matrix
            del temp_matrix

# TODO: Fix slash to others cut
# TODO: Fix Inset
def shift(context, operation='DIFFERENCE', collection='Cutters', boolshape=True, sort=True, outset=False, thickness=0.5, keep_bevels=False, parent=False, inset_slice = False, transfer_normals=False, weld=False, merge_threshold=0.0001, stitch_distance=0.0001):
    selection = set(context.selected_objects)

    objects = [[obj, mod, modifier.bool_object_get(mod)] for obj in context.blend_data.objects if obj.users_collection for mod in obj.modifiers if mod.type in {'BOOLEAN', 'NODES'} if obj.hops.status == 'BOOLSHAPE' or obj.visible_get()]

    objects = [arr for arr in objects if arr[2]]

    # doubles = [obj for obj in selection for mod in obj.modifiers if mod.type in ['BOOLEAN'] and mod.operation == 'INTERSECT' or mod.type in ['SOLIDIFY']]
    # slash = list(set(doubles))

    diff_cutters = set()
    inter_cutters = set()
    insets = []
    slices = {}
    inset_data = []
    deletables = set()

    for obj, mod, cutter in objects:

        if cutter in selection:
            node_mod = False

            wrapper = geometry_nodes.NodeBoolean.new(mod)

            if wrapper:
                mod = wrapper
                node_mod = wrapper

            if mod.operation == 'DIFFERENCE':
                diff_cutters.add(cutter)

            elif mod.operation == 'INTERSECT':
                inter_cutters.add(cutter)

                if not node_mod and [m for m in obj.modifiers if m.type == 'SOLIDIFY']:
                    insets.append(obj)
                    object_op = [(o, mod.operation) for o in context.blend_data.objects for mod in o.modifiers if mod.type == 'BOOLEAN' and mod.object and mod.object is obj]

                    deletables.update( item[0] for item in object_op if item[1] == 'INTERSECT')
                    inset_data.extend( [(item[0], None, cutter) for item in object_op] )

            elif mod.operation == 'INSET':
                if mod.inset_slice:
                    inter_cutters.add(cutter)
                else:
                    diff_cutters.add(cutter)

            slices[cutter.name] = obj

            obj.modifiers.remove(mod if not wrapper else mod.modifier)

    slicers = diff_cutters.intersection(inter_cutters)
    deletables.update(slices[slicer.name] for slicer in slicers)
    deletables.update(insets)

    for item in objects:
        if item[0] in inset_data:
            item[2] = inset_data[item[0]]

    objects = [item for item in objects + inset_data if item[0] not in deletables]
    for obj in deletables:
        selection.discard(obj)
        bpy.data.objects.remove(obj)

    for obj in selection:
        obj.select_set(False)

    for obj, mod, cutter in objects:
        if cutter in selection:
            cutter.select_set(True)
            set_active(obj, select=True, only_select=False)
            add(context, operation=operation, collection=collection, boolshape=boolshape, sort=sort, outset=outset, thickness=thickness, keep_bevels=keep_bevels, parent=parent, inset_active = False, inset_slice=inset_slice, transfer_normals=transfer_normals, weld=weld, merge_threshold=merge_threshold, stitch_distance=stitch_distance)
            cutter.select_set(False)
            obj.select_set(False)

    for obj in selection:
        obj.select_set(True)


# TODO: redo intersection with bmesh
# TODO: add material cutting
def knife(context, knife_project, material_cut = False, cut_through=True, projection='VIEW'):
    selected = context.selected_objects[:]
    cutters = [o for o in selected if o is not context.active_object and o.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}]
    if not cutters:
        return {'CANCELLED'}

    if knife_project:
        for cutter in cutters:
            edge_split = cutter.modifiers.new("Edge Split", 'EDGE_SPLIT')
            edge_split.use_edge_angle = True
            edge_split.split_angle = 0.0
            cutter.select_set(False)

        bpy.ops.object.mode_set(mode='EDIT')

        if projection == 'VIEW':
            for cutter in cutters: cutter.select_set(True)
            bpy.ops.mesh.knife_project(cut_through=cut_through)

        else:
            view = context.region_data.view_matrix.copy()
            persp = context.region_data.view_perspective
            context.region_data.view_perspective = 'ORTHO'

            if projection[0] == 'X':
                normal = Vector((1, 0, 0))

            elif projection[0] == 'Y':
                normal = Vector((0, 1, 0))

            elif projection[0] == 'Z':
                normal = Vector((0, 0, 1))

            if projection[1] == '-' : normal *= -1.0

            tangent = normal.orthogonal()
            tangent.normalize()
            cross = normal.cross(tangent)
            cross.normalize()
            matrix = Matrix()
            matrix.col[0] = [*tangent, 0]
            matrix.col[1] = [*cross, 0]
            matrix.col[2] = [*normal, 0]

            for cutter in cutters:
                cutter_mat = cutter.matrix_world.normalized()
                context.region_data.view_matrix = (cutter_mat @ matrix).inverted()
                context.region_data.update()

                cutter.select_set(True)
                bpy.ops.mesh.knife_project(cut_through=cut_through)
                cutter.select_set(False)

            context.region_data.view_matrix = view
            context.region_data.view_perspective = persp
            context.region_data.update()

        bpy.ops.object.mode_set(mode='OBJECT')


        for cutter in cutters:
            edge_split = cutter.modifiers[-1]
            cutter.modifiers.remove(edge_split)

    else:

        target = context.active_object

        for o in selected:
            o.select_set(False)

        edge_mark = False # placeholder

        for cutter in cutters:

            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(target.data)
            start_id = len(bm.faces)

            for f in bm.faces:
                f.select = False
                f.hide = False

            depsgraph = context.evaluated_depsgraph_get()
            eval_obj = cutter.evaluated_get(depsgraph)
            temp_mesh = eval_obj.to_mesh()
            temp_mesh.transform(target.matrix_world.inverted() @ cutter.matrix_world )
            bm.from_mesh(temp_mesh)
            eval_obj.to_mesh_clear()

            cutter_faces = bm.faces[start_id:]
            for face in cutter_faces:
                face.select = True

            bmesh.update_edit_mesh(target.data)

            if 'solver' in bpy.types.BooleanModifier.bl_rna.properties:
                bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode='CUT', threshold=1e-06, solver=version.bsolver_fast())
            else:
                bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode='CUT', threshold=1e-06)

            #find linked faces that belong to the cutter geo
            while True:

                ret = bmesh.ops.region_extend(bm, geom = cutter_faces, use_contract =0, use_faces = 1, use_face_step = 1)
                if not ret['geom']:
                    break
                cutter_faces.extend(ret['geom'] )

            bmesh.ops.delete(bm, geom = cutter_faces, context = 'FACES')

            #bmesh.update_edit_mesh(target.data)
            if  edge_mark:
                # create crease and bevel layers if ther are none
                edge_layers = bm.edges.layers
                if 'SubSurfCrease' not in edge_layers.crease:
                    edge_layers.crease.new('SubSurfCrease')
                if 'BevelWeight' not in edge_layers.bevel_weight:
                    edge_layers.bevel_weight.new('BevelWeight')

                new_edges = [e for e in bm.edges if e.select]
                crease = edge_layers.crease['SubSurfCrease']
                bevel = edge_layers.bevel_weight['BevelWeight']

                for e in new_edges:
                    e[crease] = 1
                    e[bevel] = 1
                    e.smooth = False
                    e.seam = True

            if material_cut:
                option = context.window_manager.Hard_Ops_material_options
                if option.material_mode == 'BLANK':
                    blank_cutting_mat()

                if option.active_material:

                    bpy.ops.mesh.loop_to_region(select_bigger=False)
                    faces = [f for f in bm.faces if f.select]

                    if len(faces) < len (bm.faces):

                        if  option.active_material not in target.data.materials:
                            target.data.materials.append( bpy.data.materials[option.active_material] )
                        index = target.data.materials.find( option.active_material  )

                        for f in faces:
                            f.material_index = index

            bmesh.update_edit_mesh(target.data, destructive = True)
            bpy.ops.object.mode_set(mode='OBJECT')

        for o in selected:
            o.select_set(False)

    if addon.preference().property.workflow == 'DESTRUCTIVE':
        for cutter in cutters:
            bpy.data.objects.remove(cutter, do_unlink=True)

    elif addon.preference().property.workflow == 'NONDESTRUCTIVE':
        context.active_object.select_set(False) # Can't change active object due to edit mode switch unfortunately

        for cutter in cutters:
            cutter.hops.status = 'BOOLSHAPE'
            cutter.display_type = 'WIRE'
            cutter.hide_render = True
            cycles.hide_preview(context, cutter)
            collections.unlink_obj(context, cutter)
            collections.link_obj(context, cutter, "Cutters")

    return {'FINISHED'}

def to_mesh (obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)

    if obj.type == 'FONT':
        bm = bmesh.new()
        bm.from_mesh(eval_obj.to_mesh())
        eval_obj.to_mesh_clear()

        dist = 0.000001
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)

        # characters like T require 2 passes
        bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges)
        bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges)

        mesh = bpy.data.meshes.new('mesh')
        bm.to_mesh(mesh)

    else:
        mesh = bpy.data.meshes.new_from_object(eval_obj, preserve_all_data_layers=False, depsgraph = depsgraph)

    return mesh

def swap_cutter(context, obj):

    cutter_mesh = to_mesh(obj)
    cutter_mesh.name = obj.data.name+"_mesh"
    cutter_obj = bpy.data.objects.new(obj.name+"_mesh", cutter_mesh)
    col=collections.hops_col_get(context)
    col.objects.link(cutter_obj)
    obj.select_set(False)
    cutter_obj.select_set(True)

    for c in list(obj.users_collection):
        c.objects.unlink(obj)

    col.objects.link(obj)
    obj.hide_set(True)

    cutter_obj.matrix_world = obj.matrix_world

    decimate = cutter_obj.modifiers.new("Decimate",type='DECIMATE')
    decimate.decimate_type = 'DISSOLVE'

    return cutter_obj
