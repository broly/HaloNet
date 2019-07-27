import asyncio
import json
import platform
import sys

# from Core import ERROR_MSG
from datetime import datetime
from functools import partial
from inspect import indentsize

# from Core.Logging import ASSERT_MSG, INFO_MSG, WARN_MSG, DEPR_MSG
from Core.intrinsic.Serialization import BinarySerialization

from Core.ConfigSystem.Bases import AppConfig
from Core.Globals import Globals


def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, datetime):
        return str(obj)
    raise TypeError


def is_valid(obj):
    return obj and hasattr(obj, '__isvalid__') and obj.__isvalid__()


def to_json(obj, **kwargs):
    return json.dumps(obj,  default=set_default, **kwargs)



class ConnectionMessageTypes:
    rmi_call = 0
    rmi_future = 1
    rmi_error = 2
    rmi_exception = 3


_debugbreak = lambda: None

def error(reason, err_type=AssertionError, depth=1, do_exit=False, do_break=False):
    from Core.Logging import ASSERT_MSG
    ASSERT_MSG(reason, depth=depth)
    if do_break:
        _debugbreak()
    if do_exit:
        sys.exit()
    raise err_type(reason)


def runnable(*args, **kwargs):
    def decorator(cls, depth=0):
        name = sys._getframe(1 + depth).f_locals['__name__']
        assert Globals.HaloNet_imported or error("Failed to run app, 'import HaloNet' must be placed to top of service file!")
        if name == "__main__":
            if hasattr(cls, "__run__"):
                arguments = kwargs.get('args', tuple())
                if 'with_context' in kwargs:
                    with kwargs['with_context']:
                        cls.__run__(*arguments)
                else:
                    cls.__run__(*arguments)
            else:
                print("%s is not runnable class" % cls)
        return cls

    if len(kwargs) == 0 and len(args) == 1 and hasattr(args[0], "__run__"):
        return decorator(args[0], 1)

    return decorator

def deprecated(message = None):
    def decorator(func):
        from Core.Logging import DEPR_MSG
        nonlocal message
        if message is None:
            message = "%s is deprecated" % func.__name__
        DEPR_MSG(message, depth=1)
        return func

    if callable(message):
        f = message
        message = None
        return decorator(f)

    return decorator


def extract_rmi_signature(func):
    variable_names = func.__code__.co_varnames
    typing = func.__annotations__
    defaults = func.__defaults__ if func.__defaults__ is not None else tuple()

    args_defaults = dict()
    for default_index, var_index in enumerate(range(len(variable_names) - len(defaults),
                                                    len(variable_names))):
        arg_name = variable_names[var_index]
        assert typing[arg_name].is_local_datatype or error("(%s) Only local datatypes can be default values" % arg_name, depth=3, do_exit=True)
        args_defaults[arg_name] = defaults[default_index]

    if 'self' not in variable_names:
        print("function %s has no 'self' variable, probably used incorrect method")

    var_list = list()
    for varname in variable_names:
        if varname in typing:
            utype = typing[varname]
            var_list.append((varname, utype))

    return_list = typing.get('return', ())
    if not isinstance(return_list, tuple):
        return_list = return_list,

    ret_list = list()
    for ret_type in return_list:
        ret_list.append(ret_type)

    return var_list, ret_list, args_defaults



async def make_default_service_mailbox(srv_name):
    from Core.Service import Service
    service_config = AppConfig.by_name[srv_name]
    if service_config is not None:
        service_context = service_config.Context
        if service_context is not None:
            default_endpoint = service_config.get_endpoint()
            if default_endpoint is not None:
                return await Service.make_mailbox(service_context, srv_name, default_endpoint)


