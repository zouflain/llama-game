#version 450

layout(location = 0) in vec2 uv_coords;
layout(location = 1) in vec3 frag_normal;
layout(location = 2) in vec3 frag_pos;
layout(location = 3) in float frag_depth;

out vec4 out_color;
out vec4 world_layer;
out vec4 depth_layer;
out vec4 normal_layer;

void main(){
    float ang = clamp(dot(frag_normal, vec3(0, 0, 1)), 0, 1);
    out_color = vec4(vec3(1) * pow(ang, 0.5), 1);
    world_layer = vec4(frag_pos, 0.0);
    depth_layer = vec4(frag_depth);
    normal_layer = vec4(frag_normal, 0.0);
}