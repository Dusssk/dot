import bpy
import gpu
import os
import math
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector
from ....utils import addon


class NSOLVE_GT_ImageTextButton(bpy.types.Gizmo):
    bl_idname = "NSOLVE_GT_ImageTextButton"
    custom_shape = None
    neighbor_magnification = 1.0
    main_magnification = 1.3  # Default value, will be overridden by preference

    def generate_shape(self, shape_type):
        """Generate vertices and indices for the specified shape type."""
        # Always create a square shape
        width = 1.0
        height = 1.0
        
        # Create square vertices
        vertices = [
            (-width/2, -height/2, 0),
            (width/2, -height/2, 0),
            (width/2, height/2, 0),
            (-width/2, -height/2, 0),
            (width/2, height/2, 0),
            (-width/2, height/2, 0)
        ]
        
        # No need for indices with direct vertices
        indices = []
        
        return vertices, indices

    def setup_image(self, image_path, text_image_path=None, shape_type='SQUARE'):
        # Load the main image texture if provided
        if image_path and os.path.exists(image_path):
            try:
                # Load the image
                image_name = os.path.basename(image_path)
                if image_name in bpy.data.images:
                    image = bpy.data.images[image_name]
                else:
                    image = bpy.data.images.load(image_path)
                
                # Create the texture
                self.texture = gpu.texture.from_image(image)
                
                # Create the shader
                self.shader = gpu.shader.from_builtin('IMAGE')
            except Exception as e:
                print(f"Error loading image: {e}")
        
        # Load the text image texture if provided
        if text_image_path and os.path.exists(text_image_path):
            try:
                # Load the text image
                text_image_name = os.path.basename(text_image_path)
                if text_image_name in bpy.data.images:
                    text_image = bpy.data.images[text_image_name]
                else:
                    text_image = bpy.data.images.load(text_image_path)
                
                # Store aspect ratio for later use
                self.text_aspect_ratio = text_image.size[0] / text_image.size[1]
                print(f"Text image loaded with aspect ratio: {self.text_aspect_ratio}")
                
                # Create the texture
                self.text_texture = gpu.texture.from_image(text_image)
                
                # Create the shader
                self.text_shader = gpu.shader.from_builtin('IMAGE')
                
                # Set the flag to indicate this button has text
                self.has_text = True
            except Exception as e:
                print(f"Error loading text image: {e}")

    def build(self, shape_type):
        """Build the gizmo with the specified shape."""
        # For text buttons, we always use a square shape
        shape_type = 'SQUARE'
        
        # Generate the shape vertices and indices
        vertices, indices = self.generate_shape(shape_type)
        
        # Default UV coordinates for a square
        uvs = [
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 0),
            (1, 1),
            (0, 1)
        ]
        
        # Create the batch for drawing
        self.batch = batch_for_shader(
            gpu.shader.from_builtin('IMAGE'), 'TRIS',
            {
                "pos": vertices,
                "texCoord": uvs,
            }
        )

    def draw(self, context):
        gpu.state.blend_set('ALPHA')
        gpu.matrix.push()
        
        # Apply the matrix
        gpu.matrix.multiply_matrix(self.matrix_basis)
        
        # Draw text image if available
        if hasattr(self, 'has_text') and self.has_text and hasattr(self, 'text_shader') and hasattr(self, 'text_texture'):
            # Create a proper rectangle for the text that respects the aspect ratio
            # Use the text_aspect_ratio to determine the dimensions
            if hasattr(self, 'text_aspect_ratio') and self.text_aspect_ratio:
                aspect_ratio = self.text_aspect_ratio
                
                # Calculate rectangle dimensions to maintain aspect ratio
                # The rectangle will fit within the 1.0 x 1.0 square but maintain the proper aspect ratio
                rect_width = 1.0
                rect_height = 1.0
                
                if aspect_ratio > 1.0:  # Wider than tall
                    # Use full width, adjust height
                    rect_height = 1.0 / aspect_ratio
                elif aspect_ratio < 1.0:  # Taller than wide
                    # Use full height, adjust width
                    rect_width = aspect_ratio
                
                # Calculate offsets to center the rectangle
                x_offset = (1.0 - rect_width) / 2.0
                y_offset = (1.0 - rect_height) / 2.0
                
                # Create vertices for the properly sized rectangle
                vertices = [
                    (-0.5 + x_offset, -0.5 + y_offset, 0),                    # Bottom left
                    (-0.5 + x_offset + rect_width, -0.5 + y_offset, 0),       # Bottom right
                    (-0.5 + x_offset + rect_width, -0.5 + y_offset + rect_height, 0),  # Top right
                    
                    (-0.5 + x_offset, -0.5 + y_offset, 0),                    # Bottom left
                    (-0.5 + x_offset + rect_width, -0.5 + y_offset + rect_height, 0),  # Top right
                    (-0.5 + x_offset, -0.5 + y_offset + rect_height, 0)       # Top left
                ]
                
                # Create UVs that map the entire texture to our rectangle (without stretching)
                uvs = [
                    (0.0, 0.0),  # Bottom left
                    (1.0, 0.0),  # Bottom right
                    (1.0, 1.0),  # Top right
                    
                    (0.0, 0.0),  # Bottom left 
                    (1.0, 1.0),  # Top right
                    (0.0, 1.0)   # Top left
                ]
                
                # Create a batch for the text image
                text_batch = batch_for_shader(
                    self.text_shader, 'TRIS',
                    {
                        "pos": vertices,
                        "texCoord": uvs,
                    }
                )
                
                # Draw the text image
                self.text_shader.bind()
                self.text_shader.uniform_sampler("image", self.text_texture)
                text_batch.draw(self.text_shader)
            else:
                # Fallback if aspect ratio is not available - use the original code
                width = 1.0
                height = 1.0
                
                vertices = [
                    (-width/2, -height/2, 0),
                    (width/2, -height/2, 0),
                    (width/2, height/2, 0),
                    (-width/2, -height/2, 0),
                    (width/2, height/2, 0),
                    (-width/2, height/2, 0)
                ]
                
                uvs = [
                    (0.0, 0.0),
                    (1.0, 0.0),
                    (1.0, 1.0),
                    (0.0, 0.0),
                    (1.0, 1.0),
                    (0.0, 1.0)
                ]
                
                # Create a batch for the text image
                text_batch = batch_for_shader(
                    self.text_shader, 'TRIS',
                    {
                        "pos": vertices,
                        "texCoord": uvs,
                    }
                )
                
                # Draw the text image
                self.text_shader.bind()
                self.text_shader.uniform_sampler("image", self.text_texture)
                text_batch.draw(self.text_shader)

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

        # Adjust for aspect ratio if this is a text button
        width_scale = effective_scale.x
        height_scale = effective_scale.y
        
        # Check if location is inside the button bounds with the effective scale
        if (translation.x - width_scale/2 < location[0] < translation.x + width_scale/2 and 
            translation.y - height_scale/2 < location[1] < translation.y + height_scale/2):
            return 0
        return -1


