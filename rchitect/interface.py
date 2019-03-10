from __future__ import unicode_literals
from rchitect._libR import ffi, lib
from .dispatch import dispatch
from .types import RObject, SEXP, sexptype, datatype

from six import string_types


dispatch.add_rules(type, datatype)
dispatch.add_rules(
    ffi.CData,
    lambda x: sexptype(x) if ffi.typeof(x) == ffi.typeof('SEXP') else ffi.CData)


@dispatch(SEXP)
def sexp(x):
    return x


@dispatch(RObject)  # noqa
def sexp(x):
    return x.s


@dispatch(RObject)
def robject(x):
    return x


@dispatch(SEXP)  # noqa
def robject(x):
    return RObject(x)


def rint_p(s):
    return lib.Rf_ScalarInteger(s)


def rint(s):
    return robject(rint_p(s))


def rlogical_p(s):
    return lib.Rf_ScalarLogical(s)


def rlogical(s):
    return robject(rlogical_p(s))


def rdouble_p(s):
    return lib.Rf_ScalarReal(s)


def rdouble(s):
    return robject(rdouble_p(s))


def rchar_p(s):
    isascii = all(ord(c) < 128 for c in s)
    b = s.encode("utf-8")
    return lib.Rf_mkCharLenCE(b, len(b), lib.CE_NATIVE if isascii else lib.CE_UTF8)


def rchar(s):
    return robject(rchar_p(s))


def rstring_p(s):
    return lib.Rf_ScalarString(rchar_p(s))


def rstring(s):
    return robject(rstring_p(s))


def rsym_p(s, t=None):
    if t:
        return rlang_p("::", rsym_p(s), rsym_p(t))
    else:
        return lib.Rf_install(s.encode("utf-8"))


def rsym(s, t=None):
    return robject(rsym_p(s, t))


def rparse_p(s):
    status = ffi.new("ParseStatus[1]")
    s = lib.Rf_protect(rstring_p(s))
    ret = lib.R_ParseVector(s, -1, status, lib.R_NilValue)
    try:
        if status[0] != lib.PARSE_OK:
            raise Exception("Parse error")
    finally:
        lib.Rf_unprotect(1)
    return ret


def rparse(s):
    return robject(rparse_p(s))


def reval_p(s):
    if isinstance(s, ):
        expressions = rparse_p(s)
    elif isinstance(s, RObject) and lib.TYPEOF(sexp(s)) == lib.EXPRSXP:
        expressions = sexp(s)
    elif isinstance(s, SEXP) and lib.TYPEOF(s) == lib.EXPRSXP:
        expressions = s
    else:
        raise TypeError("unexpected object")

    lib.Rf_protect(expressions)
    ret = lib.R_NilValue
    status = ffi.new("int[1]")
    try:
        for i in range(0, lib.Rf_length(expressions)):
            ret = lib.R_tryEval(lib.VECTOR_ELT(expressions, i), lib.R_GlobalEnv, status)
            if status[0] != 0:
                raise RuntimeError("reval error")
    finally:
        lib.Rf_unprotect(1)
    return ret


def reval(s):
    return robject(reval_p(s))


def rlang_p(*args, **kwargs):
    nprotect = 0
    for a in args:
        if isinstance(a, SEXP):
            lib.Rf_protect(a)
            nprotect += 1
    for v in kwargs.values():
        if isinstance(v, SEXP):
            lib.Rf_protect(v)
            nprotect += 1
    nargs = len(args) + len(kwargs)
    t = lib.Rf_protect(lib.Rf_allocVector(lib.LANGSXP, nargs))
    nprotect += 1
    s = t
    try:
        fname = args[0]
        if isinstance(fname, SEXP):
            lib.SETCAR(s, fname)
        elif isinstance(fname, RObject):
            lib.SETCAR(s, sexp(fname))
        elif isinstance(fname, string_types):
            lib.SETCAR(s, rsym_p(fname))
        elif isinstance(fname, tuple) and len(fname) == 2:
            lib.SETCAR(s, rsym_p(*fname))
        else:
            raise TypeError("unexpected function")

        for a in args[1:]:
            s = lib.CDR(s)
            lib.SETCAR(s, sexp(a))
        for k, v in kwargs.items():
            s = lib.CDR(s)
            lib.SETCAR(s, sexp(v))
            lib.SET_TAG(s, lib.Rf_install(k.encode("utf-8")))

        ret = t
    finally:
        lib.Rf_unprotect(nprotect)
    return ret


def rlang(*args, **kwargs):
    return robject(rlang_p(*args, **kwargs))
