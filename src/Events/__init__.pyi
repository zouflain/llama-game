from Events import Event
class FromSDL(Event):
	def __init__(self, sdl_event, **kwargs): ...

class Render(Event):
	def __init__(self, dt: float, window, resolution: tuple[int, int], render_size: tuple[int, int], framebuffer, **kwargs): '''Important rendering event'''

class Logic(Event):
	def __init__(self, dt: float, **kwargs): ...

class GenerateEntity(Event):
	def __init__(self, entity: int=None, **kwargs): ...

