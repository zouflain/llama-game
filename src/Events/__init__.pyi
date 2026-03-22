from Events import Event
class FromSDL(Event): '''None or '...''''
	def __init__(self, sdl_event, **kwargs): '''...'''

class Render(Event): '''None or '...''''
	def __init__(self, dt: float, abs_time: float, frequency: float, window, resolution: tuple[int, int], render_size: tuple[int, int], framebuffer, **kwargs): '''Important rendering event'''

class Logic(Event): '''None or '...''''
	def __init__(self, dt: float, abs_time: float, frequency: float, **kwargs): '''...'''

class GenerateEntity(Event): '''None or '...''''
	def __init__(self, entity: int=None, **kwargs): '''...'''

class CombatTick(Event): '''None or '...''''
	def __init__(self, dt: float, **kwargs): '''...'''

class CombatManueverPhase(Event): '''None or '...''''
	def __init__(self, dt: float, **kwargs): '''...'''

class SpawnCombatant(Event): '''None or '...''''
	def __init__(self, eid: int, party_id: int): '''...'''

class BattleBegin(Event): '''None or '...''''
class BattleEnd(Event): '''None or '...''''
