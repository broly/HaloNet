from Core.Type import TypeBase
from Core.Type import make_mailbox_proxy
from Core.Utils import error


class MethodInfo():
    def __init__(self, method_info, context_name):
        self.id = method_info['ID']
        self.is_async = method_info['Async']
        self.name = method_info['Name']
        self.exposed = method_info['Exposed']
        self.context_name = context_name
        self.args = list()
        for argname, argtype in method_info['Args'].items():
            if argtype in TypeBase.all_types['types']:
                type = TypeBase.all_types['types'][argtype]
                self.args.append((argname, type))
            else:
                self.args.append((argname, make_mailbox_proxy("NoContext", "Unknown")))
        self.returns = list()
        for rettype in method_info['Returns']:
            if rettype in TypeBase.all_types['types']:
                type = TypeBase.all_types['types'][rettype]
                self.returns.append(type)
            else:
                self.returns.append(make_mailbox_proxy("NoContext", "Unknown"))

        self.signature = self.args, self.returns

    def __repr__(self):
        return f"<MethodInfo '{self.name}' id={self.id} of context {self.context_name}>"


class PropertyInfo():
    def __init__(self, property_info, context_name):
        self.name = property_info['Name']
        self.context_name = context_name
        self.typename = property_info['Type']
        self.persistent = property_info['Persistent']
        self.type = TypeBase.find_type(self.typename)
        self.default = property_info['Default']

    def __repr__(self):
        return f"<PropertyInfo '{self.name}' type={self.typename} of context {self.context_name}>"


class EntityInfo():
    def __init__(self, name, entity_info):
        self.entity_name = name
        self.contexts = dict()
        for context_name, context_data in entity_info.items():
            self.contexts[context_name] = dict()
            self.contexts[context_name]['exposed'] = context_data["Exposed"]
            self.contexts[context_name]['is_application'] = context_data["IsApplication"]
            self.contexts[context_name]['base_class_name'] = context_data["BaseClass"]
            self.contexts[context_name]['methods'] = dict()
            self.contexts[context_name]['properties'] = dict()
            for method_info in context_data["Methods"]:
                self.contexts[context_name]['methods'][method_info['ID']] = MethodInfo(method_info, context_name)
            for prop_info in context_data["Properties"]:
                self.contexts[context_name]['properties'][prop_info['Name']] = PropertyInfo(prop_info, context_name)

    def get_context(self, context_name):
        return self.contexts[context_name]

    def get_method(self, context_name, id) -> MethodInfo:
        return self.contexts[context_name]['methods'][id]

    def get_property(self, context_name, prop_name) -> PropertyInfo:
        return self.get_properties(context_name)[prop_name]

    def get_properties(self, context_name, only_persistent=False):
        if only_persistent:
            return {prop_name: prop_info for prop_name, prop_info in self.contexts[context_name]['properties'].items() if prop_info.persistent}

        return self.contexts[context_name]['properties']

    def find_method(self, context_name, method_name) -> MethodInfo:
        if context_name in self.contexts:
            for method in self.contexts[context_name]['methods'].values():
                if method.name == method_name:
                    return method

    def has_context(self, context_name):
        return context_name in self.contexts.keys()


class EntitiesInfo():
    def __init__(self, generated_info):
        self.entities = dict()
        for entity_name, entity_info in generated_info.items():
            self.entities[entity_name] = EntityInfo(entity_name, entity_info)

    def get_by_name(self, name) -> EntityInfo:
        # print(self.entities)
        entity_info = self.entities.get(name, None)
        assert entity_info is not None or error('Failed to get entity with name %s' % name)
        return entity_info

    def has_entity(self, name):
        return name in self.entities