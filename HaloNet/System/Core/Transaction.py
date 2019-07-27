import asyncio

from Core import ERROR_MSG, INFO_MSG, WARN_MSG
from Core.Globals import Globals
from Core.LocalDatatypes import FPropertyInfo
from Core.Replication import Replication
from Core.Type import TArray
from Core.Utils import error
from time import time


class Transaction(Replication):
    """
    Transaction

    Transaction creates an `async with` context of transaction of variables which must changed
    
    Transaction will complete successfully if
        1. Database is actual
        2. Transaction not cancelled
        3. Code has no errors
        
    In another cases transaction not changed any variables

    Usage:
        async with Transaction(self.Money, friend.Money) as t:
            if self.Money < 10:
                t.exit()
            self.Money -= 10
            friend.Money += 10
            
    Warning:
        Transactions must no use inside anther transactions with same veriables
        This causes deadlock
    """
    id_counter = 0

    def __init__(self, *vars, name="Undefined"):
        super().__init__(*vars)
        assert len(vars) > 0 or error("To start transaction one or more variables must be passed", depth=1)
        self.serialized_variables = dict()
        self.old_variables = TArray[FPropertyInfo]()
        self.name = name
        self.id = self.new_id()

    @classmethod
    def new_id(cls):
        r = cls.id_counter
        cls.id_counter += 1
        return r

    def __repr__(self):
        return "<Transaction %s (%i)>" % (self.name, self.id)

    def __str__(self):
        return "<Transaction %s (%i)>" % (self.name, self.id)

    async def __aenter__(self):
        while any([getattr(context, varname).locked for context, varname in self.vars]):
            for context, varname in self.vars:
                var = getattr(context, varname)
                if var.locked:
                    # WARN_MSG("Variable %s locked, transaction %s waiting for unlock..." % (varname, self))
                    try:
                        await asyncio.wait_for(var.waitforunlock(), 2)
                    except asyncio.TimeoutError:
                        ERROR_MSG("Variable %s locked by %s more for 5 seconds! Check your code for nested transactions with the same variables" % (varname, var.locker), depth=1)
                        # raise TransactionError("Variables locked too long")

        INFO_MSG("Entered %s with %s" % (self, (self.vars,)), depth=1)

        for context, varname in self.vars:
            var = getattr(context, varname)
            await var.lock(self)

        self.savepoint()
        return Replication.__enter__(self)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        do_not_raise_exc = True

        if exc_type is None:
            new_variables = TArray[FPropertyInfo]()
            for context, varname in self.vars:
                var = getattr(context, varname)
                info = FPropertyInfo(EntityDBID=context.dbid,
                                     EntityClass=context.__class__.__name__,
                                     PropertyName=var.property_name,
                                     PropertyTypeName=var.get_type_name(),
                                     SerializedValue=var.serialize())
                new_variables.append(info)
            success = await Globals.this_service.db.UpdateVariablesTransactionally(self.old_variables, new_variables)
            if success:
                self.unlock_all()
                INFO_MSG("%s done" % self, depth=1)
                Replication.__exit__(self, exc_type, exc_val, exc_tb)
            else:
                self.rollback("DB error")
                self.unlock_all()
                ERROR_MSG("%s failed, because values in database not actual. Variables rolled back" % self, depth=1)
                raise TransactionError("Variables changed outside transaction")
        elif exc_type == TransactionExitException:
            self.rollback("Interrupted")
            self.unlock_all()
            do_not_raise_exc = True
            WARN_MSG("Transaction %s interrupted from code. Variables rolled back" % self, depth=1)
        else:
            self.rollback("Code error")
            self.unlock_all()
            do_not_raise_exc = False
            ERROR_MSG("%s failed, because errors in code. Variables rolled back" % self, depth=1)

        # for context, varname in self.vars:
        #     var = getattr(context, varname)
        #     if var.locked:
        #         var.unlock()

        return do_not_raise_exc

    def unlock_all(self):
        for context, varname in self.vars:
            var = getattr(context, varname)
            if var.locked:
                var.unlock()

    def savepoint(self):
        for context, varname in self.vars:
            var = getattr(context, varname)
            if var.property_name:
                serialized = var.serialize()
                old_info = FPropertyInfo(EntityDBID=context.dbid,
                                         EntityClass=context.__class__.__name__,
                                         PropertyName=var.property_name,
                                         PropertyTypeName=var.get_type_name(),
                                         SerializedValue=serialized)
                self.old_variables.append(old_info)
                self.serialized_variables[var.property_name] = (context, serialized)

    def rollback(self, reason):
        WARN_MSG("rolling back, reason", reason)
        for property_name, (context, serialized_value) in self.serialized_variables.items():
            T = context.properties[property_name].prop_type
            ds = T.deserialize(serialized_value)
            setattr(context, property_name, ds)
            getattr(context, property_name).replicate()

    def exit(self, err):
        raise TransactionExitException(err)

    def __enter__(self):
        error("Transaction is async action. Use 'async with' instead", NotImplementedError, depth=2)

class TransactionError(Exception):
    pass


class TransactionExitException(Exception):
    pass


def ensure_locked(*vars):
    """ Checks the all variables are locked (by transaction) and returns true. 
        False otherwise and shows warning about unlocked variables
    """
    result = all([var.locked for var in vars])
    if not result:
        WARN_MSG("This variables not locked: [%s]" % ", ".join(var.property_name for var in vars if not var.locked), depth=1)
    return result


def transaction_only(*properties):
    def decorator(method):

        return method
    return decorator