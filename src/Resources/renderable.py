from .resource import Resource
from collada import Collada
from pygltflib import GLTF2
import numpy as np
from collections import defaultdict


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
            self.num_faces = len(vertex_data)/3
            self.vertex_data = vertex_data


    def __init__(self, name: str, permanent: bool, meshes: list[Renderable.Mesh] = None):
        super().__init__(name, permanent)
        self.meshes = {}

    @staticmethod
    async def allocate(name: str, permanent: bool, fname: str, ftype: str) -> Renderable:
        meshes = {}
        """
        with Resource.file_system().openbin(fname, mode="r") as file:
            scene = impasse.load(file, file_type=ftype)
            for mesh in scene.meshes:
                '''num_faces = len(mesh.faces)

                normals_array = np.array(mesh.normals, dtype=np.float32)
                vertices_array = np.array(mesh.vertices, dtype=np.float32)
                face_array = np.array(mesh.faces, dtype=np.int32)

                face_normals = normals_array[face_array]
                summed_normals = face_normals.sum(axis=1)
                norms = np.linalg.norm(summed_normals, axis=1, keepdims=True)
                final_normals = np.divide(summed_normals, norms, out=np.zeros_like(summed_normals), where=norms!=0)
                flattened_faces = face_array.ravel()
                repeated_normals = np.repeat(final_normals, 3, axis=0)
                vertex_data = np.zeros(num_faces * 3, dtype=Renderable.__vertex_dtype)

                vertex_data['pos'] = vertices_array[flattened_faces]
                vertex_data['normal'] = repeated_normals
                #if mesh.texture_coords:
                #    vertex_data['uv'] = mesh.texture_coords[0][flattened_faces][:,:2]
                x = vertex_data'''

                num_faces = len(mesh.faces)
                vertex_data = np.zeros(num_faces*3, dtype=Renderable.__vertex_dtype)
                weight_lookup = defaultdict(list)
                if len(mesh.bones) > 0:
                    for b, bone in enumerate(mesh.bones):
                        if len(bone.weights) > 0:
                            all_weights = list(bone.weights)

                            for w in range(len(all_weights)):
                                weight = all_weights[w]
                                weight_lookup[weight.vertex_id].append((b, weight.weight))

                            '''
                            for weight in bone.weights:
                                weight_lookup[weight.vertex_id].append((b, weight.weight))
                            '''

                    for weight_list in weight_lookup.values():
                        weight_list.sort(key=lambda l: l[1])
                        weight_list.extend((0, 0)*4)
                        weight_list = weight_list[:4]

                        print(weight_list)

                for i, face in enumerate(mesh.faces):

                    # Per face normals
                    normal = np.zeros(3, dtype=np.float32)
                    for vertex in face:
                        normal += mesh.normals[vertex]
                    norm = np.linalg.norm(normal)
                    normal = normal / norm if norm > 0 else normal

                    # Append face vertices
                    for j, vertex in enumerate(face):
                        vid = i*3*j
                        vertex_data[vid]['pos'] = mesh.vertices[vertex]
                        vertex_data[vid]['normal'] = normal

                        # get bones
                        if mesh.bones and vertex in weight_lookup:
                            vertex[vid]["bones"] = [weight[0] for weight in weight_lookup]
                            vertex[vid]["weights"] = [weight[1] for weight in weight_lookup]
                        else:
                            vertex[vid]['bones'] = (0, 0, 0, 0)
                            vertex[vid]['weights'] = (1, 0, 0, 0)
                meshes[mesh.name] = Renderable.Mesh(num_faces, vertex_data)
        """

        """
        with Resource.file_system().openbin(fname, mode="rb") as file:
            scene = Collada(file)
            for mesh in scene.geometries:
                vertex_lists = []
                controller = next((cntl for cntl in scene.controllers if cntl.geometry == mesh), None)
                for triangles in mesh.primitives:

                    # Build out spacial data
                    positions = triangles.vertex[triangles.vertex_index].reshape(-1, 3)
                    num_verts = len(positions)
                    v0, v1, v2 = positions[0::3], positions[1::3], positions[2::3]
                    face_normals = np.cross(v1 - v0, v2 - v0)
                    face_normals /= np.linalg.norm(face_normals, axis=1)[:,np.newaxis]
                    normals = np.repeat(face_normals, 3, axis=0)
                    if len(triangles.texcoordset) > 0:
                        uvs = triangles.texcoordset[0][triangles.texcoord_indexset[0]].reshape(-1, 2)
                    else:
                        uvs = np.zeros(num_verts, dtype=(np.float32, 2))

                    # Build out weights
                    bones = np.zeros((num_verts, 4), dtype=np.int32)
                    weights = np.zeros((num_verts, 4), dtype=np.float32)
                    if controller is not None:
                        '''
                        for i, v in enumerate(triangles.vertex_index.flatten()):
                            influences = controller.weights[v]
                            for j, (bone_id, weight) in enumerate(influences[:4]):
                                bones[i, j] = bone_id
                                weights[i, j] = weight
                        '''
                        cursor = 0
                        for v, count in enumerate(controller.vcounts):
                            influences = controller.index[cursor: cursor + count*2]
                            cursor += count*2

                            bone_ids = influences[0::2]
                            weight_indices = influences[1::2]
                            weights_indexed = controller.weights[weight_indices]

                            n = min(count, 4)
                            bones[v, :n] = bone_ids[:n]
                            weights[v, :n] = weights_indexed[:n]

                    # assemble arrays
                    vertices = np.empty(num_verts, dtype=Renderable.__vertex_dtype)
                    vertices["pos"] = positions
                    vertices["normal"] = normals
                    vertices["uv"] = uvs
                    vertices["bones"] = bones
                    vertices["weights"] = weights

                    vertex_lists.append(vertices)

                vertex_data = np.concatenate(vertex_lists)

                meshes[mesh.name] = Renderable.Mesh(vertex_data)
        """

        """
        with Resource.file_system().openbin(fname, mode="r") as file:
            glb = GLTF2().load_binary_from_file_object(file)
            #blob = glb.binary_blob()
            print("wtf?")
            for mesh in glb.meshes:
                vertex_lists = []
                for primitive in mesh.primitives:
                    # assemble arrays
                    num_verts = glb.accessors[primitive.attributes.POSITION].count
                    vertices = np.empty(num_verts, dtype=Renderable.__vertex_dtype)
                    vertices["pos"] = positions
                    vertices["normal"] = normals
                    vertices["uv"] = uvs
                    vertices["bones"] = bones
                    vertices["weights"] = weights

                    vertex_lists.append(vertices)

                vertex_data = np.concatenate(vertex_lists)

                meshes[mesh.name] = Renderable.Mesh(vertex_data)
        """

        # load from file
        with Resource.file_system().openbin(fname, mode="rb") as file:
            num_bones = np.frombuffer(file.read(4), dtype=np.int32)[0]
            inverses = np.frombuffer(file.read(Renderable.__inverse_dtype.itemsize*num_bones), dtype=Renderable.__inverse_dtype)

            num_frames = np.frombuffer(file.read(4), dtype=np.int32)[0]
            frames = np.frombuffer(file.read(Renderable.__bone_dtype.itemsize*num_bones*num_frames), dtype=Renderable.__bone_dtype).reshape(num_frames, num_bones)

            num_meshes = np.frombuffer(file.read(4), dtype=np.int32)[0]
            meshes = {}
            for i in range(num_meshes):
                buffer = file.peek(64)
                name = file.read(buffer.find(b'\x00')+1)[:-1].decode("utf-8")
                num_verts = np.frombuffer(file.read(4), dtype=np.int32)[0]
                vertices = np.frombuffer(file.read(Renderable.__vertex_dtype.itemsize*num_verts), dtype=Renderable.__vertex_dtype)
                meshes[name] = vertices

        # generate buffers
        



        return Renderable(name, permanent, meshes)