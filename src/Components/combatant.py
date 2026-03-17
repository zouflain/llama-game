from .component import Component
import cbor2
import numpy as np


class Combatant(Component):
    def __init__(self, eid: int = None, pos: np.ndarray[tuple[float, float, float]] = np.zeros(3, dtype=np.float32), mannequin: str = None, active_meshes: list[str] = None, **kwargs):
        super().__init__(eid, **kwargs)
        self.pos: np.ndarray[tuple[float, float, float]] = pos
        self.mannequin: str = mannequin
        self.active_meshes: list[str] = active_meshes or []
        self.target: int = None
        self.action = None
        self.facing = 0
        self.scale = 70
        self.frame = 739
        self.animations = [
            {
                "start_frame": self.frame,
                "end_frame": self.frame,
                "frame_coefficient": 1,
                "blend_coefficient": 1
            }
        ]
        
