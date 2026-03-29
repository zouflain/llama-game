import numpy as np
from scipy.spatial.transform import Rotation
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
    class Relationship(int, Enum):
        SELF = 0
        TARGET = 1
        PARTY = 2
        NONPARTY = 3

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
        self.forward:np.array = np.array([1, 0, 0], dtype=np.float32)
        self.scale = 70
        self.frame = 0
        self.progress: float = 0
        self.progress_speed = 90.
        self.move_speed:float = 200.
        self.turn_speed:float = 360.
        self.size: float = 100
        self.status = Combatant.Status.MANUEVER
        self.posture = Combatant.Posture.AGGRESSIVE
        self.animations = [
            {
                "start_frame": self.frame,
                "end_frame": self.frame,
                "frame_coefficient": 1,
                "blend_coefficient": 1
            }
        ]

    @property
    def model(self) -> np.array:
        model = np.eye(4)
        model[:3, :3] = Rotation.from_euler('z', np.atan2(self.forward[1], self.forward[0]), degrees=False).as_matrix() * np.array([self.scale]*3)[np.newaxis, :]
        model[3, :3] = self.pos
        model[3, 3] = 1.0
        return model


class CombatTick(Events.Event):
    def __init__(self, dt: float, dilation: float = 1, view = None, last_projection = None, last_resolution = None, **kwargs):
        super().__init__(**kwargs)
        self.dt: float = dt
        self.dilation: float = dilation
        self.view = view
        self.projection = last_projection
        self.last_resolution = last_resolution


class CombatGUITick(Events.Event):
    def __init__(self, dt: float, view = None, projection = None, resolution = None):
        self.dt: float = dt
        self.view = view
        self.projection = projection
        self.resolution = resolution


class CombatManueverPhase(Events.Event):
    def __init__(self, dt: float, **kwargs):
        super().__init__(**kwargs)
        self.dt: float = dt

class CombatantReady(Events.Event):
    def __init__(self, eid: int, **kwargs):
        self.eid: int  = eid


class SpawnCombatant(Events.Event):
    def __init__(self, eid: int, party_id: int, mannequin: str, active_meshes: list[str]):
        self.eid: int = eid
        self.party_id: int = party_id
        self.combatant = None
        self.mannequin = mannequin
        self.active_meshes = active_meshes.copy()

class BattleBegin(Events.Event):
    def __init__(self, arena_size: tuple[int, int], seed: int = None, **kwargs):
        super().__init__(**kwargs)
        self.arena_size: tupe[int, int] = arena_size
        self.seed: int = seed

class BattleEnd(Events.Event):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class AICombatantReady(Events.Event):
    def __init__(self, eid: int, **kwargs):
        super().__init__(**kwargs)
        self.eid: int = eid

class PlayerCombatantReady(Events.Event):
    def __init__(self, eid: int, **kwargs):
        super().__init__(**kwargs)
        self.eid: int = eid

class PlayerCombatantCommand(Events.Event):
    def __init__(self, eid: int, posture: int, target: int, **kwargs):
        super().__init__(**kwargs)
        self.eid: int = eid
        self.posture: int = posture
        self.target = target