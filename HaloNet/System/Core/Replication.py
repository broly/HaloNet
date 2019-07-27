from Core import WARN_MSG, ERROR_MSG
from Core.Property import Property, SliceReplicationKind
from Core.Type import MapBase
from Core.Utils import error


class Replication:

    def __init__(self, *vars):
        assert len(vars) > 0 or error("To start replication context one or more variables must be passed", depth=1)
        self.vars = [(var.owner, var.property_name) for var in vars]
        if None in self.vars:
            ERROR_MSG("None property name passed into Replication")
        for var in vars:
            if isinstance(var, MapBase):  # todo: temporary for valid buffer
                var.replication_buffer.append((SliceReplicationKind.Nop, None))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for context, varname in self.vars:
            var: Property = getattr(context, varname)
            var.replicate()
            var.flush_replication_buffer()


class Sync(Replication):
    def __exit__(self, exc_type, exc_val, exc_tb):
        for context, varname in self.vars:
            var: Property = getattr(context, varname)
            var.sync()