from .resource import Resource
from scipy.spatial.transform import Rotation
from dataclasses import dataclass
from enum import Enum
import numpy as np
import OpenGL.GL as GL
import glm as GLM


class Renderable(Resource):
    __vertex_dtype = np.dtype(
        [
            ("pos", (np.float32, 3)),
            ("normal", (np.float32, 3)),
            ("uv", (np.float32, 2)),
            ("weights", (np.float32, 4)),
            ("bones", (np.uint32, 4))
        ]
    )

    __inverse_dtype = np.dtype((np.float32, 16))

    __bone_dtype = np.dtype(
        [
            ("pos", (np.float32, 3)),
            ("quat", (np.float32, 4)), # xyzw
            ("scale", (np.float32, 3))
        ]
    )

    class Bindings(int, Enum):
        VERTICES = 0
        BONES = 1

        MODEL = 0
        VIEW = 1
        PROJ = 2

    class Mesh:
        def __init__(self, vertex_data: np.array):
            self.vertex_data = vertex_data

            buffer_array = (GL.GLuint * 1)()
            GL.glCreateBuffers(1, buffer_array)
            self.ssbo = buffer_array[0]
            GL.glNamedBufferStorage(self.ssbo, self.vertex_data.nbytes, self.vertex_data, 0)


    @dataclass
    class BlendFactor:
        start_frame: int
        end_frame: int
        frame_coefficient: float
        blend_coefficient: float


    def __init__(self, name: str, permanent: bool, meshes: dict, inverses: np.array, frames: np.array, parent_ids: np.array):
        super().__init__(name, permanent)
        self.meshes = meshes
        self.inverses = inverses
        self.frames = frames
        self.parent_ids = parent_ids

        buffer_array = (GL.GLuint * 1)()
        GL.glCreateBuffers(1, buffer_array)
        self.bones_ssbo = buffer_array[0]
        GL.glNamedBufferStorage(self.bones_ssbo, 64*len(inverses), None, GL.GL_DYNAMIC_STORAGE_BIT)

    def draw(self, model: np.array, view: GLM.mat4x4, projection: GLM.mat4x4, mesh_list: list[str], blend_factors: list[Renderable.BlendFactor]) -> None:
        '''
       # Do the interpolations
        num_bones = len(self.inverses)
        
        ## Accumulated bones
        a_pos = np.zeros((num_bones, 3), dtype=np.float32)
        a_scale = np.zeros((num_bones, 3), dtype=np.float32)
        a_rvec = np.zeros((num_bones, 3), dtype=np.float32)


        ## Blend
        for factor in blend_factors:
            # fetch bones
            bones_start = self.frames[factor.start_frame]
            bones_end = self.frames[factor.end_frame]

            # interpolate frame
            i_pos = (1 - factor.frame_coefficient)*bones_start["pos"] + factor.frame_coefficient*bones_end["pos"]
            i_scale = (1 - factor.frame_coefficient)*bones_start["scale"] + factor.frame_coefficient*bones_end["scale"]

            # SLERP
            r1 = Rotation.from_quat(bones_start["quat"])
            r2 = Rotation.from_quat(bones_end["quat"])
            i_rot = r1*(r2*r1.inv())**factor.frame_coefficient

            # blend animations
            a_pos += i_pos*factor.blend_coefficient
            a_scale += i_scale*factor.blend_coefficient
            a_rvec += i_rot.as_rotvec()*factor.blend_coefficient

        final_rotations = Rotation.from_rotvec(a_rvec).as_matrix()

        blend_matrices = np.zeros((num_bones, 4, 4), dtype=np.float32)
        blend_matrices[:, :3, :3] = final_rotations * a_scale[:, np.newaxis, :]
        blend_matrices[:, :3, 3] = a_pos
        blend_matrices[:, 3, 3] = 1.0

        final_bones = np.matmul(blend_matrices, self.inverses.reshape(-1, 4, 4))
        '''


        num_bones = len(self.inverses)
        bonez = self.frames[blend_factors[0].end_frame]
        a_pos = bonez["pos"]
        a_scale = bonez["scale"]
        a_rvec =  Rotation.from_quat(bonez["quat"]).as_rotvec()
        final_rotations = Rotation.from_rotvec(a_rvec).as_matrix()

        blend_matrices = np.zeros((num_bones, 4, 4), dtype=np.float32)
        blend_matrices[:, :3, :3] = final_rotations * a_scale[:, np.newaxis, :]
        blend_matrices[:, :3, 3] = a_pos
        blend_matrices[:, 3, 3] = 1.0
        final_bones = np.matmul(blend_matrices, self.inverses.reshape(-1, 4, 4))

        '''
        world_matrices = np.zeros_like(blend_matrices)
        for i in range(num_bones):
            x = blend_matrices[i] @ self.inverses.reshape(-1, 4, 4)[i]
            print(x)
            world_matrices[i] = blend_matrices[i] if self.parent_ids[i] == -1 else world_matrices[self.parent_ids[i]] @ blend_matrices[i]
            #world_matrices[i] = blend_matrices[i] if self.parent_ids[i] == -1 else blend_matrices[i] @ world_matrices[self.parent_ids[i]]
        final_bones = np.matmul(world_matrices, self.inverses.reshape(-1, 4, 4))
        '''
        
        # Finally, draw it
        GL.glUniformMatrix4fv(Renderable.Bindings.MODEL, 1, False, model)
        GL.glUniformMatrix4fv(Renderable.Bindings.VIEW, 1, False, GLM.value_ptr(view))
        GL.glUniformMatrix4fv(Renderable.Bindings.PROJ, 1, False, GLM.value_ptr(projection))
        GL.glNamedBufferSubData(self.bones_ssbo, 0, final_bones.nbytes, final_bones.swapaxes(1, 2))
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, Renderable.Bindings.BONES, self.bones_ssbo)
        for mesh_name in mesh_list:
            mesh = self.meshes.get(mesh_name)
            if mesh:
                GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, Renderable.Bindings.VERTICES, mesh.ssbo)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(mesh.vertex_data))
            # TODO: warn if not

    @staticmethod
    async def allocate(name: str, permanent: bool, fname: str, ftype: str) -> Renderable:
        # load from file
        with Resource.file_system().openbin(fname, mode="rb") as file:
            num_bones = np.frombuffer(file.read(4), dtype=np.int32)[0]
            inverses = np.frombuffer(file.read(Renderable.__inverse_dtype.itemsize*num_bones), dtype=Renderable.__inverse_dtype)
            parent_ids = np.frombuffer(file.read(num_bones*4), dtype=np.int32)

            num_frames = np.frombuffer(file.read(4), dtype=np.int32)[0]
            frames = np.frombuffer(file.read(Renderable.__bone_dtype.itemsize*num_bones*num_frames), dtype=Renderable.__bone_dtype).reshape(num_frames, num_bones)

            meshes = {}
            num_meshes = np.frombuffer(file.read(4), dtype=np.int32)[0]
            for i in range(num_meshes):
                buffer = file.peek(64)
                mesh_name = file.read(buffer.find(b'\x00')+1)[:-1].decode("utf-8")
                num_verts = np.frombuffer(file.read(4), dtype=np.int32)[0]
                vertices = np.frombuffer(file.read(Renderable.__vertex_dtype.itemsize*num_verts), dtype=Renderable.__vertex_dtype)
                meshes[mesh_name] = Renderable.Mesh(vertices)

        item = Renderable(name, permanent, meshes, inverses, frames, parent_ids)
        await item.register()
        return item

    async def deallocate(self) -> None:
        for mesh in self.meshes.values():
            GL.glDeleteFramebuffers(1, [mesh.ssbo])
        GL.glDeleteFramebuffers(1, [self.bones_ssbo])

        # Clean up JUST in case
        self.meshes = {}
        self.inverses = np.array([], dtype=Renderable.__inverse_dtype)
        self.frames = np.array([], dtype=Renderable.__bone_dtype)
        self.inverse_ssbo = 0
        self.frames_ssbo = 0