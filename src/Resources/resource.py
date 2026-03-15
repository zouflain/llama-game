from __future__ import annotations
from abc import abstractmethod
import xml.etree.ElementTree as XML
import fs as FS
from fs.multifs import MultiFS
from fs.mountfs import MountFS
from fs.osfs import OSFS as OSFS

class Resource:
    __available_resources: dict = {}
    __file_system: MountFS = MountFS()
    
    def __init__(self, name: str, permanent: bool = False, **kwargs):
        self.name = name
        self.permanent = permanent

    def __init_subclass__(cls, **kwargs):
        if cls not in Resource.__available_resources:
            Resource.__available_resources[cls] = {}

    def __class_getitem__(cls, name: str) -> Resource:
        return Resource.__available_resources[cls].get(name) #TODO: should warn rather than silently return None

    @staticmethod
    def file_system() -> MountFS:
        return Resource.__file_system
        
    @staticmethod
    def init(packs: list[str]) -> None:
        mergers = {}
        for dir in packs:
            directory = f"packs/{dir}"
            try:
                pack_dir = OSFS(directory)
                with pack_dir.open("config.xml") as xml_file:
                    tree = XML.parse(xml_file)
                    root = tree.getroot()
                    for root_child in root:
                        if root_child.tag == "paths":
                            for resource_path in root_child:
                                tag = resource_path.tag
                                
                                if tag not in mergers:
                                    mergers[tag] = MultiFS()
                                    Resource.__file_system.mount(tag, mergers[tag])

                                resource_fs = FS.open_fs(f"{directory}/{resource_path.text}")
                                #Resource.__file_system.add_fs(f"{resource_path.tag}", resource_fs)
                                mergers[tag].add_fs(dir, resource_fs, priority=1)
            except Exception as err:
                print(err) #TODO handle better

    @staticmethod
    async def deinit() -> None:
        for cls, items in Resource.__available_resources.items():
            shallow = items.copy()
            for name, resource in shallow.items():
                await resource.deallocate()
    
    async def register(self) -> None:
        cls = type(self)
        if self.name in Resource.__available_resources[cls]:
            await Resource.__available_resources[cls][self.name].deallocate()
        Resource.__available_resources[cls][self.name] = self

    @classmethod
    async def generate(cls, **kwargs) -> Resource:
        return await cls.allocate(**kwargs)

    @staticmethod
    @abstractmethod
    async def allocate(cls, name: str, permanent: bool, **kwargs) -> Resource:
        pass

    async def deallocate(self) -> None:
        del Resource.__available_resources[type(self)][self.name]


# Syntatic sugar
init = Resource.init
file_system = Resource.file_system
deinit = Resource.deinit