from .event import Event

class Logic(Event):
    def __init__(self, dt: float, **kwargs):
        super().__init__(**kwargs)
        self.dt = dt