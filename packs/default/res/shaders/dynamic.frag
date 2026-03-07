#version 450

layout(binding = 0) uniform sampler2D tex;

in vec2 uv_coords;
in vec3 frag_normal;
in vec3 frag_pos;

out vec4 out_color;
void main(){
    out_color = vec4(1);
}