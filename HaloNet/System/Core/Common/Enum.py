from Core.Declarators.Specs import Hidden
from Core.Property import PropertyMcs


class EnumMember():
    def __init__(self, *specs, DisplayName=None, ToolTip=None):
        self.hidden = Hidden in specs
        self.display_name = DisplayName
        self.tooltip = ToolTip


def member(*args, **kwargs):
    return EnumMember(*args, **kwargs)



class EnumMeta(PropertyMcs):
    classes = dict()

    def __new__(mcs, class_name, bases, class_dict, *args, **kwargs):

        annotations = class_dict.get("__annotations__", None)
        value_counter = 0
        if annotations:

            res = super().__new__(mcs, class_name, bases, class_dict, **kwargs)
            res._names = dict()
            mcs.classes[class_name] = res

            value_names = getattr(res, "_names", dict())
            values_specified = dict()

            for member_name, member_info in annotations.items():
                if member_info is Ellipsis:
                    annotations[member_name] = member()

                member_value = class_dict.get(member_name, None)

                if member_value is None:
                    member_value = value_counter
                else:
                    values_specified[member_name] = member_value
                    value_counter = member_value

                value_names[member_value] = member_name
                value = res(member_value)
                setattr(res, member_name, value)

                value_counter += 1

            setattr(res, "_names", value_names)
            res.values_specified = values_specified

            return res

        return super().__new__(mcs, class_name, bases, class_dict, **kwargs)

    def __iter__(cls):
        return getattr(cls, 'get_members')().values().__iter__()

    def __contains__(cls, item):
        result = item in cls.__iter__()
        if not result:
            result = item in cls._names.values()
        return result


    @property
    def __members__(cls):
        return list(cls.get_members().values())

    def __matmul__(cls, other):
        if isinstance(other, int):
            return cls.__members__[other]
        return getattr(cls, other)


class IntEnum(int, metaclass=EnumMeta):
    def __new__(cls, arg=None):
        if arg is None:
            arg = list(cls.get_members().keys())[0]

        if isinstance(arg, str):
            if arg in cls.get_members():
                value = getattr(cls, arg)
                return super().__new__(cls, value)

        return super().__new__(cls, arg)

    def __init__(self, arg=None):
        if isinstance(arg, (int, IntEnum)):
            int.__init__(arg)

        if isinstance(arg, str):
            if arg in self.get_members():
                self.__init__(getattr(self, arg))
                return

        if arg is None:
            value = list(self.get_members().keys())[0]
            self.__init__(getattr(self, value))
            return


        if arg not in self._names:
            raise TypeError("Enumeration has no value %i" % arg)

    @classmethod
    def get_members(cls):
        return {name: getattr(cls, name) for name in cls.__annotations__.keys()}

    def __repr__(self):
        return "<%s value %s (%s)>" % (self.__class__.__name__, self._names[self], int.__repr__(self))

    def __str__(self):
        return '"%s"' % self._names[int(self)]