from .system import System
import Events, Components, Resources


class EntityController(System):
    def __init__(self, current_entity: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.current_entity: int = current_entity

    @System.on(Events.GenerateEntity, System.Priority.LOWEST)
    async def generateEntity(self, event: Events.GenerateEntity) -> bool:
        self.current_entity += 1
        event.entity = self.current_entity
        return False