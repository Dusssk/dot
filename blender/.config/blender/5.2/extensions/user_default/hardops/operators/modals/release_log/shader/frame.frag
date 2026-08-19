uniform vec2 loc;
uniform vec2 size;

uniform float smoothing;

uniform vec4 color;

uniform vec4 border;
uniform float border_size;

uniform vec4 corner_radius;   // tl, tr, br, bl
uniform vec4 corner_chamfer;  // 0 = round, 1 = chamfer

uniform vec4 clipping; // l, t, r, b

out vec4 FragColor;

void main() {
    vec2 coord = gl_FragCoord.xy / gl_FragCoord.w;

    if (coord.x < loc.x || coord.x > loc.x + size.x ||
        coord.y < loc.y || coord.y > loc.y + size.y) {
        discard;
    }

    float radius  = corner_radius.x;
    float chamfer = corner_chamfer.x;

    bool left   = coord.x <= loc.x + size.x * 0.5;
    bool bottom = coord.y <= loc.y + size.y * 0.5;

    if (left) {
        if (bottom) {
            radius  = corner_radius.w;
            chamfer = corner_chamfer.w;
        }
    } else {
        if (bottom) {
            radius  = corner_radius.z;
            chamfer = corner_chamfer.z;
        } else {
            radius  = corner_radius.y;
            chamfer = corner_chamfer.y;
        }
    }

    vec2 _loc = loc;
    _loc.x -= clipping.x;
    _loc.y -= clipping.w;

    vec2 _size = size;
    _size.x += clipping.z;
    _size.y += clipping.y;

    vec2 center = _loc + _size * 0.5;

    vec2 df_in         = abs(coord - center) -
                         ((_size * 0.5 - vec2(border_size + smoothing * 0.5)) -
                         vec2(radius - border_size));
    float in_round     = length(max(df_in, 0.0)) +
                         min(max(df_in.x, df_in.y), 0.0) -
                         (radius - border_size);
    float in_chamfer   = max(df_in.x + df_in.y, max(df_in.x, df_in.y)) -
                         (radius - border_size);
    float inside       = mix(in_round, in_chamfer, chamfer);
    float alpha_inside = smoothstep(-smoothing, smoothing, -inside);

    vec2 df_out       = abs(coord - center) -
                        (_size * 0.5 - vec2(radius));
    float out_round   = length(max(df_out, 0.0)) +
                        min(max(df_out.x, df_out.y), 0.0) -
                        radius;
    float out_chamfer = max(df_out.x + df_out.y - border_size * 0.3,
                        max(df_out.x, df_out.y)) -
                        radius;
    float dist_edge   = mix(out_round, out_chamfer, chamfer) +
                        smoothing;
    float alpha_edge  = smoothstep(-smoothing, smoothing, -dist_edge);

    alpha_edge -= alpha_inside;

    vec4 col = mix(border, color, alpha_inside);

    col.a *= alpha_inside * color.a + alpha_edge * border.a;
    FragColor = col;
}
