
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
void main(){
    gl_Position = vec4(1);
}