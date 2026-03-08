
#version 450
/*
struct Vert{
    float pos[3];
};


void main(){
    vec3 vpos = vec3(
        v_data[gl_VertexID].pos[0],
        v_data[gl_VertexID].pos[1],
        v_data[gl_VertexID].pos[2]
    );
    gl_Position = vec4(vpos, 1);
}
*/

layout(location=0) uniform mat4 model;
layout(location=1) uniform mat4 view;
layout(location=2) uniform mat4 projection;

void main(){
    gl_Position = projection * view * model * vec4(0, 0, 0, 1);
}