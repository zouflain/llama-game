from __future__ import annotations
from enum import Enum
from copy import deepcopy, copy
import sdl2 as SDL
import Components, Resources, Events, Systems

class GamepadChange(Events.Event):
    def __init__(self, changes: dict, **kwargs):
        super().__init__(**kwargs)
        self.changes: dict = changes

class GamepadController(Systems.System):
    MAX_JOYAXIS_VALUE = 32767
    BASE_DEADZONE = 8000
    MIN_JOYAXIS_DELTA = 0.05
    
    def __init__(self, deadzone: int = BASE_DEADZONE, **kwargs):
        super().__init__(**kwargs)
        self.states: dict = {
            "A": False,
            "B": False,
            "X": False,
            "Y": False,
            "L1": False,
            "L2": 0,
            "L3": False,
            "R1": False,
            "R2": 0,
            "R3": False,
            "START": False,
            "SELECT": False,
            "PAD_U": False,
            "PAD_R": False,
            "PAD_D": False,
            "PAD_L": False,
            "STICK_L": {"x": 0, "y": 0},
            "STICK_R": {"x": 0, "y": 0}
        }
        self.last_report = deepcopy(self.states)
        self.deadzone: int = deadzone

    @Systems.on(Events.Logic, Systems.Priority.HIGHEST)
    async def onLogic(self, event: Events.Logic) -> Events.Result:
        changes = {}
        for button, value in self.states.items():
            if type(value) == bool and self.last_report[button] != value:
                    changes[button] = value
            elif type(value) == float and abs(self.last_report[button] - value) > GamepadController.MIN_JOYAXIS_DELTA:
                    changes[button] = value
            elif type(value) == dict:
                if abs(self.last_report[button]["x"] - value["x"])+abs(self.last_report[button]["y"] - value["y"]) > GamepadController.MIN_JOYAXIS_DELTA: #manhattan distance is good enough
                    changes[button] = copy(value)

        if len(changes) > 0:
            self.last_report = deepcopy(self.states)
            await Systems.immediateEvent(Events.GamepadChange(changes=changes))
        return event.result

    @Systems.on(Events.FromSDL, Systems.Priority.LOWEST)
    async def onSDLEvent(self, event: Events.FromSDL) -> Events.Result:
        match event.sdl_event.type:
            case SDL.SDL_CONTROLLERDEVICEADDED:
                SDL.SDL_GameControllerOpen(event.sdl_event.cdevice.which)
            case SDL.SDL_CONTROLLERDEVICEREMOVED:
                which = SDL.SDL_GameControllerFromInstancedID(event.sdl_event.cdevice.which)
                if which:
                    SDL.SDL_GameControllerClose(which)
            case SDL.SDL_CONTROLLERAXISMOTION:
                match event.sdl_event.caxis.axis:
                    case SDL.SDL_CONTROLLER_AXIS_LEFTX | SDL.SDL_CONTROLLER_AXIS_LEFTY | SDL.SDL_CONTROLLER_AXIS_RIGHTX | SDL.SDL_CONTROLLER_AXIS_RIGHTY:
                        stick = None
                        axis = None
                        invert = 1
                        match event.sdl_event.caxis.axis:
                            case SDL.SDL_CONTROLLER_AXIS_LEFTX:
                                stick = "STICK_L"
                                axis = "x"
                            case SDL.SDL_CONTROLLER_AXIS_LEFTY:
                                stick = "STICK_L"
                                axis = "y"
                                invert = -1
                            case SDL.SDL_CONTROLLER_AXIS_RIGHTX:
                                stick = "STICK_R"
                                axis = "x"
                            case SDL.SDL_CONTROLLER_AXIS_RIGHTY:
                                stick = "STICK_R"
                                axis = "y"
                                invert = -1
                        value = event.sdl_event.caxis.value
                        if value < -self.deadzone or value > self.deadzone:
                            sign = 1 if value > 0 else -1
                            value = sign*(abs(value)-self.deadzone)/float(GamepadController.MAX_JOYAXIS_VALUE-self.deadzone)
                        else:
                            value = 0
                        
                        if stick and axis:
                            self.states[stick][axis] = invert * value
                    case SDL.SDL_CONTROLLER_AXIS_TRIGGERLEFT | SDL.SDL_CONTROLLER_AXIS_TRIGGERRIGHT:
                        trigger = None
                        match event.sdl_event.caxis.axis:
                            case SDL.SDL_CONTROLLER_AXIS_TRIGGERLEFT:
                                trigger = "L2"
                            case SDL.SDL_CONTROLLER_AXIS_TRIGGERRIGHT:
                                trigger = "R2"
                        value = event.sdl_event.caxis.value
                        if value > self.deadzone:
                            value = (value - self.deadzone)/float(GamepadController.MAX_JOYAXIS_VALUE-self.deadzone)
                        else:
                            value = 0
                        
                        if trigger:
                            self.states[trigger] = value
            case SDL.SDL_CONTROLLERBUTTONDOWN | SDL.SDL_CONTROLLERBUTTONUP:
                button = None
                state = False
                match event.sdl_event.type:
                    case SDL.SDL_CONTROLLERBUTTONDOWN:
                        state = True
                    case SDL.SDL_CONTROLLERBUTTONUP:
                        state = False

                match event.sdl_event.cbutton.button:
                    case SDL.SDL_CONTROLLER_BUTTON_A:
                        button = "A"
                    case SDL.SDL_CONTROLLER_BUTTON_B:
                        button = "B"
                    case SDL.SDL_CONTROLLER_BUTTON_X:
                        button = "X"
                    case SDL.SDL_CONTROLLER_BUTTON_Y:
                        button = "Y"
                    case SDL.SDL_CONTROLLER_BUTTON_BACK:
                        button = "SELECT"
                    case SDL.SDL_CONTROLLER_BUTTON_START:
                        button = "START"
                    case SDL.SDL_CONTROLLER_BUTTON_DPAD_UP:
                        button = "PAD_U"
                    case SDL.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                        button = "PAD_R"
                    case SDL.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                        button = "PAD_D"
                    case SDL.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                        button = "PAD_L"
                    case SDL.SDL_CONTROLLER_BUTTON_LEFTSTICK:
                        button = "L3"
                    case SDL.SDL_CONTROLLER_BUTTON_RIGHTSTICK:
                        button = "R3"
                    case SDL.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:
                        button = "L1"
                    case SDL.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:
                        button = "R1"
                        
                if button:
                    self.states[button] = state

        return event.result