def PyCharm_go_to(file, line):
    """ Opens an PyCharm if not opened and moves cursor to specified file and line """
    if platform.system() == 'Windows':
        from winreg import ConnectRegistry, OpenKey, EnumValue, HKEY_CLASSES_ROOT
        import subprocess

        reg = ConnectRegistry(None, HKEY_CLASSES_ROOT)

        raw_key = OpenKey(reg, r"Applications\pycharm.exe\shell\open\command")

        pycharm_path = ""
        try:
            i = 0
            while 1:
                name, pycharm_path, type = EnumValue(raw_key, i)
                if pycharm_path:
                    break
                i += 1
        except WindowsError:
            pass

        pycharm_path = pycharm_path.replace('"%1"', "").strip().strip('"')

        project_path = Globals.workspace

        pycharm_process = find_process_by_name("pycharm")
        if pycharm_process is not None:
            focus_window_by_pid(pycharm_process.pid)

        subprocess.Popen([pycharm_path, project_path, "--line", str(line), file])

EditorTCPClient = None

async def _async_UnrealEngine4_go_to(asset_path):
    global EditorTCPClient

    from Core.TCP.TestProtocolClient import create_connection
    if EditorTCPClient is None or not is_valid(EditorTCPClient):
        _, EditorTCPClient = await create_connection(("127.0.0.1", 6666), None)
    bs = BinarySerialization()
    bs << "open_asset"
    bs << asset_path
    EditorTCPClient.send(bs.get_archive())


def UnrealEngine4_go_to(asset_path):
    asyncio.get_event_loop().create_task(_async_UnrealEngine4_go_to(asset_path))

    ue4_process = find_process_by_name("ue4editor")
    if ue4_process:
        focus_window_by_pid(ue4_process.pid)


def focus_window_by_pid(pid):
    """ Focuses the window with specified process ID """
    from Core.Logging import WARN_MSG
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.AppActivate('Console2')
        shell.SendKeys('{UP}{ENTER}')
        shell.AppActivate(pid)
    except ImportError as e:
        WARN_MSG("Can't focus window: win32com not correctly installed:", e)


def find_process_by_name(process_name):
    """ Finds process by name """
    from Core.Logging import WARN_MSG
    try:
        import psutil

        for pid in psutil.pids():
            try:
                process = psutil.Process(pid)
                if process_name.lower() in process.name().lower():
                    return process
            except psutil.NoSuchProcess:
                pass

    except ImportError:
        WARN_MSG("Can't find process: psutil module not found")

    return None


def get_file_line(frame):
    return {'filename': frame.f_code.co_filename.replace("\\", '/').lower(),
            'line': frame.f_lineno}

linescache = dict()

def get_source(object, source_file):
    import inspect, linecache, re
    file = source_file
    if file:
        # Invalidate cache if needed.
        linecache.checkcache(file)
    else:
        file = inspect.getfile(object)
        # Allow filenames in form of "<something>" to pass through.
        # `doctest` monkeypatches `linecache` module to enable
        # inspection, so let `linecache.getlines` to be called.
        if not (file.startswith('<') and file.endswith('>')):
            raise OSError('source code not available')

    if file not in linescache:
        with open(file, 'r', encoding='utf-8') as f:
            data = f.read()
            lines = data.split("\n")

    else:
        lines = linescache[file]

    if inspect.ismodule(object):
        return lines, 0

    if inspect.isclass(object):
        name = object.__name__
        pat = re.compile(r'^(\s*)class\s*' + name + r'\b')
        # make some effort to find the best matching class definition:
        # use the one with the least indentation, which is the one
        # that's most probably not inside a function definition.
        candidates = []
        for i in range(len(lines)):
            match = pat.match(lines[i])
            if match:
                # if it's at toplevel, it's already the best one
                if lines[i][0] == 'c':
                    return lines, i
                # else add whitespace to candidate list
                candidates.append((match.group(1), i))
        if candidates:
            # this will sort by whitespace, and by line number,
            # less whitespace first
            candidates.sort()
            return lines, candidates[0][1]
        else:
            raise OSError('could not find class definition')

    if inspect.ismethod(object):
        object = object.__func__
    if inspect.isfunction(object):
        object = object.__code__
    if inspect.istraceback(object):
        object = object.tb_frame
    if inspect.isframe(object):
        object = object.f_code
    if inspect.iscode(object):
        if not hasattr(object, 'co_firstlineno'):
            raise OSError('could not find function definition')
        lnum = object.co_firstlineno - 1
        pat = re.compile(r'^(\s*def\s)|(\s*async\s+def\s)|(.*(?<!\w)lambda(:|\s))|^(\s*@)')
        while lnum > 0:
            if pat.match(lines[lnum]): break
            lnum = lnum - 1
        return lines, lnum
    raise OSError('could not find code object')



