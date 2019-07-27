import collections
import importlib.util
import json
import os
import os.path
import shutil
from collections import OrderedDict
from json import JSONEncoder
from os import listdir
from os.path import isfile, join
from pathlib import Path
import random

from jinja2 import Template

from Core.Access import AccessLevel
from Core.Common.Decay import get_decayed_docstring
from Core.ConfigSystem.GeneratorConfig import ConfigurationGenerator
from Core.ConfigSystem.Bases import ConfigGlobals, AppConfig, AppConfigType
from Core.Declarators.Specs import Exposed, Replicated, Persistent, BlueprintCallable, BlueprintType, Blueprintable, \
    AvailableEverywhere, Exec, Native, BlueprintNativeEvent, BlueprintImplementableEvent, Latent, Transactional, Local, \
    PartialRep_EXPERIMENTAL, DeferredReturn
from Core.Entity import Entity
from Core.Globals import Globals
from Core.Type import TypeBase, MailboxProxyDatatype, ArrayBase, MapBase, SetBase, StructBase, SubclassBase, EnumBase
from Core.Type import storage_list
from Core.Utils import error, to_json
import re


def get_latent_info(T, name):
    categories = {
        'FString': 'PC_String',
        'FName': 'PC_Name',
        'uint8': 'PC_Byte',
        'int32': 'PC_Int',
        'float': 'PC_Float',
        'bool': 'PC_Boolean',
        'FBytes': 'PC_Struct',
        'FText': 'PC_Text',
        'UClass*': 'PC_Class',
    }
    base = T.get_base()
    base_name = "nullptr"
    if base.__name__ in categories:
        category = categories[T.__name__]
    elif issubclass(base, StructBase):
        category = 'PC_Struct'
        base_name = base.__name__ + "::StaticStruct()"
    elif issubclass(base, SubclassBase):
        category = 'PC_Class'
    elif issubclass(base, EnumBase):
        category = 'PC_Byte'
        base_name = f'FindObject<UEnum>(ANY_PACKAGE, TEXT("{base.__name__}"), true)'
    elif issubclass(base, MailboxProxyDatatype):
        category = 'PC_Object'
        base_name = "U" + base.__name__ + "::StaticClass()"
    else:
        print("wrong", base_name, base)
    info = {
        "Name": name,
        "IsArray": str(issubclass(T, ArrayBase)).lower(),
        "IsMap": str(issubclass(T, MapBase)).lower(),
        "IsSet": str(issubclass(T, SetBase)).lower(),
        "BaseClass": base_name,
        "Category": category
    }
    return info

def parse_rmi_specifiers(method_ref):
    from Core.Specifiers import all_specifiers
    result = dict()
    for specifier_name, specifier_value in all_specifiers.items():
        result[specifier_name] = specifier_value in method_ref.rmi_specifiers['specifiers']
    return result


