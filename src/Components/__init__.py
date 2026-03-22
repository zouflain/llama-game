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
        if eid is not None:
            Component.__registry[type(self)][eid] = self
            self._eid = eid
        # TODO: good place for a log warning
    
    def serialize(self) -> bytes:
        return cbor2.dumps(self, default=Component.serializationEncoder)

    @property
    def eid(self) -> int:
        return _eid

    @classmethod
    def remove(cls, eid: int) -> None:
        if cls in Component.__registry:
            if eid in Component.__registry[cls][eid]:
                Component.__registry[cls][eid]._eid = None
                del Component.__registry[cls][eid]
            # TODO: another place for a good warning
    
    @classmethod
    def getAll(cls) -> list[tuple[int, Component]]:
        return [(eid, entry) for eid, entry in Component.__registry[cls].items()]
    
    @staticmethod
    def matches(has: list, exclude: list = None) -> list[int]:
        matches = []
        if has:
            has_sets = [set(Component.__registry[cls].keys()) for cls in has]
            exclude_sets = [set(Component.__registry[cls].keys()) for cls in exclude or []]

            match_set = set.intersection(*has_sets)
            if exclude_sets:
                match_set -= set.union(*exclude_sets)

            matches = list(match_set)
            
        return matches

    
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


### BOILER PLATE DYNAMIC PACKAGE ###
import sys
import os
import ast
from pathlib import Path
from importlib import import_module
from importlib.util import spec_from_file_location, module_from_spec


_CONTENT_MAP = {}
_INITIALIZED = False
_CLASS_NAME = "Component"

def _discover():
    global _INITIALIZED
    if _INITIALIZED: return
    
    base_path = Path(getattr(sys, '_MEIPASS', os.path.join(os.getcwd(), "src")))
    stub_lines = [f"from {_CLASS_NAME}s import {_CLASS_NAME}\n"]
    for path in base_path.rglob("*.py"):
        if path.name.startswith("__"):
            continue
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if any(
                        (isinstance(base, ast.Name) and base.id == _CLASS_NAME)
                        or (isinstance(base, ast.Attribute) and base.attr == _CLASS_NAME) 
                        for base in node.bases
                    ):
                        _CONTENT_MAP[node.name] = path
                        stub_lines.append(f"class {node.name}({_CLASS_NAME}): '''{ast.get_docstring(node) or '...'}'''\n")
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                signature = ast.unparse(item.args) if hasattr(ast, 'unparse') else "self, **kwargs"
                                stub_lines.append(f"\tdef {item.name}({signature}): '''{ast.get_docstring(item) or '...'}'''\n\n")
                        
        except Exception:
            continue
    _INITIALIZED = True
    stub_path = Path(__file__).with_suffix(".pyi")
    with open(stub_path, "w", encoding="utf-8") as file:
        for line in stub_lines:
            file.write(line)

def __getattr__(name):
    _discover()
    
    if name not in _CONTENT_MAP:
        raise AttributeError(f"Module '{_CLASS_NAME}s' has no event named '{name}'")
    
    path = _CONTENT_MAP[name]
    spec = spec_from_file_location(name, str(path))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    
    cls = getattr(mod, name)
    globals()[name] = cls
    return cls

def __dir__():
    _discover()
    return list(globals().keys()) + list(_CONTENT_MAP.keys())
