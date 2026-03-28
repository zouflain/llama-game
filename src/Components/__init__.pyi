from Components import Component
class Player(Component): '''...'''
class Combatant(Component): '''...'''
	def __init__(self, **kwargs): '''...'''

class BattleAnimator(Component): '''...'''
	def __init__(self, **kwargs): '''...'''

class Combatant(Component): '''...'''
	def __init__(self, party_id: int, body, eid: int=None, pos: np.ndarray[tuple[float, float, float]]=np.zeros(3, dtype=np.float32), mannequin: str=None, active_meshes: list[str]=None, **kwargs): '''...'''

	def model(self): '''...'''

class Character(Component): '''...'''
