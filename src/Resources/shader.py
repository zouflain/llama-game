from __future__ import annotations
from .resource import Resource
from OpenGL.GL.shaders import compileProgram, compileShader
import OpenGL.GL as GL

class Shader(Resource):
    def __init__(self, name: str, permanent: bool = False):
        super().__init__(name, permanent)
        self.program = 0
        self.shaders = []

    @staticmethod
    async def allocate(name: str, permanent: bool, fname: str) -> Shader:
        fs = Resource.file_system()
        item = Shader(name, permanent)
        name = fname[:-5]
        try:
            if fname.endswith(".vert") or fname.endswith(".frag"):
                with fs.open(f"shaders/{name}.vert") as vert_file:
                    with fs.open(f"shaders/{name}.frag") as frag_file:
                        vert_src = vert_file.read()
                        frag_src = frag_file.read()
                        if fs.isfile(f"shaders/{name}.geom"):
                            with fs.open(f"shaders/{name}.geom") as geom_file:
                                geom_src = geom_file.read()
                                item.shaders = [
                                    compileShader(geom_src, GL.GL_GEOMETRY_SHADER),
                                    compileShader(vert_src, GL.GL_VERTEX_SHADER),
                                    compileShader(frag_src, GL.GL_FRAGMENT_SHADER)
                                ]
                        else:
                            item.shaders = [
                                compileShader(vert_src, GL.GL_VERTEX_SHADER),
                                compileShader(frag_src, GL.GL_FRAGMENT_SHADER)
                            ]
                        item.program = compileProgram(*item.shaders)
                        await item.register()
            elif fname.endswith(".comp"):
                with fs.open(fname) as comp_file:
                    item.shaders = [compileShader(comp_file.read(), GL.GL_COMPUTE_SHADER)]
                    item.program = compileProgram(*item.shaders)
                    await item.register()
            return item
        except Exception as err:
            print("Error loading shader:", err) #TODO: log this correctly!
            raise

    async def deallocate(self):
        if self.program:
            for shader in self.shaders:
                GL.glDetachShader(self.program, shader)
                GL.glDeleteShader(shader)
            GL.glDeleteProgram(self.program)
        await super().deallocate()