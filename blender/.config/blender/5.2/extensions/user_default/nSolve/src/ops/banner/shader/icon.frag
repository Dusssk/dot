uniform sampler2D icon;
uniform vec2 loc;
uniform vec2 size;
uniform float alpha;

in vec2 uv;

out vec4 FragColor;

void main() {
    vec2 coord = gl_FragCoord.xy / gl_FragCoord.w;

    if (coord.x < loc.x || coord.x > loc.x + size.x || coord.y < loc.y || coord.y > loc.y + size.y) {
        discard;
    }

    vec4 col = texture(icon, uv);

    col.a *= alpha;
    FragColor = col;
}

