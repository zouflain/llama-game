from __future__ import annotations
import OpenGL.GL as GL
import sdl2 as SDL

from .system import System
import Events, Components

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
        self.framebuffer = None

    @System.on(Events.Render, 100)
    async def onRenderStep(self, event: Events.Render) -> bool:

        #### TEST CODE ####
        fbo_res = (640, 480)
        GL.glClearColor(1,1,0,1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
        from Resources import Framebuffer
        if self.framebuffer is None:
            self.framebuffer = await Framebuffer.allocate("battle_buffer", False, fbo_res, 1)

        GL.glNamedFramebufferReadBuffer(self.framebuffer.fbo, GL.GL_COLOR_ATTACHMENT0)
        GL.glBlitNamedFramebuffer(self.framebuffer.fbo, 0, 0, 0, fbo_res[0], fbo_res[1], 0, 0, event.resolution[0], event.resolution[1], GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
        SDL.SDL_GL_SwapWindow(event.window)
        #### END TEST CODE ####

        '''
        # Vertex data in SSBO, but OpenGL *REQUIRES* bound VBO
        #GL.glBindBuffer(GL.GL_ARRAY_BUFFER, event.blank_vbo)
        #GL.glBindVertexArray(event.blank_vao)

        # Actual draw code...
        # GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
        SDL.SDL_GL_SwapWindow(event.window)
        '''

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