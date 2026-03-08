#version 450

layout(location = 0) in vec2 uv_coords;
layout(location = 1) in vec3 frag_normal;
layout(location = 2) in vec3 frag_pos;

out vec4 out_color;

void main(){
    float dot = dot(frag_normal, vec3(0, 0, 1));
    out_color = vec4(1,1,1,1) * dot;
}