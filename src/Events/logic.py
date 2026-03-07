from .event import Event

class Logic(Event):
    def __init__(self, dt: float, *args, **kwargs):
        super().__init__(args, *args, **kwargs)
        self.dt = dt