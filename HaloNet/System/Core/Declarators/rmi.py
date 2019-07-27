import sys
from asyncio import iscoroutinefunction
from functools import partial

import asyncio

from Core import WARN_MSG, INFO_MSG
from Core.Declarators.Specs import CaptureConnection, Native, Latent, BlueprintCallable, Exposed, CaptureAccessToken, \
    WithTimeout, Exec, DeferredReturn, BlueprintNativeEvent, BlueprintImplementableEvent
from Core.Type import make_mailbox_proxy, pythonic_types_mapping
from Core.Utils import extract_rmi_signature, error, get_file_line


def reduce_classes_list(lst, context_name):
    from Core.Entity import Entity
    for i, item in enumerate(lst):
        if issubclass(item, Entity):
            lst[i] = make_mailbox_proxy(context_name, item.__name__)

        if item in pythonic_types_mapping:
            WARN_MSG("Used python type '%s' instead '%s' (replaced)" % (item.__name__, pythonic_types_mapping[item].__name__),
                     depth=2,
                     warning_id="TYPE_NEGLECT")
            lst[i] = pythonic_types_mapping[item]


def reduce_classes_pairs(lst, context_name):
    from Core.Entity import Entity
    for i, item in enumerate(lst):
        if issubclass(item[1], Entity):
            lst[i] = lst[i][0], make_mailbox_proxy(context_name, item[1].__name__)

        if item[1] in pythonic_types_mapping:
            WARN_MSG("Used python type '%s' instead '%s' (replaced)" % (item[1].__name__, pythonic_types_mapping[item[1]].__name__),
                     depth=2,
                     warning_id="TYPE_NEGLECT")
            lst[i] = lst[i][0], pythonic_types_mapping[item[1]]


FUNC_CODE_WITH_DOC = b'd\x01S\x00'
FUNC_CODE_PURE = b'd\x00S\x00'

acceptable_pure_code = FUNC_CODE_PURE, FUNC_CODE_WITH_DOC


def rmi(*specifiers, access=None, category=None, meta=None, timeout=None):
    """
    @param specifiers:
    @param kwspecifiers:
    @param access: what the access for this function used
    @param category: the category for BP an something else
    @param timeout: timeout of call of this function (with raising asyncio.TimeoutError if time passed, automatically adds the 'WithTimeout' specifier)
    @return:
    """
    def decorator(method):
        nonlocal specifiers
        frame_info = sys._getframe(1)

        # assert iscoroutinefunction(method) or error("rmi must be coroutine! Mark method as 'async'")
        assert Native not in specifiers or error("'Native' not supported", depth=2, do_exit=True)
        if Latent in specifiers and BlueprintCallable not in specifiers:
            error("'Latent' functions must be 'BlueprintCallable'", depth=2, do_exit=True)
        if BlueprintCallable in specifiers and (BlueprintNativeEvent in specifiers or BlueprintImplementableEvent in specifiers):
            error("BlueprintCallable can't be BlueprintNativeEvent or BlueprintImplementableEvent")
        if BlueprintCallable in specifiers and Exposed not in specifiers:
            error("'BlueprintCallable' functions must be 'Exposed'", depth=2, do_exit=True)
        if Exec in specifiers and Exposed not in specifiers:
            error("'Exec' functions must be 'Exposed'", depth=2, do_exit=True)
        if timeout is not None and WithTimeout not in specifiers:
            specifiers += (WithTimeout,)
        if WithTimeout in specifiers and timeout is None:
            error("'WithTimeout' should be accompanied with 'timeout=secs' keyword argument", depth=2, do_exit=True)
        if WithTimeout in specifiers and not iscoroutinefunction(method):
            error("Timeout methods must be 'async'")
        outer_class_dict = frame_info.f_locals
        context_name = outer_class_dict.get('context_name', "Unknown")
        var_list, return_list, vars_defaults = extract_rmi_signature(method)
        reduce_classes_pairs(var_list, context_name)
        reduce_classes_list(return_list, context_name)

        new_method = method

        if WithTimeout in specifiers:
            raise NotImplementedError()
            # async def timeout_method(*args, **kwargs):
            #     return await asyncio.wait_for(method(*args, **kwargs), timeout)
            # new_method = lambda *args, **kwargs:
            # new_method.__name__ = method.__name__

        for _, var in var_list:
            assert var.is_validated() or error(f"{var} is not validated. Please make validate_container for this type in Types.py", do_exit=True, depth=2)

        for ret in return_list:
            assert ret.is_validated() or error(f"{ret} is not validated. Please make validate_container for this type in Types.py", do_exit=True, depth=2)

        if (outer_class_dict.get('is_client_side', False) or outer_class_dict.get('base_entity_class', None)) and method.__code__.co_code not in acceptable_pure_code:
            error("Code not allowed. Use \"\"\"docstrings\"\"\", \"pass\" or \"...\" instead ", depth=2, do_exit=True)

        assert (len(method.__annotations__) - ('return' in method.__annotations__)) ==  \
               (method.__code__.co_argcount - 1 - int(CaptureConnection in specifiers) - int(CaptureAccessToken in specifiers)) \
                    or error("Invalid signature!", depth=2, do_exit=True)

        if not iscoroutinefunction(method) and ('return' in method.__annotations__):
            error("rmi with return values must be coroutines! Mark method as 'async'", depth=2, do_exit=True)

        new_method.is_rmi = True

        kwspecs = dict()
        if category is not None: kwspecs['Category'] = category
        if access is not None:   kwspecs['access'] = access

        new_method.rmi_specifiers = dict(specifiers=specifiers,
                                     kwspecifiers=kwspecs,
                                     isasyncmethod=iscoroutinefunction(method),
                                     meta=meta)
        new_method.rmi_signature = var_list, return_list, vars_defaults
        new_method.get_meta = lambda: meta
        new_method.inspect_info = get_file_line(frame_info)

        if 'methods_to_register' not in outer_class_dict:
            outer_class_dict['methods_to_register'] = list()
        outer_class_dict['methods_to_register'].append(new_method)

        return new_method

    if len(specifiers) == 1 and callable(specifiers[0]):
        return decorator(specifiers[0])

    return decorator


def isrmi(method):
    return getattr(method, 'is_rmi', False)
