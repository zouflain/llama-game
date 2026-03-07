#version 450

layout(binding = 0) uniform sampler2D tex;

layout(std430, binding = 1) buffer Model{
    mat4 model;
};

layout(binding = 2, std140) uniform Camera{
    mat4 projection;
    mat4 view;
};

struct Vert{
    float pos[3], normal[3];
    vec2 uv;
};

layout(binding = 3, std430) buffer Verts{
    Vert v_data[];
};

out vec2 uv_coords;
out vec3 frag_normal;
out vec3 frag_pos;

void main(){
    uv_coords = v_data[gl_VertexID].uv;
    frag_normal = vec3(
        v_data[gl_VertexID].normal[0],
        v_data[gl_VertexID].normal[1],
        v_data[gl_VertexID].normal[2]
    );
    vec3 vpos = vec3(
        v_data[gl_VertexID].pos[0],
        v_data[gl_VertexID].pos[1],
        v_data[gl_VertexID].pos[2]
    );
    frag_pos = vec4(vpos,1).xyz;
    //gl_Position = vec4(vpos,1) * view * projection;
    gl_Position = vec4(vpos, 1) * model * view * projection;
}