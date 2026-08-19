import bpy
import gpu
import os
import math
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector
from ....utils import addon


class NSOLVE_GT_ImageButton(bpy.types.Gizmo):
    bl_idname = "NSOLVE_GT_ImageButton"
    custom_shape = None
    neighbor_magnification = 1.0
    main_magnification = 1.3  # Default value, will be overridden by preference

    def generate_shape(self, shape_type='SQUARE'):
        if shape_type == 'SQUARE':
            return [
                (-0.5, -0.5), (0.5, -0.5), (0.5, 0.5),  # First triangle
                (-0.5, -0.5), (0.5, 0.5), (-0.5, 0.5),  # Second triangle
            ]

        elif shape_type == 'ROUNDED_SQUARE':
            corner_radius = 0.15  # Radius of rounded corners
            segments_per_corner = 3
            triangles = []

            # Define the inner rectangle points - shifted to be centered
            inner_rect = [
                (-0.5 + corner_radius, -0.5 + corner_radius),          # Bottom left
                (0.5 - corner_radius, -0.5 + corner_radius),      # Bottom right
                (0.5 - corner_radius, 0.5 - corner_radius),  # Top right
                (-0.5 + corner_radius, 0.5 - corner_radius),      # Top left
            ]

            # Add the inner rectangle triangles
            triangles.extend([
                inner_rect[0], inner_rect[1], inner_rect[2],  # First triangle
                inner_rect[0], inner_rect[2], inner_rect[3],  # Second triangle
            ])

            # Generate rounded corners - shifted to be centered
            corners = [
                (-0.5 + corner_radius, -0.5 + corner_radius, math.pi, 1.5*math.pi),         # Bottom left
                (0.5 - corner_radius, -0.5 + corner_radius, 1.5*math.pi, 2*math.pi),   # Bottom right
                (0.5 - corner_radius, 0.5 - corner_radius, 0, 0.5*math.pi),       # Top right
                (-0.5 + corner_radius, 0.5 - corner_radius, 0.5*math.pi, math.pi),     # Top left
            ]

            # Add corners
            for cx, cy, start_angle, end_angle in corners:
                # Generate corner vertices
                corner_verts = []
                for i in range(segments_per_corner + 1):
                    t = i / segments_per_corner
                    angle = start_angle + (end_angle - start_angle) * t
                    x = cx + corner_radius * math.cos(angle)
                    y = cy + corner_radius * math.sin(angle)
                    corner_verts.append((x, y))

                # Create triangles for this corner
                for i in range(len(corner_verts) - 1):
                    triangles.extend([
                        (cx, cy),  # Corner center
                        corner_verts[i],
                        corner_verts[i + 1]
                    ])

            # Add connecting rectangles between corners - shifted to be centered
            # Bottom
            triangles.extend([
                inner_rect[0], (-0.5 + corner_radius, -0.5), inner_rect[1],  # First triangle
                inner_rect[1], (-0.5 + corner_radius, -0.5), (0.5 - corner_radius, -0.5)  # Second triangle
            ])
            # Right
            triangles.extend([
                inner_rect[1], (0.5, -0.5 + corner_radius), inner_rect[2],  # First triangle
                inner_rect[2], (0.5, -0.5 + corner_radius), (0.5, 0.5 - corner_radius)  # Second triangle
            ])
            # Top
            triangles.extend([
                inner_rect[2], (0.5 - corner_radius, 0.5), inner_rect[3],  # First triangle
                inner_rect[3], (0.5 - corner_radius, 0.5), (-0.5 + corner_radius, 0.5)  # Second triangle
            ])
            # Left
            triangles.extend([
                inner_rect[3], (-0.5, 0.5 - corner_radius), inner_rect[0],  # First triangle
                inner_rect[0], (-0.5, 0.5 - corner_radius), (-0.5, -0.5 + corner_radius)  # Second triangle
            ])

            return triangles

        elif shape_type == 'CIRCLE':
            verts = []
            segments = 32
            radius = 0.5

            # Add center vertex
            verts.append((0, 0))

            # Generate circle vertices
            for i in range(segments):
                angle = 2 * math.pi * (i / segments)
                x = math.cos(angle) * radius
                y = math.sin(angle) * radius
                verts.append((x, y))

            # Create triangles
            triangles = []
            for i in range(segments):
                next_i = (i + 1) % segments + 1  # +1 because first vert is center
                triangles.extend([verts[0], verts[i + 1], verts[next_i]])

            return triangles

        return None

    def setup_image(self, image_path, shape_type='SQUARE'):
        if not os.path.exists(image_path):
            return False

        try:
            # Load or get existing image
            image_name = os.path.basename(image_path)
            if image_name in bpy.data.images:
                image = bpy.data.images[image_name]
            else:
                image = bpy.data.images.load(image_path)

            # Create shader for image
            self.shader = gpu.shader.from_builtin('IMAGE')
            self.texture = gpu.texture.from_image(image)

            # Get shape vertices
            shape = self.generate_shape(shape_type)
            if not shape:
                return False

            # Convert shape vertices to 3D and create UVs
            vertices = []
            uvs = []
            for i in range(0, len(shape), 3):
                # Process each triangle
                for j in range(3):
                    v = shape[i + j]
                    vertices.append((v[0], v[1], 0))  # Added Z coordinate
                    uvs.append((v[0] + 0.5, v[1] + 0.5))  # UVs stay in [0,1] range

            # Create batches for both image and highlight
            self.batch = batch_for_shader(
                self.shader, 'TRIS',
                {
                    "pos": vertices,
                    "texCoord": uvs,
                }
            )

            # Create highlight batch
            self.highlight_batch = batch_for_shader(
                gpu.shader.from_builtin('UNIFORM_COLOR'), 'TRIS',
                {
                    "pos": vertices,
                }
            )

            return True

        except Exception as e:
            print(f"Error loading image: {e}")
            return False

    def build(self, shape_type='SQUARE'):
        shape = self.generate_shape(shape_type)
        if shape:
            # Convert shape vertices to 3D by adding Z coordinate
            vertices = [(v[0], v[1], 0.0) for v in shape]
            
            # Create batch for non-textured shape
            self.batch = batch_for_shader(
                gpu.shader.from_builtin('UNIFORM_COLOR'), 'TRIS',
                {
                    "pos": vertices,
                }
            )
            
            # Create highlight batch
            self.highlight_batch = batch_for_shader(
                gpu.shader.from_builtin('UNIFORM_COLOR'), 'TRIS',
                {
                    "pos": vertices,
                }
            )
            
            # Also create custom shape for fallback
            self.custom_shape = self.new_custom_shape('TRIS', vertices)

    def draw(self, context):
        gpu.state.blend_set('ALPHA')
        gpu.matrix.push()
        
        # Determine which magnification to apply
        magnification = 1.0
        
        if self.is_highlight:
            # Use the main magnification value from preferences for highlighted buttons
            # This should always take precedence
            magnification = self.main_magnification if hasattr(self, 'main_magnification') else 2.0
        elif hasattr(self, 'neighbor_magnification') and self.neighbor_magnification > 1.0:
            # Use neighbor magnification for neighboring buttons
            magnification = self.neighbor_magnification
        
        # Apply magnification if needed
        if magnification != 1.0:
            # Create a magnification matrix
            scale_matrix = Matrix.Scale(magnification, 4)
            
            # Apply the magnification to the matrix
            magnified_matrix = self.matrix_basis.copy()
            magnified_matrix @= scale_matrix
            
            # Apply the magnified matrix
            gpu.matrix.multiply_matrix(magnified_matrix)
        else:
            # Use the original matrix if no magnification
            gpu.matrix.multiply_matrix(self.matrix_basis)
        
        # Always draw the shape first
        color_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        color_shader.bind()
        color_shader.uniform_float("color", (*self.color, self.alpha))
        self.batch.draw(color_shader)
        
        # Draw texture on top if available
        if hasattr(self, 'shader') and hasattr(self, 'texture'):
            self.shader.bind()
            self.shader.uniform_sampler("image", self.texture)
            self.batch.draw(self.shader)

        # Draw highlight if mouse is over
        if self.is_highlight and hasattr(self, 'highlight_batch'):
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            shader.bind()
            shader.uniform_float("color", (*self.color_highlight, self.alpha_highlight))
            self.highlight_batch.draw(shader)

        gpu.matrix.pop()
        gpu.state.blend_set('NONE')

    def test_select(self, context, location):
        # Get the location from matrix_basis
        translation = self.matrix_basis.to_translation()
        scale = self.matrix_basis.to_scale()
        
        # Determine the effective scale based on magnification
        effective_scale = scale.copy()
        
        # Apply magnification to the effective scale for hit testing
        # This ensures that the hit area matches the visual size
        if self.is_highlight:
            # For highlighted buttons - use main magnification
            effective_scale *= self.main_magnification if hasattr(self, 'main_magnification') else 2.0
        elif hasattr(self, 'neighbor_magnification') and self.neighbor_magnification > 1.0:
            # For neighboring buttons - use neighbor magnification
            effective_scale *= self.neighbor_magnification

        # Check if location is inside the button bounds with the effective scale
        if (translation.x - effective_scale.x/2 < location[0] < translation.x + effective_scale.x/2 and 
            translation.y - effective_scale.y/2 < location[1] < translation.y + effective_scale.y/2):
            return 0
        return -1

    def setup_image(self, image_path, shape_type='SQUARE'):
        if not os.path.exists(image_path):
            return False

        try:
            # Load or get existing image
            image_name = os.path.basename(image_path)
            if image_name in bpy.data.images:
                image = bpy.data.images[image_name]
            else:
                image = bpy.data.images.load(image_path)

            # Create shader for image
            self.shader = gpu.shader.from_builtin('IMAGE')
            self.texture = gpu.texture.from_image(image)

            # Get shape vertices
            shape = self.generate_shape(shape_type)
            if not shape:
                return False

            # Convert shape vertices to 3D and create UVs
            vertices = []
            uvs = []
            for i in range(0, len(shape), 3):
                # Process each triangle
                for j in range(3):
                    v = shape[i + j]
                    vertices.append((v[0], v[1], 0))  # Added Z coordinate
                    uvs.append((v[0] + 0.5, v[1] + 0.5))  # UVs stay in [0,1] range

            # Create batches for both image and highlight
            self.batch = batch_for_shader(
                self.shader, 'TRIS',
                {
                    "pos": vertices,
                    "texCoord": uvs,
                }
            )

            # Create highlight batch
            self.highlight_batch = batch_for_shader(
                gpu.shader.from_builtin('UNIFORM_COLOR'), 'TRIS',
                {
                    "pos": vertices,
                }
            )

            return True

        except Exception as e:
            print(f"Error loading image: {e}")
            return False

    def build(self, shape_type='SQUARE'):
        shape = self.generate_shape(shape_type)
        if shape:
            # Convert shape vertices to 3D by adding Z coordinate
            vertices = [(v[0], v[1], 0.0) for v in shape]
            
            # Create batch for non-textured shape
            self.batch = batch_for_shader(
                gpu.shader.from_builtin('UNIFORM_COLOR'), 'TRIS',
                {
                    "pos": vertices,
                }
            )
            
            # Create highlight batch
            self.highlight_batch = batch_for_shader(
                gpu.shader.from_builtin('UNIFORM_COLOR'), 'TRIS',
                {
                    "pos": vertices,
                }
            )
            
            # Also create custom shape for fallback
            self.custom_shape = self.new_custom_shape('TRIS', vertices)

