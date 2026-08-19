import bpy
from . import fix
from . import place
from . import transform
from . import transform_nsu
from . import run
from . import scroll
from . import set
from . import expand
from . import panel
from . import edit
from . import flip
from . import edit_mode
from . import add_gizmo
from . import remove_gizmo

classes = (
    fix.NSOLVE_OT_FixGizmo,
    place.NSOLVE_OT_PlaceGizmo,
    transform.NSOLVE_OT_TransformGizmo,
    transform_nsu.NSOLVE_OT_TransformNsuGizmo,
    flip.NSOLVE_OT_FlipGizmo,
    run.NSOLVE_OT_RunGizmo,
    set.NSOLVE_OT_SetGizmo,
    expand.NSOLVE_OT_ExpandGizmo,
    panel.NSOLVE_OT_CallPanel,
    edit.NSOLVE_OT_EditGizmo,
    edit_mode.NSOLVE_OT_ToggleEditMode,
    add_gizmo.NSOLVE_OT_AddGizmo,
    remove_gizmo.NSOLVE_OT_RemoveGizmo,
    scroll.NSOLVE_OT_ScrollGizmo,
)
