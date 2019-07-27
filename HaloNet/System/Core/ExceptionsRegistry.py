class ExceptionsRegistry:

    execptions_classes = dict()

    @classmethod
    def register(cls, exc):
        cls.execptions_classes[exc.__name__] = exc
        return exc

    @classmethod
    def find(cls, name):
        return cls.execptions_classes.get(name, None)


def RegisterExc(exc):
    return ExceptionsRegistry.register(exc)


class NetException(Exception):
    def __init_subclass__(cls, **kwargs):
        RegisterExc(cls)


# def GatherSystemExceptions():
#     import builtins
#
#     excs = dict([(name, cls) for name, cls in builtins.__dict__.items() if isinstance(cls, type) and issubclass(cls, Exception)])
#     for exc in excs.values():
#         RegisterExc(exc)
#
#
# GatherSystemExceptions()