class CodeGen(object):
    """ Генератор файлов проекта """

    def __init__(self, generate_only_config=False):

        target_dir = ConfigGlobals.UE4GeneratorSourcePath  # ConfigurationCommon().get_globals()['ue4_src_gen_path']

        game_editor_module_path = ConfigGlobals.UE4GeneratorSourceEditorPath  # ConfigurationCommon().get_globals()['ue4_src_editor_gen_path']

        self.latent_functions_supported = ConfigGlobals.LatentFunctionsSupported  # ConfigurationCommon().get_globals()['latent_functions_supported']
        if self.latent_functions_supported and not game_editor_module_path:
            error("Failed to use latent functions. There are no game editor module specified", do_exit=True)




        self.target_dir = target_dir + "/Generated"
        self.target_editor_module_dir = (game_editor_module_path + "/Generated") if game_editor_module_path else None
        self.game_editor_module_name = ConfigGlobals.UE4EditorGameModuleName  #  ConfigurationCommon().get_globals()['ue4_game_editor_module_name']

        self.classes_info = dict()
        self.types_info = dict()
        self.enums_info = dict()
        self.storage_info = dict()

        wn_imported = Globals.HaloNet_imported
        Globals.HaloNet_imported = True

        self.generate_config()

        Globals.HaloNet_imported = wn_imported

        if not generate_only_config:
            if os.path.exists(self.target_dir):
                shutil.rmtree(self.target_dir)
            os.makedirs(self.target_dir)

            self.generate_entities_listings()
            self.generate_types_listing()

    def render_template(self, src, dst, **kwargs):
        """ Рендер темплейта из src в dst
            @param src путь к шаблону
            @param dst путь сохранения
            @param kwargs параметры шаблонизатору
        """
        with open(src, 'r', encoding='utf-8') as f:
            text = Template(f.read()).render(
                PROJECT_NAME="Viper",
                PROJECT_API="VIPER",
                **kwargs)

            path = os.path.abspath(dst)
            with open(path, "xb") as f:
                f.write(text.encode())

    def generate_config(self):
        """ Генерация специального конфига для контроля проекта
        """
        apps_mapping = AppConfig.context_by_name

        classes_info = OrderedDict()
        try:
            with open(ConfigurationGenerator().gen_info_filename, 'rb') as f:
                data = f.read().decode('utf-8')
                if data:
                    json_data = json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode(data)
                    classes_info = json_data.get("entities", None)
                    types_info = json_data.get("types", None)
                    assert classes_info is not None
        except FileNotFoundError:
            pass

        workspace = str(Path(os.getcwd()).parent)

        for ContextName in apps_mapping.values():
            path = workspace + "/Entities/" + ContextName
            try:
                onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
            except FileNotFoundError:
                onlyfiles = []

            for filename in onlyfiles:
                ClassName = filename.replace(".py", "")
                module_path = workspace + "/Entities/" + ContextName + "/" + filename
                spec = importlib.util.spec_from_file_location(ContextName + "." + ClassName, module_path)
                foo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(foo)
                cls = foo.__dict__.get(ClassName, None)
                if cls is not None:
                    if ClassName not in classes_info:
                        classes_info[ClassName] = dict()
                    # print(filename, ContextName, ClassName, Entity, dir(Entity))
                    entity_info = self.get_entity_info(cls, ContextName, False)
                    classes_info[ClassName].update(entity_info)

        for ClassName, ContextName in apps_mapping.items():
            if ClassName not in classes_info:
                classes_info[ClassName] = dict()
            filename = ClassName + ".py"
            module_path = workspace + "/Services/" + filename
            spec = importlib.util.spec_from_file_location("module.name", module_path)
            foo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(foo)
            cls: Entity = getattr(foo, ClassName, None)
            entity_info = self.get_entity_info(cls, ContextName, True)
            classes_info[ClassName].update(entity_info)

        for ContextName in apps_mapping.values():
            from Core.Service import Service
            if 'Service' not in classes_info:
                classes_info['Service'] = dict()
            entity_info = self.get_entity_info(Service, "base", True)
            entity_info["base"]['IsApplication'] = True
            entity_info["base"]['IsBasicServiceClass'] = True
            entity_info["base"]["Exposed"] = False
            classes_info['Service'].update(entity_info)

        structs = {name: t for name, t in TypeBase.all_types['types'].items() if getattr(t, 'is_struct_type', False)}
        types_info = dict()



        for typename, typedata in structs.items():
            doc_description, \
                (doc_warnings,), \
                (doc_cvars,) = get_decayed_docstring(typedata.__doc__,
                                                    simples=["warning"],
                                                    multiples=["cvar"])

            docstring_decay = {
                "Description": doc_description,
                "Vars": doc_cvars,
                "Warnings": doc_warnings,
            }

            types_info[typename] = {
                "Name": typename,
                "Kind": "Struct",
                "Fields": {fieldname: {"Name": field.__name__, "Default": typedata.defaults.get(fieldname, None)} for fieldname, field in typedata.fields},
                "InputParams": [field.__name__ + " In" + fieldname for fieldname, field in typedata.fields],
                "SetupParams": [(": " if i == 0 else ", ") + fieldname + "(%s)" % ("In" + fieldname) for i, (fieldname, field) in enumerate(typedata.fields)],
                "SetupDefaults": [(": " if i == 0 else ", ") + fieldname + "(%s)" % (field.generator_default()) for i, (fieldname, field) in enumerate(typedata.fields)],
                "Docstring": None if not typedata.__doc__ else [s.strip() for s in typedata.__doc__.split('\n')],
                "Specs": [] + (["BlueprintType"] if BlueprintType in typedata.specifiers else [])
                            + (["Blueprintable"] if Blueprintable in typedata.specifiers else []),
                "BlueprintType": BlueprintType in typedata.specifiers,
                "Blueprintable": Blueprintable in typedata.specifiers,
                "IsLocal": Local in typedata.specifiers,
                "PgSpec": typedata.pg_spec,
                "DocstringDecay": docstring_decay,
                "Signature": typedata.get_full_type_signature(),
                "InspectInfo": getattr(typedata, "inspect_info", None),
                "GeneratedCode": getattr(typedata, "__gencode__", None)
            }

        enums = {name: t for name, t in TypeBase.all_types['types'].items() if getattr(t, 'is_enum_type', False)}

        # types_info = dict()
        for typename, typedata in enums.items():
            members = dict()
            for fieldname in typedata.get_members().keys():

                UMETA = list()
                field_data = typedata.__annotations__[fieldname]
                if field_data.hidden:
                    UMETA.append("Hidden")
                if field_data.display_name:
                    UMETA.append("DisplayName = \"%s\"" % field_data.display_name)
                if field_data.tooltip:
                    UMETA.append("ToolTip = \"%s\"" % field_data.tooltip)


                members[fieldname] = {
                    'Value': typedata.values_specified.get(fieldname, None),
                    'UMETA': UMETA,
                }

            doc_description, \
                (doc_warnings,), \
                (doc_cvars,) = get_decayed_docstring(typedata.__doc__,
                                                     simples=["warning"],
                                                     multiples=["cvar"])

            docstring_decay = {
                "Description": doc_description,
                "Vars": doc_cvars,
                "Warnings": doc_warnings,
            }

            types_info[typename] = {
                "Name": typename,
                "Kind": "Enum",
                "Members": members,
                "Docstring": None if not typedata.__doc__ else [s.strip() for s in typedata.__doc__.split('\n')],
                "Specs": [] + (["BlueprintType"] if BlueprintType in typedata.specifiers else [])
                            + (["Blueprintable"] if Blueprintable in typedata.specifiers else []),
                "BlueprintType": BlueprintType in typedata.specifiers,
                "Blueprintable": Blueprintable in typedata.specifiers,
                "IsLocal": Local in typedata.specifiers,
                "PgSpec": typedata.pg_spec,
                "DocstringDecay": docstring_decay,
                "InspectInfo": getattr(typedata, "inspect_info", None),
                "GeneratedCode": getattr(typedata, "GeneratedCode", None)
            }

        local_types = {name: t for name, t in TypeBase.all_types['types'].items() if getattr(t, 'is_local_datatype', False)}
        for typename, typedata in local_types.items():
            types_info[typename] = {
                "Name": typename,
                "Kind": "Local",
                "Docstring": None if not typedata.__doc__ else [s.strip() for s in typedata.__doc__.split('\n')],
                "PgSpec": typedata.pg_spec,
                "InspectInfo": getattr(typedata, "inspect_info", None),
            }


        storage_info = dict()

        for st in storage_list:
            storage_info[st.name] = {
                "Name": st.name,
                "Type": st.type.__name__,
                "AvailableEverywhere": AvailableEverywhere in st.specifiers,
            }

        with open(ConfigurationGenerator().gen_info_filename, 'wb') as f:
            import hashlib
            import base64

            d = to_json({'entities': classes_info,
                         'types': types_info,
                         'storage': storage_info}).encode()
            if ConfigGlobals.UseVersionGeneratorSignature:
                ver = ConfigGlobals.Version.encode()
                self.generator_signature = base64.encodebytes(hashlib.md5(ver).digest()).decode().replace("\n", " ").replace("\r", " ").replace("\\", "/")
            else:
                self.generator_signature = base64.encodebytes(hashlib.md5(d).digest()).decode().replace("\n", " ").replace("\r", " ").replace("\\", "/")

            d = to_json({'entities': classes_info,
                         'types': types_info,
                         'storage': storage_info,
                         'signature': self.generator_signature}, indent=4, ensure_ascii=False).encode('utf8')
            f.write(d)

        self.classes_info = classes_info
        self.types_info = types_info
        self.storage_info = storage_info

    def get_entity_info(self, cls, ContextName, is_app):
        """ Получение информации о сущности
            @param cls: импортированный класс
            @param ContextName: имя контекста
            @param is_app: эта сущность - сервис?
            @return: информация в виде словаря
        """
        cls_info = dict()
        if cls is not None:
            if ContextName not in cls_info:
                cls_info[ContextName] = dict()
            methods = list()
            properties = list()


            for method_id, method_ref in cls.rmi_methods.items():
                # doc_description, doc_args, doc_returns, doc_warnings = get_docstring_data(method_ref.__doc__)
                doc_description, \
                    (doc_returns, doc_warnings), \
                    (doc_args,) = get_decayed_docstring(method_ref.__doc__,
                                                                     simples=["return", "warning"],
                                                                     multiples=["param"])
                docstring_decay = {
                    "Description": doc_description,
                    "Args": doc_args,
                    "Returns": doc_returns,
                    "Warnings": doc_warnings,
                }

                method_params, method_returns, method_defaults = method_ref.rmi_signature

                method_info = {
                    "ID": method_id,
                    "Name": method_ref.__name__,
                    # "Exposed": Exposed in method_ref.rmi_specifiers['specifiers'],
                    "Async": method_ref.rmi_specifiers['isasyncmethod'],
                    # "DeferredReturn": DeferredReturn in method_ref.rmi_specifiers['specifiers'],
                    # "BlueprintCallable": BlueprintCallable in method_ref.rmi_specifiers['specifiers'],
                    # "BlueprintNativeEvent": BlueprintNativeEvent in method_ref.rmi_specifiers['specifiers'],
                    # "BlueprintImplementableEvent": BlueprintImplementableEvent in method_ref.rmi_specifiers['specifiers'],
                    # "Latent": Latent in method_ref.rmi_specifiers['specifiers'],
                    # "Exec": Exec in method_ref.rmi_specifiers['specifiers'],
                    # "Native": Native in method_ref.rmi_specifiers['specifiers'],
                    "Category": method_ref.rmi_specifiers['kwspecifiers'].get("Category", "undefined"),
                    "Access": method_ref.rmi_specifiers['kwspecifiers'].get("access", AccessLevel.Internal),
                    "Docstring": method_ref.__doc__,
                    "Args": OrderedDict((sign[0], sign[1].get_type_name()) for sign in method_params),
                    "Defaults": OrderedDict((default_var_name, default_value) for default_var_name, default_value in method_ref.rmi_signature[2].items()),
                    "Defaults_generator": OrderedDict((name, T(method_defaults[name]).generator_value()) for name, T in method_params if name in method_defaults),
                    "DocstringDecay": docstring_decay,
                    "Returns": [sign.get_type_name() for sign in method_returns],
                    "InspectInfo": method_ref.inspect_info,
                }

                # todo: Is that good idea?
                rmi_specifiers = parse_rmi_specifiers(method_ref)
                method_info.update(rmi_specifiers)

                if Latent in method_ref.rmi_specifiers['specifiers']:
                    args = list()
                    rets = list()
                    for sign in method_params:
                        args.append(get_latent_info(sign[1], sign[0]))
                    for i, ret in enumerate(method_returns):
                        rets.append(get_latent_info(ret, 'RetVal%i' % (i + 1)))
                    method_info['LatentInfo'] = {
                        "Args": args,
                        "Returns": rets,
                    }
                methods.append(method_info)
            for property_name, property_meta in cls.properties.items():
                property_info = {
                    "Name": property_name,
                    "Type": property_meta.prop_type.__name__,
                    "Persistent": Persistent in property_meta,
                    "Replicated": Replicated in property_meta,
                    "PartialRep": PartialRep_EXPERIMENTAL in property_meta,
                    "Transactional": Transactional in property_meta,
                    "Default": property_meta.default,
                    "Comment": property_meta.comment,
                    "HasDefault": property_meta.has_default,
                    "Generic": {},
                    "InspectInfo": {
                        "filename": property_meta.source.lower().replace("\\", "/"),
                        "line": property_meta.line_number + 1,
                    }
                }
                if issubclass(property_meta.prop_type, MapBase):
                    property_info['Generic']['KT'] = property_meta.prop_type.base_key.get_type_name()
                    property_info['Generic']['KV'] = property_meta.prop_type.base_value.get_type_name()

                properties.append(property_info)
            cls_info[ContextName] = {
                "Doc": cls.__doc__,
                "Exposed": cls.is_exposed,
                "IsExecCapable": getattr(cls, 'is_exec_capable', False),
                "IsApplication": is_app,
                "BaseClass": getattr(cls, 'base_entity_class', None),
                "UsingClass": getattr(cls, 'using_class', None),
                "Methods": methods,
                "Properties": properties,
                "InspectInfo": getattr(cls, "inspect_info", None),
            }
        return cls_info

    def generate_entities_listings(self):
        """ Генерация листингов для сущностей
        """
        delegate_postfixes = ["", "_OneParam", "_TwoParams", "_ThreeParams", "_FourParams", "_FiveParams", "_SixParams",
                              "_SevenParams", "_EightParams", "_NineParams"]

        latent_functions = list()

        exposed_context_name = None
        for context_name, context_data in AppConfig.by_context.items():
            if context_data.IsExposed:
                exposed_context_name = context_name


        os.makedirs(self.target_dir + "/Entities/")

        ue4_exec_capable_classes = list()
        for entity_name, entity_data in self.classes_info.items():
            for context_name, entity_info in entity_data.items():
                if entity_info.get('IsExecCapable', False):
                    ue4_exec_capable_classes.append(entity_name + context_name.capitalize())

        ue4_classes_mapping = dict()
        global_includes = list()
        for entity_name, entity_data in self.classes_info.items():
            for context_name, entity_info in entity_data.items():
                context_info = AppConfig.by_context[context_name]
                is_exposed_context = context_info.IsExposed or context_info.IsExposedApp
                is_client_context = context_info.IsClient
                has_exposed_context = exposed_context_name in entity_data

                is_app = entity_info.get("IsApplication", False)
                is_basic_class = entity_info.get("IsBasicServiceClass", False)
                base_cls = entity_info.get("BaseClass", "INVALID")
                is_available_context = (is_exposed_context or is_client_context)
                if is_available_context and not is_basic_class:
                    context_path = self.target_dir + "/Entities/" + context_name
                    if not os.path.exists(context_path):
                        os.makedirs(context_path)


                    entity_fullname = (entity_name + context_name.capitalize()) if not is_app else entity_name
                    exec_capable = entity_info.get('IsExecCapable', False)

                    methods = dict()
                    properties = dict()
                    forwarded_types = list()
                    forwarded_includes = list()

                    for method_info in entity_info["Methods"]:
                        if method_info["Exposed"]:
                            name = method_info["Name"]
                            id = method_info["ID"]
                            exposed = method_info["Exposed"]
                            doc = method_info["Docstring"]
                            args = {argname: TypeBase.find_type(argtype).get_type_signature() for argname, argtype in method_info["Args"].items()}
                            defaults = method_info.get("Defaults_generator", {})
                            signed_args = {argname: TypeBase.find_type(argtype).get_full_type_signature() for argname, argtype in method_info["Args"].items()}

                            returns = [TypeBase.find_type(ret).get_type_signature() for ret in method_info["Returns"]]
                            returns_sig = [TypeBase.find_type(ret).get_full_type_signature() for ret in method_info["Returns"]]

                            for argtype in list(method_info["Args"].values()) + method_info["Returns"]:
                                if issubclass(TypeBase.find_type(argtype), MailboxProxyDatatype):
                                    T = TypeBase.find_type(argtype)
                                    forwarded_types.append("U" + T.simple_name)

                            # forwarded_types += ["U" + argtype for argtype in
                            #                         list(method_info["Args"].values()) + method_info["Returns"]
                            #                     if issubclass(TypeBase.find_type(argtype), MailboxProxyDatatype)]

                            for argtypename in list(method_info["Args"].values()) + method_info["Returns"]:
                                argtype = TypeBase.find_type(argtypename)
                                if issubclass(argtype, MailboxProxyDatatype):
                                    forwarded_includes.append((argtype.meta_context_name, argtype.meta_class_name + argtype.meta_context_name.capitalize()))
                            # forwarded_includes = list()
                            # print(forwarded_types)

                            # print([(TypeBase.find_type(ret).get_type_signature(), ret) for i, ret in enumerate(returns)])
                            # print(TypeBase.all_types)

                            if exposed or is_client_context:
                                methods[name] = {
                                    "ID": id,
                                    "Name": name,
                                    "BlueprintCallable": method_info['BlueprintCallable'],
                                    "Latent": method_info['Latent'],
                                    "SystemInternal": method_info['SystemInternal'],

                                    "BlueprintNativeEvent": method_info['BlueprintNativeEvent'],
                                    "BlueprintImplementableEvent": method_info['BlueprintImplementableEvent'],
                                    "Category": method_info['Category'],
                                    "Exec": method_info['Exec'],
                                    "Native": method_info['Native'],
                                    "Docstring": None if not doc else [s.strip() for s in doc.split('\n')],
                                    "params_list": [typename + " " + argname for argname, typename in args.items()],
                                    "params_list_with_defaults": [typename + " " + argname + (" = " + defaults[argname] if argname in defaults else "") for argname, typename in args.items()],
                                    "signature_params_list_with_defaults": [typename + " " + argname + (" = " + defaults[argname] if argname in defaults else "") for argname, typename in signed_args.items()],
                                    "signature_params_list": [typename + " " + argname for argname, typename in signed_args.items()],
                                    "params_names": [argname for argname in args.keys()],
                                    "delegate_postfix": delegate_postfixes[len(returns)],
                                    "delegate_retvals": [ret for ret in returns],
                                    "dynamic_delegate_retvals": [ret + ", " + "RetVal%i" % (i + 1) for i, ret in enumerate(returns)],
                                    "dynamic_delegate_retvals_decl": [ret + ", " + "RetVal%i" % (i + 1) for i, ret in enumerate(returns_sig)],
                                    "returns_list": [ret + " " + "RetVal%i" % (i + 1) for i, ret in enumerate(returns)],
                                    "ret_names": ["RetVal%i" % (i + 1) for i, ret in enumerate(returns)],
                                    "params_commas": [", " + typename + ", " + argname for argname, typename in args.items()],

                                    "is_async": method_info['Async'],
                                    "DeferredReturn": method_info['DeferredReturn'],


                                    "returns_list_result_def": [ret + " " + "InRetVal%i" % (i + 1) for i, ret in enumerate(returns)],
                                    "returns_list_result_decl": ["RetVal{0} = InRetVal{0}".format(i + 1) for i, ret in enumerate(returns)],
                                    "returns_list_result_call": ["result.RetVal%i" % (i + 1) for i, ret in enumerate(returns)],

                                    "owner_name": entity_name,
                                    "owner_fullname": entity_fullname,
                                    "latent_info": method_info['LatentInfo'] if 'LatentInfo' in method_info else None
                                }

                                if method_info['Latent']:
                                    latent_functions.append(methods[name])

                    if has_exposed_context:
                        for property_info in entity_data[exposed_context_name]['Properties']:
                            if property_info["Replicated"]:
                                properties[property_info['Name']] = property_info


                    dest = context_path + "/" + entity_name + context_name.capitalize() + "Mailbox.h"
                    self.render_template("../System/Core/CodeGen_templates/Mailbox.h", dest,
                                         FORWARDED_TYPES=set(forwarded_types),
                                         FORWARDED_INCLUDES=set(forwarded_includes),
                                         ENTITY_NAME=entity_name,
                                         ENTITY_FULLNAME=entity_fullname,
                                         EXEC_CAPABLE=exec_capable,
                                         CONTEXT_NAME=context_name.capitalize(),
                                         METHODS=methods,
                                         LATENT_SUPPORTED=self.latent_functions_supported)

                    global_includes.append("Entities/" + context_name + "/" + entity_name + context_name.capitalize() + "Mailbox.h")

                    dest = context_path + "/" + entity_name + context_name.capitalize() + "Mailbox.cpp"
                    self.render_template("../System/Core/CodeGen_templates/Mailbox.cpp", dest,
                                         FORWARDED_TYPES=set(forwarded_types),
                                         FORWARDED_INCLUDES=set(forwarded_includes),
                                         ENTITY_NAME=entity_name,
                                         ENTITY_FULLNAME=entity_fullname,
                                         EXEC_CAPABLE=exec_capable,
                                         CONTEXT_NAME=context_name.capitalize(),
                                         METHODS=methods,
                                         LATENT_SUPPORTED=self.latent_functions_supported)

                    if is_client_context:
                        dest = context_path + "/" + entity_name + context_name.capitalize() + "Interface.h"
                        self.render_template("../System/Core/CodeGen_templates/Interface.h", dest,
                                         FORWARDED_TYPES=forwarded_types,
                                         FORWARDED_INCLUDES=forwarded_includes,
                                         ENTITY_NAME=entity_name,
                                         ENTITY_FULLNAME=entity_fullname,
                                         CONTEXT_NAME=context_name.capitalize(),
                                         METHODS=methods,
                                         PROPERTIES=properties)

                        global_includes.append("Entities/" + context_name + "/" + entity_name + context_name.capitalize() + "Interface.h")

                        dest = context_path + "/" + entity_name + context_name.capitalize() + "Interface.cpp"
                        self.render_template("../System/Core/CodeGen_templates/Interface.cpp", dest,
                                         ENTITY_NAME=entity_name,
                                         FORWARDED_TYPES=set(forwarded_types),
                                         FORWARDED_INCLUDES=forwarded_includes,
                                         ENTITY_FULLNAME=entity_fullname,
                                         CONTEXT_NAME=context_name.capitalize(),
                                         METHODS=methods,
                                         PROPERTIES=properties)

                    generate_entity = False
                    generate_entity_file = (is_app or is_client_context and has_exposed_context)
                    # if is_app and not is_client_context and is_basic_class:
                    #     generate_entity_file = False
                    ent_data = dict()


                    # has_exposed_context = (exposed_context_name in entity_data)

                    if is_client_context and has_exposed_context and not is_app:
                        generate_entity = True
                        assert entity_info["BaseClass"] is not None
                        ent_data['is_actor_entity'] = False
                        if entity_info["BaseClass"].startswith("A"):
                            ent_data['is_actor_entity'] = True
                        elif entity_info["BaseClass"].startswith("U"):
                            ent_data['is_actor_entity'] = False
                        else:
                            raise AssertionError("Must starts with A or U")

                        assert entity_info["UsingClass"] is not None or error("there is no UsingClass for %s" % entity_name)

                        ent_data['using_class'] = entity_info["UsingClass"]

                        ue4_classes_mapping[entity_name] = entity_info["UsingClass"]

                    if generate_entity_file:
                        dest = context_path + "/" + entity_name + context_name.capitalize() + "Entity.h"
                        self.render_template("../System/Core/CodeGen_templates/Entity.h", dest,
                                             ENTITY_NAME=entity_name,
                                             BASE_CLASS=base_cls,
                                             FORWARDED_TYPES=set(forwarded_types),
                                             FORWARDED_INCLUDES=set(forwarded_includes),
                                             ENTITY_FULLNAME=entity_fullname,
                                             GENERATE_ENTITY=generate_entity,
                                             CONTEXT_NAME=context_name.capitalize(),
                                             EXPOSED_CONTEXT_NAME=exposed_context_name.capitalize(),
                                             ENTITY=ent_data,
                                             METHODS=methods,
                                             PROPERTIES=properties)

                        global_includes.append("Entities/" + context_name + "/" + entity_name + context_name.capitalize() + "Entity.h")

                        dest = context_path + "/" + entity_name + context_name.capitalize() + "Entity.cpp"
                        self.render_template("../System/Core/CodeGen_templates/Entity.cpp", dest,
                                             ENTITY_NAME=entity_name,
                                             FORWARDED_TYPES=set(forwarded_types),
                                             FORWARDED_INCLUDES=set(forwarded_includes),
                                             ENTITY_FULLNAME=entity_fullname,
                                             GENERATE_ENTITY=generate_entity,
                                             EXPOSED_CONTEXT_NAME=exposed_context_name.capitalize(),
                                             CONTEXT_NAME=context_name.capitalize(),
                                             ENTITY=ent_data,
                                             METHODS=methods,
                                             PROPERTIES=properties)
        storages = list()
        for storage in storage_list:
            storage_keys = dict()
            for key, value in storage.type.fields:
                if value.blueprint_atomic:
                    storage_keys[key] = value
            print(storage_keys)
            storages.append((storage.name, storage.type.__name__, AvailableEverywhere in storage.specifiers, storage_keys))

        self.render_template("../System/Core/CodeGen_templates/HaloNetCommon.h", self.target_dir + "/HaloNetCommon.h",
                             CLIENT_CLASSES_MAPPING=ue4_classes_mapping,
                             EXEC_CAPABLE_CLASSES=ue4_exec_capable_classes,
                             GENERATOR_SIGNATURE=self.generator_signature,
                             STORAGES=storages)
        self.render_template("../System/Core/CodeGen_templates/HaloNetCommon.cpp", self.target_dir + "/HaloNetCommon.cpp",
                             CLIENT_CLASSES_MAPPING=ue4_classes_mapping,
                             EXEC_CAPABLE_CLASSES=ue4_exec_capable_classes,
                             GENERATOR_SIGNATURE=self.generator_signature,
                             STORAGES=storages)

        self.render_template("../System/Core/CodeGen_templates/HaloNetClasses.h", self.target_dir + "/HaloNetClasses.h",
                             INCLUDES=[inc.replace('/', '/') for inc in global_includes])
        # self.render_template("../System/Core/CodeGen_templates/HaloNetClasses.cpp", self.target_dir + "/HaloNetClasses.cpp",
        #                      CLIENT_CLASSES_MAPPING=ue4_classes_mapping)


    def generate_types_listing(self):
        """ Генерация листинга для типов
        """
        context_path = self.target_dir


        dest = context_path + "/" + "HaloNetDataTypes.h"
        self.render_template("../System/Core/CodeGen_templates/HaloNetDataTypes.h", dest,
                             TYPES=self.types_info)
        dest = context_path + "/" + "HaloNetDataTypes.cpp"
        self.render_template("../System/Core/CodeGen_templates/HaloNetDataTypes.cpp", dest,
                             TYPES=self.types_info)