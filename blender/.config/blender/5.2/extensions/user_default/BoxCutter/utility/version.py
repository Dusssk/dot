import bpy
BMOD_SOLVERS = {itm.identifier for itm in bpy.types.BooleanModifier.bl_rna.properties['solver'].enum_items}

def bsolver_fast() -> str:
    '''Returns version compatible identifier for FAST boolean solver\n
    used by both Boolean modifier and edit mode ops\n
    FLOAT for 5+; FAST otherwise'''


    return 'FAST' if 'FAST' in BMOD_SOLVERS else 'FLOAT'
