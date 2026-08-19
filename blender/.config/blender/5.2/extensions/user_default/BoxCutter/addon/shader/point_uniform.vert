uniform mat4 ModelViewProjectionMatrix;

uniform float size;

in vec3 pos;


void main() {
    gl_Position = ModelViewProjectionMatrix  * vec4(pos, 1.0);
    gl_PointSize = size;
}
