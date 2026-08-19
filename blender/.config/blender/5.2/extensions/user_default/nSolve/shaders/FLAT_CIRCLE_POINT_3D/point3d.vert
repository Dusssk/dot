void main() {
    vec4 pos_4d = vec4(pos, 1.0);
    gl_Position = ViewProjectionMatrix * pos_4d;
    gl_PointSize = size;

    float r = size * 0.5;
    radius[0] = r; // radius
    radius[1] = r - 1; // feathering

    radius /= size; // normalized point corrdinates

    fColor = color;
}