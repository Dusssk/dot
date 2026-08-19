void main() {
    float dist = length(gl_PointCoord - vec2(0.5));

    fragColor = fColor;

    if (dist > radius[0]) {
        discard;

    }
    float alpha = smoothstep(radius[0], radius[1], dist);
    fragColor[3] = alpha;
}