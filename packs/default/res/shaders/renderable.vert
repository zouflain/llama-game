
#version 450

layout(location=0) uniform mat4 model;
layout(location=1) uniform mat4 view;
layout(location=2) uniform mat4 projection;
layout(location=3) uniform int num_bones;
layout(location=4) uniform int num_frames;

struct Interpolation{
    int start_frame;
    int end_frame;
    float idx_coef;
    float blend_coef;
};
layout(location=5) uniform Interpolation interpolations[4];

layout(binding=0) uniform sampler2D tex;

struct Vert{
    float pos[3];
    float normal[3];
    float bone_weights[4];
    int bone_ids[4];
    vec2 uv;
};
layout(std430, binding=1) buffer Verts{
    Vert v_data[];
};
layout(std430, binding=2) buffer InverseBinds{
    mat4 inverses[];
};
struct Bone{
    float pos[3];
    float quat[4];
    float scale[3];
};
layout(std430, binding=3) buffer Frames{
    Bone bones[];
};

layout(location = 0) out vec2 uv_coords;
layout(location = 1) out vec3 frag_normal;
layout(location = 2) out vec3 frag_pos;


void main(){
    uv_coords = v_data[gl_VertexID].uv;
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

    /*vec4 v_skinned = vec4(0);
    for(int i=0;i<4;i++){
        int current_bone = v_data[gl_VertexID].bone_ids[i];
        v_skinned += vec4(v_pos, 1) * inv_bind[current_bone].pose * temp_bone * v_data[gl_VertexID].bone_weights[i];
    }
    vec4 world_pos = v_skinned * correction * makeModel();*/

    vec4 world_pos = vec4(0);
    frag_pos = vec3(world_pos);
    gl_Position = world_pos * view * projection;
}
