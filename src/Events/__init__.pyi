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

class GamepadChange(Event):
'''None or '...''''
	def __init__(self, changes: dict, **kwargs):
'''...'''

class AudioTrigger(Event):
'''None or '...''''
	def __init__(self, fmod_event: str, eid: int=0, playback: PlaybackType=PlaybackType.FIRE_AND_FORGET, parameters: dict=None, **kwargs):
'''...'''

class AudioParameters(Event):
'''None or '...''''
	def __init__(self, fmod_event: str, eid: int, parameters: dict):
'''...'''

class UISnapMouse(Event):
'''None or '...''''
	def __init__(self, center: dict=None, **kwargs):
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
	def __init__(self, **kwargs):
'''...'''

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
	def __init__(self, eid: int, action: str, target: int, **kwargs):
'''...'''

class CombatActionComplete(Event):
'''None or '...''''
	def __init__(self, eid: int, **kwargs):
'''...'''

class CombatDamage(Event):
'''None or '...''''
	def __init__(self, eid: int, target: int, **kwargs):
'''...'''

