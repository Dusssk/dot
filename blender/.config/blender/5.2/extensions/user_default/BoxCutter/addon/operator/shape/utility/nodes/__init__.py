from . array import Array
from . generate import Generate
from . deform import Deform
from . clean import Clean
from . import deform_modal


from ......utility.geometry_nodes import SmoothByAngle

def mod_type(mod):
    if mod.type != 'NODES': return mod.type

    if Array.is_valid_modifier(mod): return 'ARRAY'
    if Generate.is_valid_modifier(mod): return 'GENERATE'
    if Deform.is_valid_modifier(mod): return 'DEFORM'
    if Clean.is_valid_modifier(mod): return 'CLEAN'
    if SmoothByAngle.is_valid_modifier(mod): return 'AUTOSMOOTH'

    return 'NODES'