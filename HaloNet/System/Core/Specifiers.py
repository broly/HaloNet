import sys

specifiers_docs = list()

def declspec(__doc__=""):
    pass

all_specifiers = dict()

def END_SPECIFIERS():
    outer = sys._getframe(1).f_locals
    for key in outer['__annotations__'].keys():
        all_specifiers[key] = outer[key]
