import collections
import json

from Core.Common.Helpers import Singleton


class ConfigurationGenerator(metaclass=Singleton):
    """ Access to generated config files
        @cvar gen_info_filename - name of generated file
    """
    gen_info_filename = "Config.generated.json"

    def __init__(self):
        self.generated_info = dict()
        self.generated_types = dict()
        self.generator_signature = "~"

    def load_generated_info(self):
        """  Загрузка сгенерированной инфромации
        """
        try:
            with open(ConfigurationGenerator().gen_info_filename, 'rb') as f:
                data = f.read().decode('utf-8')

                g = json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode(data)
                self.generated_info = g["entities"]
                self.generated_types = g["types"]
                self.generator_signature = g['signature']
                from Core.Info import EntitiesInfo
                self.generated_entities_info = EntitiesInfo(self.generated_info)
        except FileNotFoundError:
            pass


class ConfigurationAccess:
    def __init__(self, config_dict, name):
        self.config_dict = config_dict
        self.name = name

    def __getattr__(self, item):
        value = self.config_dict.get(item, None)
        if item not in self.config_dict:
            return InvalidConfigurationAccess(self.name + "." + item)
        if isinstance(value, dict):
            return ConfigurationAccess(value, self.name + "." + item)
        return value

    def __repr__(self):
        return f"<ConfigurationAccess to '{self.name}'>"


class InvalidConfigurationAccess:
    def __init__(self, name):
        from Core import WARN_MSG
        self.name = name
        WARN_MSG(f"Access to invalid configuration '{self.name}'")

    def __repr__(self):
        return f"<InvalidConfigurationAccess to '{self.name}'>"

    def __getattr__(self, item):
        return InvalidConfigurationAccess(self.name + "." + item)

    def __bool__(self):
        return False