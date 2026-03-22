import numpy as np
from enum import Enum, auto as EnumAuto
import Systems, Events, Components, Resources


class Combatant(Components.Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.actions = {
            "pending": None, # action to be performed upon crossing act threshold
            "prepared": None, # action clears upon crossing prep threshold, but can trigger
            "performing": None
        }


class BattleAnimator(Components.Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elapsed_time = None
        self.frame_data = None


class Combatant(Components.Component):
    class Status(int, Enum):
        MANUEVER = EnumAuto()
        ACT = EnumAuto()
        LOCKED = EnumAuto()

    class Posture(int, Enum):
        EVASIVE = 0 # Ignore Target, Ignore Allies, evade enemies (eg to evade damage)
        AGGRESSIVE = 1 # Ignore Allies, approach enemies (eg to be positioned to attack)
        DEFENSIVE = 2 # Ignore enemies, approach allies (eg to be positioned for defense)
        PASSIVE = 3

    def __init__(self, party_id: int, body, eid: int = None, pos: np.ndarray[tuple[float, float, float]] = np.zeros(3, dtype=np.float32), mannequin: str = None, active_meshes: list[str] = None, **kwargs):
        super().__init__(eid, **kwargs)
        self.body = body
        self.party_id: int = party_id
        self.pos: np.ndarray[tuple[float, float, float]] = pos
        self.mannequin: str = mannequin
        self.active_meshes: list[str] = active_meshes or []
        self.target: int = None
        self.action = None
        self.facing = 0
        self.scale = 70
        self.frame = 0
        self.speed = 100
        self.size:float = 100
        self.status = Combatant.Status.MANUEVER
        self.posture = Combatant.Posture.AGGRESSIVE
        self.progress: float = 0
        self.animations = [
            {
                "start_frame": self.frame,
                "end_frame": self.frame,
                "frame_coefficient": 1,
                "blend_coefficient": 1
            }
        ]


class Character(Components.Component): pass


class CombatTick(Events.Event):
    def __init__(self, dt: float, **kwargs):
        super().__init__(**kwargs)
        self.dt: float = dt


class CombatManueverPhase(Events.Event):
    def __init__(self, dt: float, **kwargs):
        super().__init__(**kwargs)
        self.dt: float = dt


class SpawnCombatant(Events.Event):
    def __init__(self, eid: int, party_id: int):
        self.eid: int = eid
        self.party_id: int = party_id
        self.combatant = None

class BattleBegin(Events.Event): pass

class BattleEnd(Events.Event): pass