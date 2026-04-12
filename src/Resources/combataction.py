from __future__ import annotations
from enum import Enum, auto as EnumAuto
from .resource import Resource
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import yaml

class Hook(BaseModel):
    event: str
    fields: Optional[Dict[str, Any]] = None

class Requirements(BaseModel):
    require: List[str] = Field(default_factory=list)
    exclude: List[str] = Field(default_factory=list)

class Action(BaseModel):
    name: Optional[str] = None
    heirarchy: List[str] = Field(default_factory=list)
    posture: List[float] = Field(default_factory=list)
    animation: Optional[str] = None
    icon: Optional[str] = None
    hooks: Dict[str, List[Hook]] = Field(default_factory=dict)
    requirements: Requirements
    range: Optional[int] = float('inf')
    state: Optional[str] = None

class CombatAction(Resource):
    def __init__(self, name: str, permanent: bool, definition: Action, **kwargs):
        super().__init__(name=name, permanent=permanent, **kwargs)
        self.__dict__.update(definition.model_dump())

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
                for action_def in definitions.get("actions", []):
                    name = action_def["name"]
                    action = Action(**action_def)
                    await CombatAction.generate(name=name, permanent=True, definition=action)
                