from Core.Utils import error
from Core.Property import PropertyMcs
from Core.Logging import INFO_MSG, ERROR_MSG, WARN_MSG

import asyncio

__author__ = "Broly"


def _isbase(dictionary):
    """ Проверка на то, что словарь принадлежит подклассу, а не главному классу AsyncObj """
    return dictionary.get('_base_flag', False)


class AsyncObjMcs(PropertyMcs):
    """
    Обработка ассершинов при неправильном использовании AsyncObj
    Обратите внимание, метакласс не меняет какую-либо логику создания классов, он лишь следит за созданием классов,
    обращая внимание пользователя на неправильное использование классов
    """
    def __new__(mcs, cls_name, bases, dictionary):

        assert not (not _isbase(dictionary) and '__init__' in dictionary) or \
               error("You can't overload __init__ in your AsyncObj subclass %s! Just use __ainit__ instead" % cls_name,
                     depth=2, do_exit=True)

        assert not (not _isbase(dictionary) and '__await__' in dictionary) or \
               error("You can't overload __await__ in your AsyncObj subclass %s! Not supported" % cls_name,
                     depth=2, do_exit=True)

        cls = super().__new__(mcs, cls_name, bases, dictionary)

        return cls


class AsyncObj(metaclass=AsyncObjMcs):
    """
    asynchronous object

    used asynchronously*

    Syntax:
    #>>>    async def func():                 #
    #>>>        async_obj = await AsyncObj()  # instatioation

    Use __ainit__ instead of __init__

    [*] Instatioation is only possible insde async methods
    """
    _base_flag = True  # flag-assertion: this class is not subclass (used in metaclass)

    def __init__(self, *args, **kwargs):
        """
        Standard constructor used for arguments pass
        Do not override. Use __ainit__
        """
        self.__storedargs = args, kwargs
        self.async_initialized = False

    async def __ainit__(self, *args, **kwargs):
        """ Async constructor """

    async def __apostinit__(self):
        """ Used after object asyncly created """

    async def __initobj(self):
        """ Crutch used for __await__ after spawning """
        assert not self.async_initialized or error("Unable to initialize twice!")
        self.async_initialized = True
        await self.__ainit__(*self.__storedargs[0], **self.__storedargs[1])
        await self.__apostinit__()
        return self

    def spawn(self):
        """ Спаун объекта без ожидания """
        asyncio.Task(self.__initobj())
        return self

    def __await__(self):
        return self.__initobj().__await__()

    def __isvalid__(self):
        """ Проверка на валидность асинхронного объекта """
        if not self.async_initialized:
            ERROR_MSG("Wrong object %s, not awaited" % self)
        return self.async_initialized

    def __bool__(self):
        return self.__isvalid__()

    def __del__(self):
        """ Calling __del__ calls async __adel__ later for async destruction actions """
        if self.async_initialized:
            INFO_MSG(f"Destroyed object {self}")
            asyncio.Task(self.__adel__())
        # else:
        #     ERROR_MSG("%s not awaited..." % self.__class__.__name__)

    async def __adel__(self):
        """ Async destructor """

    def __init_subclass__(cls, **kwargs):
        assert asyncio.iscoroutinefunction(cls.__ainit__) or error("'__ainit__' must be async", do_exit=True, depth=3)

    @property
    def async_state(self):
        if not self.async_initialized:
            return "[initialization pending]"
        return "[initialization done and successful]"
