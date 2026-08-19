import bpy


class HOPS_OT_Bloom_Toggle(bpy.types.Operator):
    bl_idname = "hops.bloom_toggle"
    bl_label = "Toggle Compositor Bloom in Viewvport"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = """Toggle Bloom in current compsitor node tree"""

    threshold: bpy.props.FloatProperty(
        name = "Threshold",
        description = 'Bloom Threshold',
        min = 0.0,
        default = 0.2)

    @classmethod
    def poll(cls, context):
        return bpy.app.version >= (4, 0, 0)

    def draw(self, context):
        if not self.bloom_node: return
        self.layout.prop(self, 'threshold')


    def execute(self, context):
        scene = context.scene
        context.space_data.shading.use_compositor = 'ALWAYS'
        self.bloom_node = ''


        composite = None
        render_layer = None
        viewers = []
        out_name= ''

        if bpy.app.version[0] < 5:
            scene.use_nodes = True
            node_tree = scene.node_tree
            out_name = 'CompositorNodeComposite'
        else:
            node_tree = scene.compositing_node_group
            if not node_tree:
                node_tree = scene.compositing_node_group = bpy.data.node_groups.new('Bloom', 'CompositorNodeTree')
            out_name = 'NodeGroupOutput'


        for node in node_tree.nodes:
            if node.type in {"COMPOSITE", "GROUP_OUTPUT"} and not composite:
                if node.inputs[0].is_linked:
                    composite = node

            if node.type == 'VIEWER':
                viewers.append(node)

        for node in viewers:
            node_tree.nodes.remove(node)

        # if there is not composite node assume whole tree is invalid and make basic one
        if not composite:
            composite = node_tree.nodes.new(out_name)

        # in 5.0 there can be multiple, but not using 1st is cringe
        if not composite.inputs[0].is_linked:
            render_layer = node_tree.nodes.new("CompositorNodeRLayers")
            composite.location.x = render_layer.width * 2

            # in 5.X empty output has no color socket
            if bpy.app.version[0] > 4:
                node_tree.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')

            input = composite.inputs[0]
            output = render_layer.outputs[0]
            node_tree.links.new(input, output)

        comp_input = composite.inputs[0]
        if comp_input.is_linked:
            from_socket = comp_input.links[0].from_socket
            to_socket = comp_input.links[0].to_socket
            link = comp_input.links[0]
            input_node = comp_input.links[0].from_node

            # it's not glare bloom inject it
            if input_node.type != 'GLARE' or glare_type(input_node) !='BLOOM':
                glare = node_tree.nodes.new("CompositorNodeGlare")
                if bpy.app.version[0] < 5:
                    glare.glare_type = 'BLOOM'
                    if 'Threshold' in glare.inputs:
                        glare.inputs['Threshold'].default_value = self.threshold
                    else:
                        glare.threshold = self.threshold

                else:
                    glare.inputs['Type'].default_value = 'Bloom'
                    glare.inputs['Threshold'].default_value = self.threshold


                node_tree.links.remove(link)
                node_tree.links.new(glare.inputs[0], from_socket)
                node_tree.links.new(glare.outputs[0], to_socket)

                from_node = from_socket.node
                to_node = to_socket.node
                glare.location.x = from_node.location.x + from_node.width + 100
                to_node.location.x = glare.location.x + glare.width + 100
                self.bloom_node = glare.name

            # otherwise toggle node
            else:
                input_node.mute = not input_node.mute

                if not input_node.mute:
                    self.bloom_node = input_node.name
                    if 'Threshold' in input_node.inputs:
                        input_node.inputs['Threshold'].default_value = self.threshold
                    else:
                        input_node.threshold = self.threshold

        return {"FINISHED"}


def glare_type(node)-> str:
    '''Assume node is GLARE type'''
    if bpy.app.version[0] < 5:
        return node.glare_type

    # assume it's not linked
    val: str = node.inputs[1].default_value
    return val.capitalize()
