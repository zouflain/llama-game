import numpy as np
from scipy.spatial.transform import Rotation
from enum import Flag, Enum, auto as EnumAuto
import Systems, Events, Components, Resources


class CombatDamage(Events.Event):
    def __init__(self, eid: int, target: int, **kwargs):
        super().__init__(**kwargs)
        self.eid = eid
        self.target = target

class BeginStagger(Events.Event):
    def __init__(self, eid: int, source: int = None, **kwargs):
        super().__init__(**kwargs)
        self.eid: int = eid
        self.source: int = source

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
    def __init__(self, eid: int, action: str, target: int, **kwargs):
        super().__init__(**kwargs)
        self.eid: int = eid
        self.action: str = action
        self.target = target


class CombatActionComplete(Events.Event):
    def __init__(self, eid: int, **kwargs):
        super().__init__(**kwargs)
        self.eid = eid