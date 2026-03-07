from .resource import Resource
from collada import Collada
from pygltflib import GLTF2
from collections import defaultdict
import numpy as np
import OpenGL.GL as GL


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
            ("quat", (np.float32, 4)), # wxyz
            ("scale", (np.float32, 3))
        ]
    )

    class Mesh:
        def __init__(self, vertex_data: np.array):
            self.vertex_data = vertex_data
            self.ssbo = GL.glCreateBuffers(1)
            GL.glNamedBufferStorage(self.ssbo, self.vertex_data.nbytes, self.vertex_data, 0)


    def __init__(self, name: str, permanent: bool, meshes: dict, inverses: np.array, frames: np.array):
        super().__init__(name, permanent)
        self.meshes = meshes
        self.inverses = inverses
        self.frames = frames

        self.inverse_ssbo = GL.glCreateBuffers(1)
        GL.glNamedBufferStorage(self.inverse_ssbo, self.inverses.nbytes, self.inverses, 0)

        self.frames_ssbo = GL.glCreateBuffers(1)
        GL.glNamedBufferStorage(self.frames, self.frames.nbytes, self.frames, 0)
        
    @staticmethod
    async def allocate(name: str, permanent: bool, fname: str, ftype: str) -> Renderable:
        # load from file
        with Resource.file_system().openbin(fname, mode="rb") as file:
            num_bones = np.frombuffer(file.read(4), dtype=np.int32)[0]
            inverses = np.frombuffer(file.read(Renderable.__inverse_dtype.itemsize*num_bones), dtype=Renderable.__inverse_dtype)

            num_frames = np.frombuffer(file.read(4), dtype=np.int32)[0]
            frames = np.frombuffer(file.read(Renderable.__bone_dtype.itemsize*num_bones*num_frames), dtype=Renderable.__bone_dtype).reshape(num_frames, num_bones)

            meshes = {}
            num_meshes = np.frombuffer(file.read(4), dtype=np.int32)[0]
            for i in range(num_meshes):
                buffer = file.peek(64)
                name = file.read(buffer.find(b'\x00')+1)[:-1].decode("utf-8")
                num_verts = np.frombuffer(file.read(4), dtype=np.int32)[0]
                vertices = np.frombuffer(file.read(Renderable.__vertex_dtype.itemsize*num_verts), dtype=Renderable.__vertex_dtype)
                meshes[name] = Renderable.Mesh(vertices)

        return Renderable(name, permanent, meshes, inverses, frames)

    async def deallocate(self) -> None:
        for mesh in self.meshes.values():
            GL.glDeleteFramebuffers(1, [mesh.ssbo])
        GL.glDeleteFramebuffers(2, [self.inverse_ssbo, self.frames_ssbo])

        # Clean up JUST in case
        self.meshes = {}
        self.inverses = np.array([], dtype=Renderable.__inverse_dtype)
        self.frames = np.array([], dtype=Renderable.__bone_dtype)
        self.inverse_ssbo = 0
        self.frames_ssbo = 0