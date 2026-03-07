#version 450

layout(binding = 0) uniform sampler2D tex;

layout(std430, binding = 1) buffer Model{
    mat4 model;
};

/*
struct Light{
    float diffuse[3];
    float ambient[3];
    float position[3];
};
layout(std430, binding = 4) buffer Lights{
    Light lights[];
};*/

in vec2 uv_coords;
in vec3 frag_normal;
in vec3 frag_pos;

out vec4 out_color;
//out int out_entity;

void main(){
    vec4 tex_color = texture(tex, uv_coords);
    /*out_color = vec4(0.0,0.0,0.0,0.0);
    for(int i=0; i<4; i++){
        vec3 l_pos = vec3(lights[i].position[0],lights[i].position[1],lights[i].position[2]);
        float light_angle = dot(frag_normal, normalize(l_pos-frag_pos));
        light_angle = clamp(light_angle,0,1);
        vec3 light_color = vec3(
            tex_color.x*lights[i].ambient[0] + lights[i].diffuse[0]*light_angle,
            tex_color.y*lights[i].ambient[1] + lights[i].diffuse[1]*light_angle,
            tex_color.z*lights[i].ambient[2] + lights[i].diffuse[2]*light_angle
        );
        out_color += vec4(light_color,0.0);
    }*/
    out_color = tex_color;
    //out_color = vec4(tex_color.xy,1,1);
    //out_color = vec4(uv_coords,1,1);
    //out_entity = eid;
    //out_color = vec4(1);
}