from __future__ import annotations
from enum import Enum, auto as EnumAuto
from .resource import Resource
import yaml


class CombatAction(Resource):
    class HookResponse(int, Enum):
        SUCCESS = EnumAuto()
        FAILURE = EnumAuto()
        IGNORE = EnumAuto()


    def __init__(self, name: str, permanent: bool, definition: dict, **kwargs):
        super().__init__(name=name, permanent=permanent, **kwargs)
        self.__dict__.update(definition)

    async def onHook(self, eid: int, hook:str) -> CombatAction.HookResponse:
        result = CombatAction.HookResponse.IGNORE
        if hook in self.hooks:
            match hook:
                case _:
                    pass

        return result

    @staticmethod
    async def allocate(name: str, permanent: bool, definition: dict, **kwargs) -> Resource:
        item =  CombatAction(name, permanent, definition)
        await item.register()
        return item

    @staticmethod
    async def loadAllActions() -> list[str]:
        fs = Resource.file_system()
        for path in fs.walk.files("/actions/combat-actions/"):
            with fs.open(path, "r") as file:
                definitions = yaml.safe_load(file)
                for action in definitions.get("actions", []):
                    name = action.pop("name")
                    await CombatAction.generate(name=name, permanent=True, definition=action)
                