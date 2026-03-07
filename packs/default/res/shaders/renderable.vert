
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

// Helpers for quick conversion
vec3 toVec3(float values[3]){
    return vec3(values[0], values[1], values[2]);
}
void writeVec3(vec3 value, inout float result[3]){
    //unwound for loop for slight optimization
    result[0] = value[0];
    result[1] = value[1];
    result[2] = value[2];
}
vec4 toVec4(float values[4]){
    return vec4(values[0], values[1], values[2], values[3]);
}
void writeVec4(vec4 value, inout float result[4]){
    //unwound for loop for slight optimization
    result[0] = value[0];
    result[1] = value[1];
    result[2] = value[2];
    result[3] = value[3];
}

//Main functions
vec3 lerp(vec3 v1, vec3 v2, float coef){
    return (1.0f-coef)*v1+coef*v2;
}
vec4 lerp4(vec4 v1, vec4 v2, float coef){
    return (1.0f-coef)*v1+coef*v2;
}

vec4 slerp(vec4 q1, vec4 q2, float coef){
    float dp = dot(q1, q2);
    if(dp < 0.0f){
        q2 = -q2;
        dp = -dp;
    }
    dp = clamp(dp, -1.0f, 1.0f);

    float theta = acos(dp);
    if(theta < 0.001){
        return normalize(lerp4(q1, q2, coef));
    }

    float invs_theta = 1/sin(theta);
    float w1 = sin((1.0f - coef) * theta) * invs_theta;
    float w2 = sin(coef *theta) * invs_theta;

    return w1 * q1 + w2 * q2;
}

void interpolate(Bone b1, Bone b2, float coef, inout Bone result){
    writeVec3(
        lerp(
            toVec3(b1.pos),
            toVec3(b2.pos),
            coef
        ),
        result.pos
    );
    writeVec3(
        lerp(
            toVec3(b1.scale),
            toVec3(b2.scale),
            coef
        ),
        result.scale
    );
    writeVec4(
        slerp(
            toVec4(b1.quat),
            toVec4(b2.quat),
            coef
        ),
        result.quat
    );
}

mat4 toMat4(Bone b){
    vec3 pos = toVec3(b.pos);
    vec3 scale = toVec3(b.scale);
    vec4 q = toVec4(b.quat).yzwx;//Note the swizzle, from blender wxyz order

    // Shameless AI code...
    float x2 = q.x + q.x, y2 = q.y + q.y, z2 = q.z + q.z;
    float xx = q.x * x2, xy = q.x * y2, xz = q.x * z2;
    float yy = q.y * y2, yz = q.y * z2, zz = q.z * z2;
    float wx = q.w * x2, wy = q.w * y2, wz = q.w * z2;

    return mat4(
        vec4((1.0 - (yy + zz)) * scale.x, (xy + wz) * scale.x, (xz - wy) * scale.x, 0.0),
        vec4((xy - wz) * scale.y, (1.0 - (xx + zz)) * scale.y, (yz + wx) * scale.y, 0.0),
        vec4((xz + wy) * scale.z, (yz - wx) * scale.z, (1.0 - (xx + yy)) * scale.z, 0.0),
        vec4(pos, 1.0)
    );
}

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

    vec4 world_pos = vec4(0);
    for(int i=0; i<4; i++){
        float blend = interpolations[i].blend_coef;
        if(blend < 0){
            continue;
        }

        vec4 v_pos_prime = vec4(0);
        for(int j=0; j<4; j++){
            float weight = v_data[gl_VertexID].bone_weights[j];
            if(weight < 0){
                continue;
            }

            int bone_id = v_data[gl_VertexID].bone_ids[j];
            int prev_id = interpolations[i].start_frame*num_frames+bone_id;
            int next_id = interpolations[i].end_frame*num_frames+bone_id;

            Bone interpolated;
            interpolate(bones[prev_id], bones[next_id], interpolations[i].idx_coef, interpolated);
            v_pos_prime += vec4(v_pos, 1.0f)*inverses[bone_id]*toMat4(interpolated)*weight;
        }
        world_pos += v_pos_prime*blend;
    }
    frag_pos = vec3(world_pos);
    gl_Position = world_pos * model * view * projection;
}
