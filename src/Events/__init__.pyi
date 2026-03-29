from Events import Event
class FromSDL(Event):
'''None or '...''''
	def __init__(self, sdl_event, **kwargs):
'''...'''

class Render(Event):
'''None or '...''''
	def __init__(self, dt: float, abs_time: float, time_step: float, window, resolution: tuple[int, int], render_size: tuple[int, int], framebuffer, view=None, **kwargs):
'''Important rendering event'''

class Logic(Event):
'''None or '...''''
	def __init__(self, dt: float, abs_time: float, time_step: float, **kwargs):
'''...'''

class GenerateEntity(Event):
'''None or '...''''
	def __init__(self, entity: int=None, **kwargs):
'''...'''

class CameraUpdate(Event):
'''None or '...''''
	def __init__(self, distance: float=None, sharpness: float=None, target_center: np_array=None, **kwargs):
'''...'''

class UIEvent(Event):
'''None or '...''''
	def __init__(self, name: str, **kwargs):
'''...'''

class CombatTick(Event):
'''None or '...''''
	def __init__(self, dt: float, dilation: float=1, view=None, last_projection=None, last_resolution=None, **kwargs):
'''...'''

class CombatGUITick(Event):
'''None or '...''''
	def __init__(self, dt: float, view=None, projection=None, resolution=None):
'''...'''

class CombatManueverPhase(Event):
'''None or '...''''
	def __init__(self, dt: float, **kwargs):
'''...'''

class CombatantReady(Event):
'''None or '...''''
	def __init__(self, eid: int, **kwargs):
'''...'''

class SpawnCombatant(Event):
'''None or '...''''
	def __init__(self, eid: int, party_id: int, mannequin: str, active_meshes: list[str]):
'''...'''

class BattleBegin(Event):
'''None or '...''''
	def __init__(self, arena_size: tuple[int, int], seed: int=None, **kwargs):
'''...'''

class BattleEnd(Event):
'''None or '...''''
class AICombatantReady(Event):
'''None or '...''''
	def __init__(self, eid: int, **kwargs):
'''...'''

class PlayerCombatantReady(Event):
'''None or '...''''
	def __init__(self, eid: int, **kwargs):
'''...'''

class PlayerCombatantCommand(Event):
'''None or '...''''
	def __init__(self, eid: int, posture: int, target: int, **kwargs):
'''...'''

