uniform vec2 loc;
uniform vec2 size;
uniform vec2 border;

uniform vec4 color;
uniform vec4 edge;

out vec4 FragColor;


void main() {
    vec2 coord = gl_FragCoord.xy / gl_FragCoord.w;

    if (coord.x < loc.x || coord.x > loc.x + size.x || coord.y < loc.y || coord.y > loc.y + size.y) {
        discard;
    }

    float aa = 1;
    float edge_size = border.x;
    float radius = border.y;

    vec2 center = loc + size * 0.5;

    vec2 d = abs(coord - center) - ((size/2 - vec2(edge_size)) - vec2(radius - edge_size));
    float dist_inside = length(max(d, 0)) + min(max(d.x, d.y), 0) - (radius - edge_size);
    float alpha_inside = smoothstep(-aa, aa, -dist_inside);

    d = abs(coord - center) - (size/2 - vec2(radius));
    float dist_edge = length(max(d, 0)) + min(max(d.x, d.y), 0) - radius;
    float alpha_edge = smoothstep(-aa, aa, -dist_edge);

    alpha_edge = alpha_edge - alpha_inside;

    vec4 col = mix(edge, color, alpha_inside);

    float alpha = (alpha_inside * color.a) + (alpha_edge * edge.a);
    col.a *= alpha;

    FragColor = col;
}

