from __future__ import annotations
from collections import defaultdict
from enum import Enum
import numpy as np
import cbor2
import zlib

class Component:
    __registry: defaultdict = defaultdict(dict)
    __tag_to_class: dict = {}
    __class_to_tag: dict = {}

    class SpecialTag(int, Enum):
        NP_ARRAY = 40

    def __init__(self, eid: int = None):
        self._eid: int = eid
        if eid is not None:
            self.assign(eid)

    def __init_subclass__(cls, **kwargs):
        if cls not in Component.__registry:
            Component.__registry[cls] = {}

        if cls not in Component.__class_to_tag:
            tag = (zlib.adler32(cls.__name__.encode()) & 0xffffffff) + 100000
            Component.__tag_to_class[tag] = cls
            Component.__class_to_tag[cls] = tag
            

    def __class_getitem__(cls, eid: int) -> Component:
        return Component.__registry[cls].get(eid)

    def assign(self, eid: int) -> None:
        Component.__registry[type(self)][eid] = self
        self._eid = eid
    
    def serialize(self) -> bytes:
        return cbor2.dumps(self, default=Component.serializationEncoder)

    @property
    def eid(self) -> int:
        return _eid

    @classmethod
    def remove(cls, eid: int) -> None:
        if cls in Component.__registry:
            del Component.__registry[cls][eid]
    
    @classmethod
    def getAll(cls) -> list[tuple[int, Component]]:
        return [(eid, entry) for eid, entry in Component.__registry[cls].items()]
    
    @staticmethod
    def matches(has: list, exclude: list = None) -> list[int]:
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
    @cbor2.shareable_encoder
    def serializationEncoder(encoder, value) -> None:
        if isinstance(value, Component):
            encoder.encode(
                cbor2.CBORTag(
                    Component.__class_to_tag[type(value)],
                    {key: value for key, value in value.__dict__.items() if key == "_eid" or not key.startswith("_")}
                )
            )
        elif isinstance(value, np.ndarray):
            encoder.encode(cbor2.CBORTag(Component.SpecialTag.NP_ARRAY, (value.dtype.str, value.shape, value.tobytes())))
        else:
            encoder.encode(value)

    @staticmethod
    def serializationDecoder(decoder, tag):
        cls = Component.__tag_to_class.get(tag.tag)
        if cls:
            component = cls.__new__(cls)
            component.__dict__.update(tag.value)
            component.assign(component._eid)
            return component
        
        match tag.tag:
            case Component.SpecialTag.NP_ARRAY:
                dtype, shape, raw = tag.value
                return np.frombuffer(raw, dtype=dtype).reshape(shape)
        return tag

    @staticmethod
    def deserialize(data) -> Component:
        return cbor2.loads(data, tag_hook=Component.serializationDecoder)


# Syntatic sugar
find = Component.matches