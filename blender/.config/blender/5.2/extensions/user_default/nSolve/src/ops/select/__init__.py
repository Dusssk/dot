import bpy
from . import planar_loop
from . import rounded
from . import similar_strip
from . import smart_loop


classes = (
    planar_loop.NSOLVE_OT_SelectPlanarLoop,
    planar_loop.NSOLVE_OT_SelectMultiPlanarLoop,
    rounded.NSOLVE_OT_SelectRoundedArea,
    similar_strip.NSOLVE_OT_SelectSimilarStrip,
    smart_loop.NSOLVE_OT_SelectSmartLoop,
    smart_loop.NSOLVE_OT_SelectMultiSmartLoop,
)