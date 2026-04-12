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
import os
import OpenGL.GL as GL
from inspect import isclass
from enum import Enum, Flag, auto as EnumAuto
from typing import Callable

import Resources
import Events
import Systems
import Components


class FromSDL(Events.Event):
    def __init__(self, sdl_event, **kwargs):
        super().__init__(**kwargs)
        self.sdl_event = sdl_event

class Render(Events.Event):
    def __init__(self, dt: float, abs_time: float, time_step: float, window, resolution: tuple[int, int], render_size: tuple[int, int], framebuffer, view = None, **kwargs):
        '''Important rendering event'''
        super().__init__(**kwargs)
        self.dt: float = dt
        self.abs_time: float = abs_time
        self.time_step: float = time_step
        self.window: SDL.SDL_Window = window
        self.resolution: tuple[int, int] = resolution
        self.render_size: tuple[int, int] = render_size
        self.framebuffer: Resources.Framebuffer = framebuffer
        self.view = view

class Logic(Events.Event):
    def __init__(self, dt: float, abs_time: float, time_step: float, **kwargs):
        super().__init__(**kwargs)
        self.dt: float = dt
        self.abs_time: float = abs_time
        self.time_step: float = time_step

class GenerateEntity(Events.Event):
    def __init__(self, entity: int = None, **kwargs):
        super().__init__(**kwargs)
        self.entity = entity

class CameraUpdate(Events.Event):
    def __init__(self, distance: float = None, sharpness: float = None, target_center: np_array = None, **kwargs):
        self.target_center = target_center
        self.distance = distance
        self.sharpness = sharpness


class Player(Components.Component): pass

class Game:
    class Constants(int, Enum):
        RENDER_FPS = 200
        LOGIC_FPS = 50
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
        self.is_running = False
        self.screen_dimensions = (1440, 810)
        self.target_resolution = (1440, 810)
        self.main_fbo = None
        self.blank_vao = None
        self.packs = ["default"]
        self.joysticks = []

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
        SDL.SDL_InitSubSystem(SDL.SDL_INIT_GAMECONTROLLER)
        with open(os.path.join(getattr(sys, '_MEIPASS', os.getcwd()), "src", "Include","gamecontrollerdb.txt"), "rb") as mapfile:
            mappings = mapfile.read()
            SDL.SDL_GameControllerAddMappingsFromFile(mappings)
            for i in range(SDL.SDL_NumJoysticks()):
                self.joysticks.append(SDL.SDL_GameControllerOpen(i))

        #SDL.SDL_SetWindowMouseGrab(self.window, SDL.SDL_TRUE)
        SDL.SDL_GL_SetSwapInterval(0)



    async def boot(self) -> None:
        # Async & Post Init
        self.initWindow()
        Resources.init(self.packs)

        #schedule the Render pass
        self.scheduled_tasks.append(
            Game.ScheduledTask(
                Events.Render,
                Game.Constants.RENDER_FPS,
                window=self.window,
                resolution=self.screen_dimensions,
                render_size=self.target_resolution,
                framebuffer = await Resources.Framebuffer.allocate("main_fbo", False, self.target_resolution, 5)
            )
        )

        self.is_running = True

        #####TEST CODE#####
        await Resources.FrameData.generate(name="attacks", permanent=True, fname="attack_undefended.yaml")
        renderable = await Resources.Renderable.generate(name="mage", permanent=True, fname="models/Mage.Z3D", ftype="glb")
        tex = await Resources.GlyphSet.generate(name="font", permanent=True, file_list=["fonts/atlas2.png"])
        '''arr = tex.getArray(
            "This is a test\nThis is a really long line that might be a problem.\nThis isn't.\n123456789012345#ffacbc6789012345x\n1234567890##123456789*0*12345x\n1231456780123456789012345\n",
            1,
            (25, 5),
            (0,0,0)
        )'''

        print(Resources.FrameData["attacks"].data)
        await Resources.CombatAction.loadAllActions()
        await Systems.register(Systems.Battle(), render_size=self.target_resolution)
        await Systems.register(Systems.EntityController(150))
        await Systems.register(Systems.UserInterface(self.screen_dimensions))
        await Systems.register(Systems.CameraSystem())
        await Systems.register(Systems.AudioController())
        await Systems.register(Systems.GamepadController())
        
        await Systems.immediateEvent(Events.BattleBegin(arena_size=(10000,10000)))

        player_evt = await Systems.immediateEvent(Events.GenerateEntity())
        Components.Player(player_evt.entity)
        await Systems.immediateEvent(Events.SpawnCombatant(
            eid=player_evt.entity,
            party_id=player_evt.entity,
            mannequin="mage",
            active_meshes=[
                mesh for mesh in Resources.Renderable["mage"].meshes.keys() if mesh not in [
                    "Icosphere", "Spellbook", "Spellbook_open", "Mage_Hat",
                    "Mage_Cape", "2H_Staff", "1H_Wand"
                ]
            ]
        ))
        for i in range(2):
            enemy_evt = await Systems.immediateEvent(Events.GenerateEntity())
            await Systems.immediateEvent(Events.SpawnCombatant(
                eid=enemy_evt.entity,
                party_id=player_evt.entity+1,
                mannequin="mage",
                active_meshes=[
                    mesh for mesh in Resources.Renderable["mage"].meshes.keys() if mesh not in [
                        "Icosphere", "Spellbook", "Spellbook_open",# "Mage_Hat",
                        "Mage_Cape", "2H_Staff", "1H_Wand"
                    ]
                ]
            ))
            combatant = Components.Combatant[enemy_evt.entity]
            if i == 0:
                combatant.active_meshes.extend(["Icosphere", "Spellbook", "Spellbook_open"])

        #####END TEST CODE#####
        last_fps = time.monotonic()
        frame_count = 0

        while self.is_running:
            now = time.monotonic()
            delta = now - last_fps
            frame_count +=1
            if delta > 10:
                print(frame_count/delta)
                frame_count = 0
                last_fps = time.monotonic()

            # Handle events
            last_motion = None
            for event in SDLext.get_events():
                match event.type:
                    case SDL.SDL_QUIT:
                        self.is_running = False
                    case SDL.SDL_MOUSEMOTION:
                        last_motion = event
                    case SDL.SDL_MOUSEBUTTONDOWN | SDL.SDL_MOUSEBUTTONUP:
                        if last_motion:
                            Systems.raiseEvent(Events.FromSDL(last_motion))
                            last_motion = None
                        Systems.raiseEvent(Events.FromSDL(event))
                    case SDL.SDL_CONTROLLERBUTTONUP | SDL.SDL_CONTROLLERBUTTONDOWN | SDL.SDL_CONTROLLERDEVICEADDED | SDL.SDL_CONTROLLERDEVICEREMOVED | SDL.SDL_CONTROLLERAXISMOTION:
                        Systems.raiseEvent(Events.FromSDL(event))
                    # TODO: need keydowns, maybe others...
            if last_motion:
                Systems.raiseEvent(Events.FromSDL(last_motion))
            
            # Queue scheduled events
            for task in self.scheduled_tasks:
                # Start the timers if not already set
                if task.last_run is None:
                    task.last_run = now

                dt = now - task.last_run
                if dt >= 1.0/task.interval:
                    Systems.raiseEvent(task.event_type(dt=dt, abs_time=now, time_step=1./task.interval, **task.kwargs))
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
        await Systems.deinit()


if __name__ == "__main__":
    game = Game()
    asyncio.run(game.boot())