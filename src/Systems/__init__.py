from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Iterator, Type
from enum import Enum
from Events import Event


class Priority(int, Enum):
    HIGHEST = 100000
    DEFAULT = 1000
    LOWEST = 0

class System:
    __active_systems: list[System] = []
    __pending_events: list[Event] = []
    __listener_cache: dict[Type[Event], list[System.Listner]] = defaultdict(list)
    __suppressed_systems: set[tuple[Type, Type]] = set()

    @dataclass
    class Listener:
        system: System
        priority: int
        callback: Callable[[Event, ...], Event.Result]
        kwargs: dict = field(default_factory=dict)

        async def execute(self, event: Event) -> Event.Result:
            return await self.callback(event=event, **self.kwargs)


    def __init__(self, **kwargs):
        self.listeners = defaultdict(list)

        for name in dir(self):
            attr = getattr(self, name)
            if hasattr(attr, "_listener"):
                metadata = attr._listener
                self.addListener(metadata["event"], metadata["priority"], attr, **metadata["kwargs"])

    @staticmethod
    def __recache(event_type: Type[Event]) -> None:
        listeners = [
            listener
            for system in System.__active_systems
            for listener in system.listeners.get(event_type, [])
        ]
        listeners.sort(key=lambda l: l.priority, reverse=True)
        System.__listener_cache[event_type] = listeners


    def addListener(self, event: Type, priority: int, callback: Callable[[Event, ...], bool], **kwargs) -> None:
        self.listeners[event].append(System.Listener(self, priority, callback, **kwargs))
        System.__recache(event)

    @staticmethod
    def on(event: Type[Event], priority: int, **kwargs):
        def decorator(callback: Callable[[Event, ...], bool]):
            callback._listener = {
                "event": event,
                "priority": priority,
                "kwargs": kwargs
            }
            return callback
        return decorator
        

    @staticmethod
    async def immediateEvent(event: Event) -> Event:
        event.setResult(Event.Result.CONTINUE)
        for listener in System.__listener_cache[type(event)]:
            if (type(event), type(listener.system)) in System.__suppressed_systems:
                continue

            event.setResult(await listener.execute(event))
            match event.result:
                case Event.Result.ABORT | Event.Result.CONSUME:
                    break
                case Event.Result.CONTINUE:
                    pass # for now, eventually log it!
        else:
            if event.result == Event.Result.CONTINUE:
               event.setResult(Event.Result.FINISHED)

        return event

    @staticmethod
    def raiseEvent(event: Event) -> None:
        System.__pending_events.append(event)

    @staticmethod
    def yieldEvents() -> Iterator[Event]:
        while len(System.__pending_events) > 0:
            yield System.__pending_events.pop(0)

    @staticmethod
    async def register(system: System, **kwargs) -> bool:
        result = False
        if system not in System.__active_systems:
            result = await system.boot(**kwargs)
            if result:
                System.__active_systems.append(system)
                for event_type in system.listeners.keys():
                    System.__recache(event_type)
        return result

    @staticmethod
    async def unregister(system: System) -> None:
        System.__active_systems.remove(system)
        await system.unboot()
        for event_type in system.listeners.keys():
            System.__recache(event_type)

    @staticmethod
    def suppress(event: Type, system: Type) -> None:
        System.__suppressed_systems.add((event, system))

    @staticmethod
    def unsuppress(event: Type, system: Type) -> None:
        System.__suppressed_systems.remove((event, system))

    @staticmethod
    async def deinit() -> None:
        for system in System.__active_systems:
            await system.unboot()

    async def boot(self, **kwargs) -> bool:
        return True

    async def unboot(self) -> None: pass


# Syntatic Sugar
raiseEvent = System.raiseEvent
immediateEvent = System.immediateEvent
yieldEvents = System.yieldEvents
register = System.register
unregister = System.unregister
on = System.on
suppress = System.suppress
unsuppress = System.unsuppress
deinit = System.deinit


### BOILER PLATE DYNAMIC PACKAGE ###
import sys
import os
import ast
from pathlib import Path
from importlib import import_module
from importlib.util import spec_from_file_location, module_from_spec


_CONTENT_MAP = {}
_INITIALIZED = False
_CLASS = System
_CLASS_NAME = _CLASS.__name__

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
                        stub_lines.append(f"class {node.name}({_CLASS_NAME}):\n    '''{ast.get_docstring(node) or '...'}'''\n")
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
    _discover()
    
    if name not in _CONTENT_MAP:
        raise AttributeError(f"Module '{_CLASS_NAME}s' has no {_CLASS_NAME} named '{name}'")
    
    if name not in globals():
        path = _CONTENT_MAP[name]
        spec = spec_from_file_location(name, os.fspath(path))
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)

        for attr in dir(mod):
            cls = getattr(mod, attr)
            if isinstance(cls, type) and issubclass(cls, _CLASS) and cls is not _CLASS:
                globals()[attr] = cls
    return globals()[name]
    
def __dir__():
    _discover()
    return list(globals().keys()) + list(_CONTENT_MAP.keys())
