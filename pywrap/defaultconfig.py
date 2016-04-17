cpp_header_endings = ["h", "hh", "hpp"]
pyx_file_ending = "pyx"
pxd_file_ending = "pxd"
# TODO extend operator mapping:
# http://docs.cython.org/src/reference/special_methods_table.html
operators = {
    "operator()": "__call__",
    "operator[]": "__getitem__",
    "operator+": "__add__",
    "operator-": "__sub__",
    "operator*": "__mul__",
    "operator/": "__div__"
}
call_operators = {
    "operator()": "call",
    "operator[]": "getitem",
    "operator+": "add",
    "operator-": "sub",
    "operator*": "mul",
    "operator/": "div"
}

typedef_def = """cdef extern from "%(filename)s" namespace "%(namespace)s":
    ctypedef %(underlying_type)s %(tipe)s"""
class_def = """cdef extern from "%(filename)s" namespace "%(namespace)s":
    cdef cppclass %(name)s:"""
method_def = "        %(result_type)s %(name)s(%(args)s)"
constructor_def = "        %(name)s(%(args)s)"
function_def = """cdef extern from "%(filename)s" namespace "%(namespace)s":
    %(result_type)s %(name)s(%(args)s)"""
arg_def = "%(tipe)s %(name)s"
field_def = "        %(tipe)s %(name)s"

py_class_def = """cdef class %(name)s:
    cdef cpp.%(name)s * thisptr
    cdef bool delete_thisptr

    def __cinit__(self):
        self.thisptr = NULL
        self.delete_thisptr = True

    def __dealloc__(self):
        if self.delete_thisptr and self.thisptr != NULL:
            del self.thisptr
"""
py_default_ctor = """    def __init__(cpp.%(name)s self):
        self.thisptr = new cpp.%(name)s()
"""
py_signature_def = "%(def)s %(name)s(%(args)s):"
py_ctor_signature_def = "def __init__(%(args)s):"
py_ctor_call = "self.thisptr = new cpp.%(class_name)s(%(args)s)"
py_arg_def = "%(name)s"
py_field_def = """    %(name)s = property(get_%(name)s, set_%(name)s)
"""
setup_extension = """
    config.add_extension(
        '%(module)s',
        sources=["%(module)s.cpp", "%(filename)s"],
        include_dirs=["%(sourcedir)s", numpy.get_include()],
        define_macros=[("NDEBUG",)],
        extra_compile_args=["-O3"],
        language="c++",
    )
"""
setup_py = """def configuration(parent_package='', top_path=None):
    from numpy.distutils.misc_util import Configuration
    import numpy

    config = Configuration('.', parent_package, top_path)
%(extensions)s
    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup
    setup(**configuration(top_path='').todict())
"""
