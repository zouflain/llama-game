from __future__ import annotations
import OpenGL.GL as GL
import glm as GLM
import sdl2 as SDL
import numpy as np

from .system import System
import Events, Components, Resources

class Combatant(Components.Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actions = {
            "pending": None, # action to be performed upon crossing act threshold
            "prepared": None, # action clears upon crossing prep threshold, but can trigger
            "performing": None
        }


class BattleAnimator(Components.Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.elapsed_time = None
        self.frame_data = None


class Battle(System):
    def __init__(self):
        super().__init__()

    @System.on(Events.Render, 100)
    async def onRenderStep(self, event: Events.Render) -> bool:

        #### TEST CODE ####
        fbo_res = (640, 480)
        GL.glClearColor(1,1,0,1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)

        # Setup/Allocate (rechecks every frame to be sure these things dont get deallocated randomly)
        framebuffer = Resources.Framebuffer["battle_buffer"]
        shader = Resources.Shader["renderable"]

        if framebuffer is None:
            framebuffer = await Resources.Framebuffer.allocate("battle_buffer", False, fbo_res, 1)

        if shader is None:
            shader = await Resources.Shader.generate(name="renderable", permanent=True, fname="renderable.vert")

        renderable = Resources.Renderable["mage"]

        GL.glEnable(GL.GL_DEPTH_TEST)
        with Resources.Framebuffer.Binding(framebuffer, event.resolution):
            GL.glClearColor(0.05,0.05,0.05,1)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
            with Resources.Shader.Binding(shader):
                model = np.eye(4, dtype=np.float32)*70
                model[3][3] = 1.0
                view = GLM.lookAt((-10, -10, 10), (0, 0, 0), (0, 0, 1))
                projection = GLM.ortho(-framebuffer.resolution[0]/2, framebuffer.resolution[0]/2, -framebuffer.resolution[1]/2, framebuffer.resolution[1]/2, -1000, 1000)
                renderable.draw(
                    model,
                    view,
                    projection,
                    [mesh for mesh in renderable.meshes.keys() if mesh != "Icosphere"],
                    [Resources.Renderable.BlendFactor(738, 738, 1, 1)]
                )
        GL.glNamedFramebufferReadBuffer(framebuffer.fbo, GL.GL_COLOR_ATTACHMENT0)
        GL.glBlitNamedFramebuffer(framebuffer.fbo, 0, 0, 0, fbo_res[0], fbo_res[1], 0, 0, event.resolution[0], event.resolution[1], GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
        SDL.SDL_GL_SwapWindow(event.window)
        #### END TEST CODE ####

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