from .event import Event

class FromSDL(Event):
    def __init__(self, sdl_event, *args, **kwargs):
        super().__init__(args, *args, **kwargs)
        self.sdl_event = sdl_event