
#version 450

const mat4 correction = mat4(
    0, 0, 1, 0,
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0 , 0, 1
);

layout(location=0) uniform int num_bones;
layout(location=1) uniform float dt;
layout(location=2) uniform int frame_number;
layout(location=3) uniform vec4 model_pos;
layout(location=4) uniform float model_scale;

layout(binding=0) uniform sampler2D tex;


layout(std140, binding=2) uniform Camera{
    mat4 projection;
    mat4 view;
};


struct Vert{
    float pos[3];
    float normal[3];
    float bone_weights[4];
    int bone_ids[4];
    vec2 uv;
};
layout(std430, binding=3) buffer Verts{
    Vert v_data[];
};

struct Bone{
    mat4 pose;
    int parent_id;
    int padding[3];//STD430 still appears to pad out a struct to align on 16 bytes
};
layout(std430, binding=4) buffer InvBind{
    Bone inv_bind[];
};
layout(std430, binding=5) buffer AnimationPoses{
    Bone a_pos[];
};
layout(std430, binding=6) buffer PrevPoses{
    Bone prev_pos[];
};

out vec2 uv_coords;
out vec3 frag_normal;
out vec3 frag_pos;


mat4 qToMat4(vec4 qin){
    vec4 q = normalize(qin);
    mat4 m;

    m[0][0] = 1 - 2*q.y*q.y - 2*q.z*q.z;
    m[0][1] = 2*q.x*q.y + 2*q.z*q.w;
    m[0][2] = 2*q.x*q.z - 2*q.y*q.w;
    m[0][3] = 0;

    m[1][0] = 2*q.x*q.y - 2*q.z*q.w;
    m[1][1] = 1 - 2*q.x*q.x - 2*q.z*q.z;
    m[1][2] = 2*q.y*q.z + 2*q.x*q.w;
    m[1][3] = 0;

    m[2][0] = 2*q.x*q.z + 2*q.y*q.w;
    m[2][1] = 2*q.y*q.z - 2*q.x*q.w;
    m[2][2] = 1 - 2*q.x*q.x - 2*q.y*q.y;
    m[2][3] = 0;

    m[3][0] = 0;
    m[3][1] = 0;
    m[3][2] = 0;
    m[3][3] = 1;

    return m;
}

vec4 qSlerp(vec4 qa, vec4 qb, float coef){
    vec4 nqa = normalize(qa);
    vec4 nqb = normalize(qb);
    float omega = acos(dot(nqa, nqb));
    bool cond = omega>1e-15;
    float a = mix(1.0f-coef, sin((1.0f-coef)*omega)/sin(omega), cond);
    float b = mix(coef, sin(coef*omega)/sin(omega), cond);
    return a*nqa+b*nqb;
}

vec4 qFromMat4(mat4 m){
    vec4 q;
    float trace = m[0][0] + m[1][1] + m[2][2];
    if( trace > 0 ) {
        float s = 0.5f / sqrt(trace+ 1.0f);
        q.x = ( m[1][2] - m[2][1] ) * s;
        q.y = ( m[2][0] - m[0][2] ) * s;
        q.z = ( m[0][1] - m[1][0] ) * s;
        q.w = 0.25f / s;
    } else {
        if ( m[0][0] > m[1][1] && m[0][0] > m[2][2] ) {
            float s = 2.0f * sqrt( 1.0f + m[0][0] - m[1][1] - m[2][2]);
            q.x = 0.25f * s;
            q.y = (m[1][0] + m[0][1] ) / s;
            q.z = (m[2][0] + m[0][2] ) / s;
            q.w = (m[1][2] - m[2][1] ) / s;
        } else if (m[1][1] > m[2][2]) {
            float s = 2.0f * sqrt( 1.0f + m[1][1] - m[0][0] - m[2][2]);
            q.x = (m[1][0] + m[0][1] ) / s;
            q.y = 0.25f * s;
            q.z = (m[2][1] + m[1][2] ) / s;
            q.w = (m[2][0] - m[0][2] ) / s;
        } else {
            float s = 2.0f * sqrt( 1.0f + m[2][2] - m[0][0] - m[1][1] );
            q.x = (m[2][0] + m[0][2] ) / s;
            q.y = (m[2][1] + m[1][2] ) / s;
            q.z = 0.25f * s;
            q.w = (m[0][1] - m[1][0] ) / s;
        }
    }
    return q;
}

vec4 vFromMat4(mat4 source){
    return vec4(
        source[0][3],
        source[1][3],
        source[2][3],
        source[3][3]
    );
}
mat4 vToMat4(vec4 source){
    mat4 result = mat4(1);
    for(int i=0;i<4;i++){
        result[i][3] = source[i];
    }
    return result;
}


mat4 interpolate(mat4 source, mat4 dest, float coef){
    vec4 q_source = qFromMat4(source);
    vec4 q_dest = qFromMat4(dest);

    vec4 q_final = qSlerp(q_source, q_dest, coef);
    vec4 v_final = vFromMat4(source)*(1-coef)+vFromMat4(dest)*coef;

    mat4 rotation = qToMat4(q_final);
    mat4 translation = vToMat4(v_final);
    return rotation*translation;
}

mat4 makeModel(){
    mat4 result;
    float c = cos(model_pos.w);
    float s = sin(model_pos.w);
    float t = 1-c;

    result[0][0] = c;
    result[0][1] = -s;
    result[0][2] = 0;

    result[1][0] = s;
    result[1][1] = c;
    result[1][2] = 0;

    result[2][0] = 0;
    result[2][1] = 0;
    result[2][2] = (t+c);

    result[3][0] = 0;
    result[3][1] = 0;
    result[3][2] = 0;
    
    result[0][3] = model_pos.x;
    result[1][3] = model_pos.y;
    result[2][3] = model_pos.z;
    result[3][3] = 1;

    mat4 scale = mat4(model_scale);
    scale[3][3] = 1;
    return scale*result;
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

    vec4 v_skinned = vec4(0);
    for(int i=0;i<4;i++){
        int current_bone = v_data[gl_VertexID].bone_ids[i];
        mat4 temp_bone = mat4(1);
        int bone_id = current_bone;
        while(bone_id >= 0){
            int temp_id = num_bones*frame_number+bone_id;
            mat4 interpolated;
            if(frame_number == 0){
                interpolated = prev_pos[current_bone].pose;
            }else if(frame_number == 1){
                interpolated = interpolate(prev_pos[current_bone].pose, a_pos[temp_id].pose, dt);
            }else{
                interpolated = interpolate(a_pos[num_bones*(frame_number-1)+bone_id].pose, a_pos[temp_id].pose, dt);
            }
            //interpolated = a_pos[temp_id].pose;
            temp_bone = temp_bone*interpolated;
            bone_id = a_pos[temp_id].parent_id;
        }
        v_skinned += vec4(v_pos, 1) * inv_bind[current_bone].pose * temp_bone * v_data[gl_VertexID].bone_weights[i];
    }
    vec4 world_pos = v_skinned * correction * makeModel();
    frag_pos = vec3(world_pos);
    gl_Position = world_pos * view * projection;
}
