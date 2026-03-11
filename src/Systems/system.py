from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Iterator, Type
from enum import Enum
from Events import Event

class System:
    __active_systems: list[System] = []
    __pending_events: list[Event] = []
    __listener_cache: dict[Type[Event], list[System.Listner]] = defaultdict(list)

    @dataclass
    class Listener:
        priority: int
        callback: Callable[[Event, ...], bool]
        kwargs: dict = field(default_factory=dict)

        async def execute(self, event: Event) -> bool:
            return await self.callback(event=event, **self.kwargs)

    class Priority(int, Enum):
        HIGHEST = 100000
        DEFAULT = 10000
        LOWEST = 0


    def __init__(self, **kwargs):
        self.listeners = defaultdict(list)

        for name in dir(self):
            attr = getattr(self, name)
            if hasattr(attr, "_listener"):
                metadata = attr._listener
                self.addListener(metadata["cls"], metadata["priority"], attr, **metadata["kwargs"])

    @staticmethod
    def __recache(event_type: Type[Event]) -> None:
        listeners = [
            listener
            for system in System.__active_systems
            for listener in system.listeners.get(event_type, [])
        ]
        listeners.sort(key=lambda l: l.priority, reverse=True)
        System.__listener_cache[event_type] = listeners


    def addListener(self, cls: Type, priority: int, callback: Callable[[Event, ...], bool], **kwargs) -> None:
        self.listeners[cls].append(System.Listener(priority, callback, **kwargs))
        System.__recache(cls)

    @staticmethod
    def on(cls: Type[Event], priority: int, **kwargs):
        def decorator(callback: Callable[[Event, ...], bool]):
            callback._listener = {
                "cls": cls,
                "priority": priority,
                "kwargs": kwargs
            }
            return callback
        return decorator
        

    @staticmethod
    async def immediateEvent(event: Event) -> Event:
        for listener in System.__listener_cache[type(event)]:
            if await listener.execute(event):
                break

        return event

    @staticmethod
    def raiseEvent(event: Event) -> None:
        System.__pending_events.append(event)

    @staticmethod
    def yieldEvents() -> Iterator[Event]:
        while len(System.__pending_events) > 0:
            yield System.__pending_events.pop()

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

    async def boot(self, **kwargs) -> bool:
        return True

    async def unboot(self) -> None: pass


# Syntatic Sugar
raiseEvent = System.raiseEvent
immediateEvent = System.immediateEvent
yieldEvents = System.yieldEvents
register = System.register
unregister = System.unregister
