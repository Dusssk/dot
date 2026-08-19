import bpy

from . import project
from . import analyze
from . import bevel
from . import collapse_verts
from . import cut
from . import dissolve
from . import hard_edge_slide
from . import hard_loop_cut
from . import join_verts
from . import merge_verts
from . import offset_edges
from . import slide_vert
from . import unbevel
from . import set_tool
from . import hide


class types():
    class theme(bpy.types.PropertyGroup):
        project: bpy.props.PointerProperty(type=project.types.theme)
        analyze: bpy.props.PointerProperty(type=analyze.types.theme)
        bevel: bpy.props.PointerProperty(type=bevel.types.theme)
        collapse_verts: bpy.props.PointerProperty(type=collapse_verts.types.theme)
        cut: bpy.props.PointerProperty(type=cut.types.theme)
        dissolve: bpy.props.PointerProperty(type=dissolve.types.theme)
        hard_edge_slide: bpy.props.PointerProperty(type=hard_edge_slide.types.theme)
        hard_loop_cut: bpy.props.PointerProperty(type=hard_loop_cut.types.theme)
        join_verts: bpy.props.PointerProperty(type=join_verts.types.theme)
        merge_verts: bpy.props.PointerProperty(type=merge_verts.types.theme)
        offset_edges: bpy.props.PointerProperty(type=offset_edges.types.theme)
        hide: bpy.props.PointerProperty(type=hide.types.theme)

    class scene(bpy.types.PropertyGroup):
        analyze: bpy.props.PointerProperty(type=analyze.types.scene)

    class pref(bpy.types.PropertyGroup):
        analyze: bpy.props.PointerProperty(type=analyze.types.pref)


types_classes = (
    *project.types_classes,
    *analyze.types_classes,
    *bevel.types_classes,
    *collapse_verts.types_classes,
    *cut.types_classes,
    *dissolve.types_classes,
    *hard_edge_slide.types_classes,
    *hard_loop_cut.types_classes,
    *join_verts.types_classes,
    *merge_verts.types_classes,
    *offset_edges.types_classes,
    *hide.types_classes,
    types.theme,
    types.scene,
    types.pref,
)

classes = (
    *project.classes,
    analyze.NSOLVE_OT_Analyze,
    bevel.NSOLVE_OT_Bevel,
    collapse_verts.NSOLVE_OT_CollapseVerts,
    cut.NSOLVE_OT_MeshCut,
    dissolve.NSOLVE_OT_Dissolve_Edges,
    hard_edge_slide.NSOLVE_OT_HardEdgeSlide,
    hard_loop_cut.NSOLVE_OT_HardLoopCut,
    join_verts.NSOLVE_OT_JoinVerts,
    merge_verts.NSOLVE_OT_MergeVerts,
    offset_edges.NSOLVE_OT_Offset_Edges,
    slide_vert.NSOLVE_OT_SlideVert,
    unbevel.NSOLVE_OT_Unbevel,
    set_tool.NSOLVE_OT_SetTool,
    hide.NSOLVE_OT_Hide,
)