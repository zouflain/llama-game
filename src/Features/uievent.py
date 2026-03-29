import Events

class UIEvent(Events.Event):
    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self.name: str = name
        self.data: dict = kwargs