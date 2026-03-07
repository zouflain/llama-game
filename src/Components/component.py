from __future__ import annotations

class Component:
    __registry = {}

    def __init__(self, eid: int = None):
        self._eid = eid
        if eid is not None:
            self.assign(eid)

    def __init_subclass__(cls, **kwargs):
        if cls not in Component.__registry:
            Component.__registry[cls] = {}

    def __class_getitem__(cls, eid: int) -> Component:
        return Component.__registry[cls].get(eid)

    def assign(self, eid: int) -> None:
        Component.__registry[type(self)][eid] = self
        self._eid = eid

    @property
    def eid(self) -> int:
        return self._eid

    @classmethod
    def remove(cls, eid: int) -> None:
        if cls in Component.__registry:
            del Component.__registry[cls][eid]
    
    @classmethod
    def getAll(cls) -> list[Component]:
        return [(eid, entry) for eid, entry in Component.__registry[cls].items()]
    
    @staticmethod
    def matches(has: list, exclude: list = None) -> list[Component]:
        first_cls = has.pop()
        match_set = [eid for eid in Component.__registry[first_cls].keys()]
            
        for cls in has:
            new_set = match_set.copy()
            for eid in match_set:
                if eid not in Component.__registry[cls]:
                    new_set.remove(eid)
            match_set = new_set

            if len(match_set) == 0:
                break

        if len(match_set) > 0 and exclude:
            for cls in exclude:
                new_set = match_set.copy()
                for eid in match_set:
                    if eid in Component.__registry[cls]:
                        new_set.remove(eid)
                match_set=new_set
            
                if len(match_set) == 0:
                    break

        return match_set
    
    @staticmethod
    def assignMany(eid: int, components: list[Component]) -> None:
        for component in components:
            component.assign(eid)

    @staticmethod
    def deserialize(game) -> None:
        pass

    @staticmethod
    def serialize(game) -> None:
        pass


# Syntatic sugar
find = Component.matches