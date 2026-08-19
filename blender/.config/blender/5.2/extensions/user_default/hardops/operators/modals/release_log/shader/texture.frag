uniform sampler2D image;

uniform vec2 loc;
uniform vec2 size;

uniform float smoothing;

uniform vec4 corner_radius;   // tl, tr, br, bl
uniform vec4 corner_chamfer;  // 0 = round, 1 = chamfer

uniform vec4 clipping; // l, t, r, b

uniform float alpha;

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

    vec2 df = abs(coord - center) -
              ((_size * 0.5 - vec2(smoothing * 0.5)) - vec2(radius));

    float dist_round   = length(max(df, 0.0)) +
                         min(max(df.x, df.y), 0.0) -
                         radius;
    float dist_chamfer = max(df.x + df.y, max(df.x, df.y)) -
                         radius;
    float dist         = mix(dist_round, dist_chamfer, chamfer);

    vec4 col = texture(image, (gl_FragCoord.xy - loc) / size);

    col.a *= smoothstep(-smoothing, smoothing, -dist) * alpha;
    FragColor = col;
}

