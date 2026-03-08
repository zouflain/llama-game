PROFILE_MODE = True
GL_DEBUG_MODE = True


import OpenGL
if not GL_DEBUG_MODE:
    OpenGL.ERROR_CHECKING = False

import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API")

import asyncio
import functools
import sdl2 as SDL
import sdl2.ext as SDLext
import sqlite3 as SQL
import json as JSON
import time
import sys
import OpenGL.GL as GL
from inspect import isclass
from enum import Enum, auto
from typing import Callable

import Resources
import Events
import Systems
import Components

class Game:
    class Constants(int, Enum):
        RENDER_FPS = 200
        LOGIC_FPS = 10
        VSYNC_ON = 0
        MAX_LOGIC_TIME = 4


    class ScheduledTask:
        def __init__(self, event_type: type, interval: float, **kwargs):
            self.event_type = event_type
            self.kwargs = kwargs
            self.interval = float(interval)
            self.last_run = None


    def __init__(self):
        self.window = None
        self.gl_context = None
        self.resources = dict()
        self.is_running = False
        self.screen_dimensions = (1280, 720)
        self.target_resolution = (640, 360)
        self.blank_vao = None
        self.next_entity = 0
        self.file_system = None
        self.packs = ["default"]

        self.scheduled_tasks = [
            Game.ScheduledTask(Events.Logic, Game.Constants.LOGIC_FPS)
        ]


    def initWindow(self) -> None:
        SDL.SDL_Init(SDL.SDL_INIT_VIDEO)
        self.window = SDL.SDL_CreateWindow(
            b"Ember's End",
            SDL.SDL_WINDOWPOS_CENTERED,
            SDL.SDL_WINDOWPOS_CENTERED,
            self.screen_dimensions[0],
            self.screen_dimensions[1],
            SDL.SDL_WINDOW_SHOWN|SDL.SDL_WINDOW_OPENGL
        )

        # Init OpenGL Context within SDL
        SDL.video.SDL_GL_SetAttribute(SDL.video.SDL_GL_CONTEXT_MAJOR_VERSION, 4)
        SDL.video.SDL_GL_SetAttribute(SDL.video.SDL_GL_CONTEXT_MINOR_VERSION, 6)
        SDL.video.SDL_GL_SetAttribute(
            SDL.video.SDL_GL_CONTEXT_PROFILE_MASK,
            SDL.video.SDL_GL_CONTEXT_PROFILE_CORE
        )
        self.gl_context = SDL.SDL_GL_CreateContext(self.window)

        # Baseline OpenGL Settings
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_MULTISAMPLE)
        GL.glClearColor(0.15, 0.15, 0.15, 0.15)

        ## Vertices are drawn using SSBO's instead of VBOs, but openGL will not tolerate not having one bound
        self.blank_vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.blank_vao)

        # controllers
        SDL.SDL_InitSubSystem(SDL.SDL_INIT_JOYSTICK)

        #schedule the Render pass
        self.scheduled_tasks.append(Game.ScheduledTask(Events.Render, Game.Constants.RENDER_FPS, window=self.window, resolution=self.screen_dimensions))


    async def boot(self) -> None:

        self.initWindow()
        Resources.init(["default"])

        self.is_running = True

        #####TEST CODE#####
        #await Resources.Shader.generate(name="attacks", permanent=True, fname="attack_undefended.yaml")
        await Resources.FrameData.generate(name="attacks", permanent=True, fname="attack_undefended.yaml")
        #await Resources.Renderable.generate(name="mage", permanent=True, fname="models/Mage.daex", ftype="glb")
        #await Resources.Renderable.generate(name="mage", permanent=True, fname="models/Mage.glb", ftype="glb")
        await Resources.Renderable.generate(name="mage", permanent=True, fname="models/Mage.Z3D", ftype="glb")
        print(Resources.FrameData["attacks"].data)
        await Systems.register(Systems.Battle())
        player = Components.Character(self.next_entity)
        player = Components.PartyMember(self.next_entity)
        self.next_entity = self.next_entity + 1

        for char in Components.find([Components.Character, Components.PartyMember]):
            print(char)
        #####END TEST CODE#####

        while self.is_running:
            now = time.monotonic()

            # Handle events
            for event in SDLext.get_events():
                match event.type:
                    case SDL.SDL_QUIT:
                        self.is_running = False
                    case _:
                        Systems.raiseEvent(Events.FromSDL(event))

            # Queue scheduled events
            for task in self.scheduled_tasks:
                # Start the timers if not already set
                if task.last_run is None:
                    task.last_run = now

                dt = now - task.last_run
                if dt >= 1.0/task.interval:
                    Systems.raiseEvent(task.event_type(dt=dt, **task.kwargs))
                    task.last_run = now

            # Iterate over queued events
            for event in Systems.yieldEvents():
                await Systems.immediateEvent(event)

            # Yield CPU power
            await asyncio.sleep(0)

        # Clean all resources
        await self.onExit()

    async def onExit(self) -> None:
        await Resources.deinit()


if __name__ == "__main__":
    game = Game()
    asyncio.run(game.boot())