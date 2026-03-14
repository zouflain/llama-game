from enum import Enum
import yaml


class Event:
    class Result(int, Enum):
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
    