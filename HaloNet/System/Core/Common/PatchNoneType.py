import ctypes
import asyncio
from types import CoroutineType


class PyObject(ctypes.Structure):
    pass

Py_ssize_t = hasattr(ctypes.pythonapi, 'Py_InitModule4_64') and ctypes.c_int64 or ctypes.c_int

PyObject._fields_ = [
    ('ob_refcnt', Py_ssize_t),
    ('ob_type', ctypes.POINTER(PyObject)),
]

class SlotsPointer(PyObject):
    _fields_ = [('dict', ctypes.POINTER(PyObject))]


def proxy_builtin(cls):
    name = cls.__name__
    slots = getattr(cls, '__dict__', name)

    pointer = SlotsPointer.from_address(id(slots))
    namespace = {}

    ctypes.pythonapi.PyDict_SetItem(
        ctypes.py_object(namespace),
        ctypes.py_object(name),
        pointer.dict,
    )

    return namespace[name]


class __class:
    def wait_for(self, seconds):
        return asyncio.wait_for(self, seconds)


proxy_builtin(CoroutineType)['wait_for'] = __class.wait_for


def is_valid():
    return False

def run_NoneType_patch():
    proxy_builtin(None.__class__)['is_valid'] = is_valid
