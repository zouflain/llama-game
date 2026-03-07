from .event import Event

class Render(Event):
    def __init__(self, dt: float, window, resolution: tuple[float, float], blank_vao: int, blank_vbo: int, *args, **kwargs):
        super().__init__(args, *args, **kwargs)
        self.dt = dt
        self.window = window
        self.blank_vao = blank_vao
        self.blank_vbo = blank_vbo
        self.resolution = resolution