import sys
import os
import ast
from pathlib import Path
from importlib import import_module
from importlib.util import spec_from_file_location, module_from_spec


import enum
import yaml


class Event:
    __registry: dict = {}

    class Result(int, enum.Enum):
        FINISHED = enum.auto() # All listeners allowed continue
        CONTINUE = enum.auto() # Currently processing
        CONSUME = enum.auto() # A listener prevented others
        ABORT = enum.auto() # A listener prevented others, reporting failure
        TERMINATE = enum.auto() # a listener is allowing others, but reports failure

    def __init__(self, **kwargs):
        self._result: Result = Event.Result.CONTINUE

    def __init_subclass__(cls, **kwargs):
        event_tag = f"!{cls.__name__}"

        def constructor(loader, node):
            fields = loader.construct_mapping(node, deep=True)
            return cls(**fields)

        yaml.SafeLoader.add_constructor(event_tag, constructor)

    @staticmethod
    def get(name: str) -> Event:
        return Event.__registry.get(name)
        
    @property
    def result(self) -> Event.Result:
        return self._result

    def setResult(self, result: Event.Result) -> None: #Done for explictness (also logging?)
        self._result = result


# Syntatic Sugar
Result = Event.Result
get = Event.get


### BOILER PLATE DYNAMIC PACKAGE ###
_CLASS = Event
_CLASS_NAME = _CLASS.__name__
_CONTENT_MAP = {}
_FILE_CACHE = set()
_INITIALIZED = False

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
                        stub_lines.append(f"class {node.name}({_CLASS_NAME}):\n    '''{ast.get_docstring(node)} or '...''''\n")
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                signature = ast.unparse(item.args) if hasattr(ast, 'unparse') else "self, **kwargs"
                                stub_lines.append(f"    def {item.name}({signature}):\n        '''{ast.get_docstring(item) or '...'}'''\n\n")
                        
        except Exception:
            continue
    _INITIALIZED = True
    stub_path = Path(__file__).with_suffix(".pyi")
    with open(stub_path, "w", encoding="utf-8") as file:
        for line in stub_lines:
            file.write(line)

def __getattr__(name):
    global _FILE_CACHE
    _discover()

    if name not in _CONTENT_MAP:
        raise AttributeError(f"Module '{_CLASS_NAME}s' has no {_CLASS_NAME} named '{name}'")

    path = _CONTENT_MAP[name]
    if path not in _FILE_CACHE:
        _FILE_CACHE.add(path)
        namespace = set(globals().keys())
        with open(path, "r") as file:
            exec(compile(file.read(), str(path), 'exec'), globals())
        
        for key in set(globals().keys()) - namespace:
            obj = globals()[key]
            if isinstance(obj, type) and issubclass(obj, _CLASS) and obj is not _CLASS:
                obj.__module__ = __name__
                Event._Event__registry[key] = obj
            else:
                del globals()[key]
    return globals().get(name)
        
def __dir__():
    _discover()
    return list(globals().keys()) + list(_CONTENT_MAP.keys())
