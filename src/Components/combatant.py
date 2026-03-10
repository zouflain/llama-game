from .component import Component
import numpy as np

class Combatant(Component):
    def __init__(self, eid: int = None, pos: np.ndarray[tuple[float, float, float]] = np.zeros(3, dtype=np.float32), mannequin: str = None, active_meshes: list[str] = None, **kwargs):
        super().__init__(eid, **kwargs)
        self.pos: pos
        self.mannequin: str = mannequin
        self.active_meshes: list[str] = active_meshes or []

