from .resource import Resource
from typing import defaultdict
import OpenGL.GL as GL

class Framebuffer(Resource):
    class Binding:
        __fbo: int = 0
        __resolution: tuple[float, float] = None

        def __init__(self, framebuffer: Framebuffer, fallback: tuple[float, float] = None):
            self.prev_resolution = Framebuffer.Binding.__resolution
            self.prev_fbo = Framebuffer.Binding.__fbo
            self.fbo = framebuffer.fbo
            self.resolution = framebuffer.resolution
            self.fallback = fallback
            Framebuffer.Binding.__fbo = self.fbo
            Framebuffer.Binding.__resolution = self.resolution

        def __enter__(self) -> Framebuffer.Binding:
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fbo)
            GL.glViewport(0, 0, self.resolution[0], self.resolution[1])
            return self

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            Framebuffer.Binding.__resolution = self.prev_resolution
            Framebuffer.Binding.__fbo = self.prev_fbo

            resolution = self.prev_resolution or self.fallback
            #TODO: assert(resolution)

            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.prev_fbo)
            GL.glViewport(0, 0, resolution[0], resolution[1])



    def __init__(self, name: str, permanent: bool, resolution: tuple[int, int], fbo: int, textures: dict):
        super().__init__(name, permanent)
        self.fbo = fbo
        self.textures = textures
        self.resolution = resolution

    @staticmethod
    async def allocate(name: str, permanent: bool, resolution: tuple[int, int], color_channels: int) -> Framebuffer:
        textures = {}

        # Gen FBO
        fbo = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fbo)


        if color_channels > 0:
            # Generate channels [color, normal, ...]
            GL.glDrawBuffers(color_channels, [GL.GL_COLOR_ATTACHMENT0+i for i in range(color_channels)])
            texture_ids = GL.glGenTextures(color_channels) if color_channels > 1 else [GL.glGenTextures(color_channels)]
            for i in range(color_channels):
                GL.glBindTexture(GL.GL_TEXTURE_2D, texture_ids[i])
                GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, resolution[0], resolution[1], 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
                GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0+i, GL.GL_TEXTURE_2D, texture_ids[i], 0)
                textures[GL.GL_COLOR_ATTACHMENT0+i] = texture_ids[i]

            # attach depth buffer
            depth = GL.glGenTextures(1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, depth)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT24, resolution[0], resolution[1], 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)     
            GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, depth, 0)
            textures[GL.GL_DEPTH_ATTACHMENT] = depth

            item = Framebuffer(name, permanent, resolution, fbo, textures)

            if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) != GL.GL_FRAMEBUFFER_COMPLETE:
                GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
                raise Exception("Bad framebuffer!")
            else:
                GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
                await item.register()
                return item
        else:
            raise Exception(f"Invalid channel count: {color_channels}")

    def bind(self):
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fbo)
        GL.glViewport(0, 0, self.resolution[0], self.resolution[1])

    @staticmethod
    def unbind(window_resolution: tuple[int, int]):
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glViewport(0, 0, window_resolution[0], window_resolution[1])

    async def deallocate(self):
        GL.glDeleteFramebuffers(1, [self.fbo])
        if self.textures:
            GL.glDeleteTextures(len(self.textures), list(self.textures.values()))
        await super().deallocate()