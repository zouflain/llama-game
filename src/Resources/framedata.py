from __future__ import annotations
from .resource import Resource
import yaml

class FrameData(Resource):
    def __init__(self, name: str, permanent: bool = False):
        super().__init__(name, permanent)
        self.data = None

    @staticmethod
    async def allocate(name: str, permanent: bool, fname: str) -> FrameData:
        item = FrameData(name, permanent)
        item.data = yaml.safe_load(Resource.file_system().open(f"/framedata/{fname}"))
        await item.register()
        return item