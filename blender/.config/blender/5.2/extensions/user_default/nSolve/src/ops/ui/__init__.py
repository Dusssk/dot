from . import text
from . import header
from . import operator_list
from . import gizmo_operators
from . import set_tool_operators

classes = (
    text.NSOLVE_OT_InterfaceText,
    *header.classes,
    *operator_list.classes,
    *gizmo_operators.classes,
    *set_tool_operators.classes,
)
