import sys
import os
import ast
from pathlib import Path
from importlib import import_module
from importlib.util import spec_from_file_location, module_from_spec


import enum
import yaml


class Event:
    class Result(int, enum.Enum):
        CONTINUE = 1
        CONSUME = 0
        ABORT = -1

    def __init__(self, **kwargs):
        self._status: Result = Event.Result.CONTINUE

    def __init_subclass__(cls, **kwargs):
        event_tag = f"!{cls.__name__}"

        def constructor(loader, node):
            fields = loader.construct_mapping(node, deep=True)
            return cls(**fields)

        yaml.SafeLoader.add_constructor(event_tag, constructor)


### BOILER PLATE DYNAMIC PACKAGE ###
_CONTENT_MAP = {}
_INITIALIZED = False
_CLASS_NAME = "Event"

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
                        stub_lines.append(f"class {node.name}({_CLASS_NAME}):\n")
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
