from .event import Event

class GenerateEntity(Event):
    def __init__(self, entity: int = None, **kwargs):
        super().__init__(**kwargs)
        self.entity = entity