class DrawTextButton:
    def __init__(self, gm, location, size, image_path=None, text_image_path=None, pushed=False):
        self.location = location
        self.size = size
        self.gizmo = self.create(gm, location, size, image_path, text_image_path, pushed)

    def create(self, gm, location, size, image_path, text_image_path, pushed):
        translation_matrix = Matrix.Translation((location.x, location.y, 0))
        
        # Create a new gizmo
        gz = gm.gizmos.new(NSOLVE_GT_ImageTextButton.bl_idname)
        gz.hide_select = True

        # For text buttons, we'll use a square shape
        shape_type = 'SQUARE'
        
        # Handle text image path first to get aspect ratio
        text_aspect_ratio = None
        text_full_path = None
        
        if text_image_path:
            # Handle text image path
            if isinstance(text_image_path, (list, tuple)):
                text_image_path = "_".join(str(x) for x in text_image_path)
            
            # Get the full path to the text image in the icons/text folder
            text_full_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "icons", "text", text_image_path)
            
            # Make sure to add .png extension if not already present
            if not text_full_path.lower().endswith('.png'):
                text_full_path += '.png'
            
            print(f"Looking for text image at: {text_full_path}")
            
            # Load text image to get dimensions for aspect ratio
            if os.path.exists(text_full_path):
                try:
                    # Load text image
                    text_image_name = os.path.basename(text_full_path)
                    if text_image_name in bpy.data.images:
                        text_image = bpy.data.images[text_image_name]
                    else:
                        text_image = bpy.data.images.load(text_full_path)
                    
                    # Calculate aspect ratio
                    text_aspect_ratio = text_image.size[0] / text_image.size[1]
                    
                    # Store aspect ratio in gizmo for later use
                    gz.text_aspect_ratio = text_aspect_ratio
                    
                    print(f"Text image loaded successfully with aspect ratio: {text_aspect_ratio}")
                except Exception as e:
                    print(f"Error loading text image for size calculation: {e}")
            else:
                print(f"Text image not found at: {text_full_path}")
        
        # Setup the gizmo
        gz.build(shape_type)
        gz.location = location
        gz.size = size
        
        # Create scale matrix that preserves the aspect ratio
        scale_matrix = Matrix.Scale(size.x, 4, Vector((1, 0, 0))) @ Matrix.Scale(size.y, 4, Vector((0, 1, 0)))

        # Handle image paths
        if image_path:
            # Handle case where image_path is a list
            if isinstance(image_path, (list, tuple)):
                image_path = "_".join(str(x) for x in image_path)
            full_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "icons", "buttons", image_path)
            
            # Setup the image with the text image
            gz.setup_image(full_path, text_full_path, shape_type)
        
        # Set basic properties
        gz.use_event_handle_all = True
        gz.use_draw_modal = True
        gz.scale_basis = 1
        gz.matrix_basis = translation_matrix @ scale_matrix
        
        # Set flag to indicate this is a text button
        gz.is_text_button = True

        return gz

    def hide(self, set=False):
        if set:
            self.gizmo.hide = True
        else:
            self.gizmo.hide = False

    def update(self, matrix_basis):
        self.gizmo.matrix_basis = matrix_basis


classes = (
    NSOLVE_GT_ImageTextButton,
)
