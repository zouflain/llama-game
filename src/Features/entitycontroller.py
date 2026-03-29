import Systems, Events, Components, Resources


class EntityController(Systems.System):
    def __init__(self, current_entity: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.current_entity: int = current_entity

    @Systems.on(Events.GenerateEntity, Systems.Priority.LOWEST)
    async def generateEntity(self, event: Events.GenerateEntity) -> Events.Result:
        self.current_entity += 1
        event.entity = self.current_entity
        return event.result