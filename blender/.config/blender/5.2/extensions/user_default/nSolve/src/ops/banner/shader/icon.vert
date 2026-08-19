//uniform mat4 projection;
in vec2 pos;
in vec2 coord;

out vec2 uv;


void main() {
    uv = coord;
    gl_Position = vec4(pos*2-1, 0.0f, 1.0f);
}
