from . import edge
from . import face
from . import files
from . import menu
from . import nso
from . import object_menu
from . import personas
from . import project
from . import select
from . import vert
from . import helper
from . import gizmo_pie


classes = (
    nso.NSOLVE_MT_NsoMenu,
    edge.NSOLVE_MT_EdgeMenu,
    face.NSOLVE_MT_FaceMenu,
    files.NSOLVE_MT_FilesMenu,
    menu.NSOLVE_MT_MainMenu,
    object_menu.NSOLVE_MT_ObjectMenu,
    personas.NSOLVE_MT_PersonasMenu,
    project.NSOLVE_MT_ProjectMenu,
    select.NSOLVE_MT_SelectMenu,
    vert.NSOLVE_MT_VertMenu,
    helper.NSOLVE_OT_RefreshFolders,
    helper.NSOLVE_OT_Helper,
    gizmo_pie.NSOLVE_MT_GizmoPie,
)
