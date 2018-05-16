from ctypes import py_object, c_void_p, cast, pointer, CFUNCTYPE
from .internals import R_MakeExternalPtr, R_RegisterCFinalizerEx, R_NilValue
from .types import SEXP

extptrs = {}


@CFUNCTYPE(None, SEXP)
def finalizer(s):
    if s.value in extptrs:
        del extptrs[s.value]


def rextptr(f):
    fpy = py_object(f)
    s = R_MakeExternalPtr(cast(pointer(fpy), c_void_p), R_NilValue, R_NilValue)
    extptrs[s.value] = fpy
    R_RegisterCFinalizerEx(s, finalizer, 1)
    return s