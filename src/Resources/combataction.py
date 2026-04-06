from __future__ import annotations
from enum import Enum, auto as EnumAuto
from .resource import Resource
import yaml


class CombatAction(Resource):
    def __init__(self, name: str, permanent: bool, definition: dict, **kwargs):
        super().__init__(name=name, permanent=permanent, **kwargs)
        self.__dict__.update(definition)

    def onHook(self, hook:str) -> list[tuple[str, dict]]:
        return [
            (data.get("event"), data.get("fields") or {})
            for data in self.hooks.get(hook, [])
        ]

    @staticmethod
    async def allocate(name: str, permanent: bool, definition: dict, **kwargs) -> Resource:
        item =  CombatAction(name, permanent, definition)
        await item.register()
        return item

    @staticmethod
    async def loadAllActions() -> list[str]:
        fs = Resource.file_system()
        for path in fs.walk.files("/actions/combat-actions/"):
            print(path)
            with fs.open(path, "r") as file:
                definitions = yaml.safe_load(file)
                for action in definitions.get("actions", []):
                    name = action.pop("name")
                    await CombatAction.generate(name=name, permanent=True, definition=action)
                