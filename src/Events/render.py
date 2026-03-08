from .event import Event

class Render(Event):
    def __init__(self, dt: float, window, resolution: tuple[float, float], *args, **kwargs):
        super().__init__(args, *args, **kwargs)
        self.dt = dt
        self.window = window
        self.resolution = resolution