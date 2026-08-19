import bpy, mathutils, math, bmesh
from math import radians

DESC = """Clean Edges
Dissolve verts between collinear edges
"""


class HOPS_OT_Clean_Edge(bpy.types.Operator):
    bl_idname = "hops.clean_edge"
    bl_label = "Clean Edges"
    bl_description = DESC
    bl_options = {"REGISTER", "UNDO"}

    threshold: bpy.props.FloatProperty(
        name = 'Angle Threshold',
        description = '\n Edge angle above which the vertex is dissolved',
        subtype = 'ANGLE',
        unit = 'ROTATION',
        default = radians(179),
        min=0,
        max=radians(180),
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):

        count = 0
        for obj in context.selected_editable_objects:
            obj.update_from_editmode()
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)

            dissolve_verts = []

            for vert in bm.verts:
                if len(vert.link_edges) != 2: continue
                e1 = vert.link_edges[0]
                e2 = vert.link_edges[1]
                vec1 = e1.other_vert(vert).co - vert.co
                vec2 = e2.other_vert(vert).co - vert.co

                if vec1.angle(vec2) > self.threshold:
                    dissolve_verts.append(vert)

            if dissolve_verts:
                count += len(dissolve_verts)
                bmesh.ops.dissolve_verts(bm, verts=dissolve_verts)
                bmesh.update_edit_mesh(mesh)

            self.report({'INFO'}, f'{count} Vertices dissolved')
        return {'FINISHED'}


