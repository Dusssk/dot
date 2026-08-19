import os
import gpu


def compile():
    shader_info = gpu.types.GPUShaderCreateInfo()

    shader_info.push_constant('MAT4', 'ViewProjectionMatrix')
    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_in(2, 'FLOAT', 'size')

    v_out = gpu.types.GPUStageInterfaceInfo('v_out')
    v_out.flat('VEC4', 'fColor')
    v_out.flat('VEC2', 'radius')

    shader_info.fragment_out(0, 'VEC4', 'fragColor')
    shader_info.vertex_out(v_out)

    current_script_directory = os.path.dirname(os.path.realpath(__file__))

    vertex_shader_path = os.path.join(current_script_directory, "point3d.vert")
    fragment_shader_path = os.path.join(current_script_directory, "point3d.frag")

    with open(vertex_shader_path, "r", encoding="utf-8") as f:
        vertex_shader_source = f.read()

    with open(fragment_shader_path, "r", encoding="utf-8") as f:
        fragment_shader_source = f.read()

    shader_info.vertex_source(vertex_shader_source)
    shader_info.fragment_source(fragment_shader_source)

    return gpu.shader.create_from_info(shader_info)