class Draw:
    def __init__(self, gm, location, size, image_path=None, pushed=False):
        self.location = location
        self.size = size
        self.gizmo = self.create(gm, location, size, image_path, pushed)

    def create(self, gm, location, size, image_path, pushed):
        translation_matrix = Matrix.Translation((location.x, location.y, 0))
        scale_matrix = Matrix.Scale(size.x, 4, Vector((1, 0, 0))) @ Matrix.Scale(size.y, 4, Vector((0, 1, 0)))

        gz = gm.gizmos.new(NSOLVE_GT_ImageButton.bl_idname)

        nsolve = addon.pref().tools.nsolve
        shape_type = nsolve.main_gizmo_shape

        gz.build(shape_type)
        gz.location = location
        gz.size = size

        if image_path:
            # Handle case where image_path is a list
            if isinstance(image_path, (list, tuple)):
                image_path = "_".join(str(x) for x in image_path)
            full_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "icons", "buttons", image_path)
            gz.setup_image(full_path, shape_type)

        if pushed:
            gz.color = addon.pref().tools.nsolve.gizmo_col.selected[:-1]
            gz.alpha = addon.pref().tools.nsolve.gizmo_col.selected[-1]
        else:
            gz.color = addon.pref().tools.nsolve.gizmo_col.inner[:-1]
            gz.alpha = addon.pref().tools.nsolve.gizmo_col.inner[-1]

        gz.color_highlight = (1.0, 1.0, 1.0)
        gz.alpha_highlight = 0.3
        gz.use_event_handle_all = True
        gz.use_draw_modal = True
        gz.scale_basis = 1
        gz.matrix_basis = translation_matrix @ scale_matrix

        return gz

    def is_modal(self):
        return self.gizmo.is_modal

    def hide(self, set=False):
        if set:
            self.gizmo.hide = True
        else:
            self.gizmo.hide = False

    def operator(self, operator, properties=None):
        try:
            op_props = self.gizmo.target_set_operator(operator)
        except Exception as e:
            print(f"Error setting operator '{operator}': {e}")
            return
        if properties:
            for prop, value in properties.items():
                try:
                    setattr(op_props, prop, value)
                except Exception as e:
                    print(f"Error setting property '{prop}' to '{value}' for operator '{operator}': {e}")

    def update(self, matrix_basis):
        self.gizmo.matrix_basis = matrix_basis