def get_annotation_comment_and_line_by_source(container_object, variable_name, source_file):
    try:
        lines, lnum = get_source(container_object, source_file)
    except (OSError, TypeError):
        return None

    i = 1
    while indentsize(lines[lnum + i]) == indentsize(lines[lnum]):
        i += 1

    if len(lines) > lnum and indentsize(lines[lnum + i]) > indentsize(lines[lnum]):
        this_cls_indentsize = indentsize(lines[lnum + i])

        l = lnum + i
        while l < len(lines):
            cur_indentsize = indentsize(lines[l])
            if cur_indentsize < this_cls_indentsize and lines[l].strip() != "":
                break

            if cur_indentsize == this_cls_indentsize:
                expr = lines[l].strip().replace(" ", "")
                if expr.startswith(variable_name + ":"):
                    lnum = l
                    break
            l += 1

    if lnum > 0:
        indent = indentsize(lines[lnum])
        end = lnum - 1
        if end >= 0 and lines[end].lstrip()[:1] == '#' and \
                        indentsize(lines[end]) == indent:
            comments = [lines[end].expandtabs().lstrip()]
            if end > 0:
                end = end - 1
                comment = lines[end].expandtabs().lstrip()
                while comment[:1] == '#' and indentsize(lines[end]) == indent:
                    comments[:0] = [comment]
                    end = end - 1
                    if end < 0: break
                    comment = lines[end].expandtabs().lstrip()
            while comments and comments[0].strip() == '#':
                comments[:1] = []
            while comments and comments[-1].strip() == '#':
                comments[-1:] = []
            return '\n'.join(comments), lnum
    return None, lnum


def get_uclass_name(uclass_path):
    if (uclass_path.lower().startswith("blueprint'") or uclass_path.lower().startswith("class'")) and uclass_path.endswith("'"):
        wo_literals_path = uclass_path[uclass_path.index("'") + 1: -1]
        name = wo_literals_path[wo_literals_path.rindex("/") + 1:]
        if '.' in name:
            name = name[name.rindex('.') + 1:]
        return name
    return ""


def get_uclass_true_path(uclass_path):
    if uclass_path.startswith("Blueprint'") and uclass_path.endswith("'"):
        true_path = uclass_path[10:-1] + "_C"
        return true_path


def has_access(player_access):
    pass

def get_retcode_descr(retcode):
    return {
        0: "Successfully done",
        1: "Closed by user or partial succeed",
        2: "Unrecognized command",
        3: "Has been crashed",
        0xC000013A: "Ctrl+C"
    }.get(retcode, "Unknown code")



class CodeMeta(type):
    def __matmul__(self, other):
        a = sys._getframe(1)
        a.f_locals['__gencode__'] = other


class CODE(metaclass=CodeMeta):
    """ Injects a code into USTRUCT for C++ """


def call_later(func, secs) -> asyncio.TimerHandle:
    new_func = func
    if asyncio.iscoroutinefunction(func) or isinstance(func, partial) and asyncio.iscoroutinefunction(func.func):
        new_func = lambda: asyncio.Task(func())
    return asyncio.get_event_loop().call_later(secs, new_func)


from cProfile import runctx
from time import time

def profile_it(func):
    def profiled(*args, **kwargs):
        nonlocal func
        runctx('func(*args, **kwargs)', globals(), locals())
    return profiled


async def async_profile_it(func):
    async def profiled(*args, **kwargs):
        nonlocal func
        runctx('await func(*args, **kwargs)', globals(), locals())
    return profiled

def time_it(func):
    def profiled(*args, **kwargs):
        t = time()
        func(*args, **kwargs)
        print(f"{func} called at {time() - t}")
    return profiled

def async_time_it(func):
    async def profiled(*args, **kwargs):
        t = time()
        res = await func(*args, **kwargs)
        print(f"async {func} called at {time() - t}")
        return res
    return profiled