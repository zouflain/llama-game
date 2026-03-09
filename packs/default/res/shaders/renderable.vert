
#version 450

layout(location=0) uniform mat4 model;
layout(location=1) uniform mat4 view;
layout(location=2) uniform mat4 projection;

struct Vert{
    float pos[3];
    float normal[3];
    float uv[2];
    float bone_weights[4];
    int bone_ids[4];
};
layout(std430, binding=0) buffer Verts{
    Vert v_data[];
};
layout(std430, binding=1) buffer Frame{
    mat4 bones[];
};

layout(location = 0) out vec2 uv_coords;
layout(location = 1) out vec3 frag_normal;
layout(location = 2) out vec3 frag_pos;

void main(){
    uv_coords = vec2(
        v_data[gl_VertexID].uv[0],
        v_data[gl_VertexID].uv[1]
    );
    frag_normal = vec3(
        v_data[gl_VertexID].normal[0],
        v_data[gl_VertexID].normal[1],
        v_data[gl_VertexID].normal[2]
    );
    vec3 v_pos = vec3(
        v_data[gl_VertexID].pos[0],
        v_data[gl_VertexID].pos[1],
        v_data[gl_VertexID].pos[2]
    );

    vec4 world_pos = vec4(0);
    vec4 world_norm = vec4(0);
    mat4 transform = mat4(0);
    for(int i=0; i<4; i++){
        transform += bones[v_data[gl_VertexID].bone_ids[i]]*v_data[gl_VertexID].bone_weights[i];
    }
    world_pos = model * transform  * vec4(v_pos, 1.0);
    world_norm = transform * vec4(frag_normal, 0);

    frag_pos = vec3(world_pos);
    frag_normal = normalize(mat3(model)*vec3(world_norm));
    gl_Position = projection * view * world_pos;
}
