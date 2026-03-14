from __future__ import annotations
from enum import Enum
import OpenGL.GL as GL
import glm as GLM
import sdl2 as SDL
import numpy as np

from .system import System
import Events, Components, Resources


class Combatant(Components.Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.actions = {
            "pending": None, # action to be performed upon crossing act threshold
            "prepared": None, # action clears upon crossing prep threshold, but can trigger
            "performing": None
        }


class BattleAnimator(Components.Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elapsed_time = None
        self.frame_data = None


class Battle(System):
    class Constants (int, Enum):
        COLOR = 0
        WORLD = 1
        DEPTH = 2
        NORMALS = 3
        OUTPUT = 4

        IMAGE_UNIT = 32  # size of an individual image unit (for subdivision of compute shader)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def boot(self, render_size: tuple[int, int]) -> bool:
        self.framebuffer = await Resources.Framebuffer.allocate("battle_buffer", False, render_size, 5)
        self.render_shader = await Resources.Shader.generate(name="renderable", permanent=True, fname="renderable.vert")
        self.sobel_shader = await Resources.Shader.generate(name="outlines", permanent=True, fname="outlines.comp")
        
        self.glyph_shader = await Resources.Shader.generate(name="glyphs", permanent=True, fname="text.comp")
        return True

    @System.on(Events.Render, System.Priority.LOWEST)
    async def onRenderStep(self, event: Events.Render) -> bool:
        GL.glClearColor(0,0,0,0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)

        #### TEST CODE ####
        model = np.eye(4, dtype=np.float32)*70
        model[3, :3] = np.array([25,25,0], dtype=np.float32)
        model[3][3] = 1.0
        view = GLM.lookAt((100, -100, 100), (0, 0, 0), (0, 0, 1))
        projection = GLM.ortho(-self.framebuffer.resolution[0]/2, self.framebuffer.resolution[0]/2, -self.framebuffer.resolution[1]/2, self.framebuffer.resolution[1]/2, 0, 1000)
        #### END TEST CODE ####

        GL.glEnable(GL.GL_DEPTH_TEST)
        with Resources.Framebuffer.Binding(self.framebuffer, event.resolution):
            GL.glClearColor(0.05,0.05,0.05,1)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
            with Resources.Shader.Binding(self.render_shader) as render_prog:
                for eid, combatant in Components.Combatant.getAll():
                    Resources.Renderable[combatant.mannequin].draw(render_prog, model, view, projection, combatant.active_meshes, [Resources.Renderable.BlendFactor(2, 2, 0.5, 1)])

            with Resources.Shader.Binding(self.sobel_shader):
                GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)
                GL.glBindImageTexture(Battle.Constants.COLOR, self.framebuffer.textures[GL.GL_COLOR_ATTACHMENT0], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.WORLD, self.framebuffer.textures[GL.GL_COLOR_ATTACHMENT1], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.DEPTH, self.framebuffer.textures[GL.GL_COLOR_ATTACHMENT2], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.NORMALS, self.framebuffer.textures[GL.GL_COLOR_ATTACHMENT3], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)

                GL.glBindImageTexture(Battle.Constants.OUTPUT, self.framebuffer.textures[GL.GL_COLOR_ATTACHMENT4], 0, GL.GL_FALSE, 0, GL.GL_WRITE_ONLY, GL.GL_RGBA32F)
                GL.glDispatchCompute(int(self.framebuffer.resolution[0]/32)+1, int(self.framebuffer.resolution[1]/32)+1, 1, 0)
                GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

            with Resources.Shader.Binding(self.glyph_shader) as glyph_program:
                Resources.GlyphSet["font"].draw(
                    #glyph_program, event.resolution, self.framebuffer.textures[GL.GL_COLOR_ATTACHMENT4], "Hello world!\n#ff0000TEST!", (0, 0), 32, (1184,96), (0,1,1)
                    glyph_program, event.resolution, self.framebuffer.textures[GL.GL_COLOR_ATTACHMENT4],
                    #"ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789'\"+_)(&^%$@!`?.><\\/)",
                    "You there! Out of the WAY!\nKeep standin' there and you'll\nget knocked into the ocean!",
                    (0, 0), 32, (1184,96), (0,1,1)
                )

        GL.glNamedFramebufferReadBuffer(self.framebuffer.fbo, GL.GL_COLOR_ATTACHMENT4)
        GL.glBlitNamedFramebuffer(self.framebuffer.fbo, 0, 0, 0, event.render_size[0], event.render_size[1], 0, 0, event.resolution[0], event.resolution[1], GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)

        #System.immediateEvent(PostRender())
        SDL.SDL_GL_SwapWindow(event.window)

        return False

    @System.on(Events.Logic, System.Priority.DEFAULT)
    async def onLogicStep(self, event: Events.Logic) -> bool:
        combatant_ids = Components.find([Combatant, BattleAnimator])
        action_occuring = None
        for combatant_id in combatant_ids:
            combatant = Components.Combatant[combatant_id]
            action_occuring = combatant.actions["performing"]
            if action_occuring:
                break
        
        if action_occuring:
            pass

        return False

    @System.on(Events.FromSDL, System.Priority.DEFAULT+10)
    async def interfaceCatchSDL(self, event: Events.FromSDL) -> bool:
        #print(event)
        return False

    @System.on(Events.FromSDL, System.Priority.HIGHEST)
    async def gameplayCatchSDL(self, event: Events.FromSDL):
        #print("Nope!")
        return True