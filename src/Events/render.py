from .event import Event

class Render(Event):
    def __init__(self, dt: float, window, resolution: tuple[int, int], render_size: tuple[int, int], framebuffer, **kwargs):
        super().__init__(**kwargs)
        self.dt = dt
        self.window = window
        self.resolution = resolution
        self.render_size = render_size
        self.framebuffer = framebuffer