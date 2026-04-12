import numpy as np
from scipy.spatial.transform import Rotation
from enum import Flag, Enum, auto as EnumAuto
import Components


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
    class TargetFlags(Flag):
        SAME_PARTY = EnumAuto()
        ALIVE = EnumAuto()

    class Relationship(int, Enum):
        SELF = 0
        TARGET = 1
        PARTY = 2
        NONPARTY = 3

    class Status(int, Enum):
        MANUEVER = EnumAuto() # Can move
        ACT = EnumAuto() # Has chosen action
        EXECUTE = EnumAuto() # Is executing action
        LOCKED = EnumAuto() # Hitstun
        STANDBY = EnumAuto() # Has chosen standby action

    def __init__(self, party_id: int, body, eid: int = None, pos: np.ndarray[tuple[float, float, float]] = np.zeros(3, dtype=np.float32), mannequin: str = None, active_meshes: list[str] = None, **kwargs):
        super().__init__(eid, **kwargs)
        # Logic
        self.party_id: int = party_id
        self.target: int = None
        self.status: Combatant.Status = Combatant.Status.MANUEVER
        self.posture: tuple[float, float, float, float] = [0, 0, -0.15, 1] # defensive
        self.default_posture: tuple[float, float, float, float] = [0, 0, -0.15, 1] # evasive
        self.available_actions: list[str] = ["Strike", "Escort", "Fireball", "Quick Strike"]
        self.stagger: float = 0
        self.action = None

        # Data
        self.body = body
        self.pos: np.ndarray[tuple[float, float, float]] = pos
        self.forward:np.array = np.array([1, 0, 0], dtype=np.float32)
        self.scale = 70
        self.progress: float = 0
        self.progress_speed = 90.
        self.move_speed:float = 400.
        self.turn_speed:float = 360.
        self.size: float = 100

        # Render details
        self.mannequin: str = mannequin
        self.active_meshes: list[str] = active_meshes or []
        self.frame = 0
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
