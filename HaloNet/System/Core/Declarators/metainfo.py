import sys

from Core.Declarators.Specs import Exposed, Exec, Multicast


class metainfo:
    """
    Stores metadata prepared for inject to outer frame
    """
    def __init__(self, *args, base=None, using_class=None, display_attributes=None):
        self.args = args
        self.base = base
        self.using_class = using_class
        self.display_attributes = display_attributes

    def __invert__(self):
        """ Внедряет метаданные во внешний фрейм """
        locals = sys._getframe(1).f_locals

        if Exposed in self.args: locals['is_exposed'] = True
        if Exec in self.args: locals['is_exec_capable'] = True
        if Multicast in self.args: locals['is_multicast'] = True

        if self.base: locals['base_entity_class'] = self.base
        if self.using_class: locals['using_class'] = self.using_class
        if self.display_attributes: locals['display_attributes'] = self.display_attributes

        return self