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

    @System.on(Events.Render, 100)
    async def onRenderStep(self, event: Events.Render) -> bool:
        GL.glClearColor(0,0,0,0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)


        # Setup/Allocate (rechecks every frame to be sure these things dont get deallocated randomly)
        framebuffer = Resources.Framebuffer["battle_buffer"]
        shader = Resources.Shader["renderable"]
        sobel_shader = Resources.Shader["outlines"]

        if framebuffer is None:
            framebuffer = await Resources.Framebuffer.allocate("battle_buffer", False, event.render_size, 5)

        if shader is None:
            shader = await Resources.Shader.generate(name="renderable", permanent=True, fname="renderable.vert")

        if sobel_shader is None:
            sobel_shader = await Resources.Shader.generate(name="outlines", permanent=True, fname="outlines.comp")

        #### TEST CODE ####
        model = np.eye(4, dtype=np.float32)*70
        model[3, :3] = np.array([25,25,0], dtype=np.float32)
        model[3][3] = 1.0
        view = GLM.lookAt((100, -100, 100), (0, 0, 0), (0, 0, 1))
        projection = GLM.ortho(-framebuffer.resolution[0]/2, framebuffer.resolution[0]/2, -framebuffer.resolution[1]/2, framebuffer.resolution[1]/2, 0, 1000)
        
        renderable = Resources.Renderable["mage"]

        GL.glEnable(GL.GL_DEPTH_TEST)
        with Resources.Framebuffer.Binding(framebuffer, event.resolution):
            GL.glClearColor(0.05,0.05,0.05,1)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
            with Resources.Shader.Binding(shader) as render_prog:
                for eid, combatant in Components.Combatant.getAll():
                    renderable = Resources.Renderable[combatant.mannequin]
                    renderable.draw(render_prog, model, view, projection, combatant.active_meshes, [Resources.Renderable.BlendFactor(2, 2, 0.5, 1)])
                '''
                renderable.draw(
                    render_prog,
                    model,
                    view,
                    projection,
                    [
                        mesh for mesh in renderable.meshes.keys() if mesh not in [
                            "Icosphere", "Spellbook", "Spellbook_open",# "Mage_Hat",
                            "Mage_Cape", "2H_Staff", "1H_Wand"
                        ]
                    ],
                    [Resources.Renderable.BlendFactor(2, 2, 0.5, 1)]
                )
                '''

            GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)
            with Resources.Shader.Binding(sobel_shader):
                GL.glBindImageTexture(Battle.Constants.COLOR, framebuffer.textures[GL.GL_COLOR_ATTACHMENT0], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.WORLD, framebuffer.textures[GL.GL_COLOR_ATTACHMENT1], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.DEPTH, framebuffer.textures[GL.GL_COLOR_ATTACHMENT2], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.NORMALS, framebuffer.textures[GL.GL_COLOR_ATTACHMENT3], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)

                GL.glBindImageTexture(Battle.Constants.OUTPUT, framebuffer.textures[GL.GL_COLOR_ATTACHMENT4], 0, GL.GL_FALSE, 0, GL.GL_WRITE_ONLY, GL.GL_RGBA32F)
                GL.glDispatchCompute(int(framebuffer.resolution[0]/32)+1, int(framebuffer.resolution[1]/32)+1, 1, 0)
            GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        GL.glNamedFramebufferReadBuffer(framebuffer.fbo, GL.GL_COLOR_ATTACHMENT4)
        GL.glBlitNamedFramebuffer(framebuffer.fbo, 0, 0, 0, event.render_size[0], event.render_size[1], 0, 0, event.resolution[0], event.resolution[1], GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
        #### END TEST CODE ####

        #System.immediateEvent(PostRender())
        SDL.SDL_GL_SwapWindow(event.window)

        return False

    @System.on(Events.Logic, 100)
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

    @System.on(Events.FromSDL, 1000)
    async def interfaceCatchSDL(self, event: Events.FromSDL) -> bool:
        #print(event)
        return False

    @System.on(Events.FromSDL, 10)
    async def gameplayCatchSDL(self, event: Events.FromSDL):
        #print("Nope!")
        return True