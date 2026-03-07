import yaml

class Event:
    def __init__(self, *args, **kwargs):
        pass

    def __init_subclass__(cls, **kwargs):
        event_tag = f"!{cls.__name__}"

        def constructor(loader, node):
            fields = loader.construct_mapping(node, deep=True)
            return cls(**fields)

        yaml.SafeLoader.add_constructor(event_tag, constructor)
    