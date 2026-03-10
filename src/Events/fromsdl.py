from .event import Event

class FromSDL(Event):
    def __init__(self, sdl_event, **kwargs):
        super().__init__(**kwargs)
        self.sdl_event = sdl_event