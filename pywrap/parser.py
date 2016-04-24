try:
    import clang.cindex as ci
    ci.Config.set_library_path("/usr/lib/llvm-3.5/lib/")
except:
    raise Exception("Install 'python-clang-3.5' and 'libclang-3.5-dev'. "
                    "Note that a recent operating system is required, e.g. "
                    "Ubuntu 14.04.")
import os
import warnings
from .type_conversion import cythontype_from_cpptype


def parse(include_file, parsable_file, includes, verbose):
    index = ci.Index.create()
    translation_unit = index.parse(parsable_file)
    cursor = translation_unit.cursor

    ast = AST(includes)
    ast.parse(cursor, parsable_file, include_file, verbose)
    return ast


class AST:
    """Abstract Syntax Tree."""
    def __init__(self, includes):
        self.includes = includes
        self.namespace = ""
        self.last_function = None
        self.last_type = None
        self.last_enum = None
        self.unnamed_struct = None
        self.functions = []
        self.classes = []
        self.typedefs = []
        self.enums = []

    def parse(self, node, parsable_file, include_file, verbose=0):
        namespace = self.namespace
        if verbose >= 2:
            print("Node: %s, %s" % (node.kind, node.displayname))

        parse_children = True
        try:
            if node.location.file is None:
                pass
            elif node.location.file.name != parsable_file:
                return
            elif node.kind == ci.CursorKind.NAMESPACE:
                if self.namespace == "":
                    self.namespace = node.displayname
                else:
                    self.namespace = self.namespace + "::" + node.displayname
            elif node.kind == ci.CursorKind.PARM_DECL:
                tname = cythontype_from_cpptype(node.type.spelling)
                self.includes.add_include_for(tname)
                param = Param(node.displayname, tname)
                if self.last_function is not None:
                    self.last_function.arguments.append(param)
            elif node.kind == ci.CursorKind.FUNCTION_DECL:
                tname = cythontype_from_cpptype(node.result_type.spelling)
                self.includes.add_include_for(tname)
                function = Function(
                    include_file, self.namespace, node.spelling, tname)
                self.functions.append(function)
                self.last_function = function
            elif node.kind == ci.CursorKind.FUNCTION_TEMPLATE:
                self.last_function = DummyFunction()
                warnings.warn("Templates are not implemented yet")
            elif node.kind == ci.CursorKind.CXX_METHOD:
                if node.access_specifier == ci.AccessSpecifier.PUBLIC:
                    tname = cythontype_from_cpptype(node.result_type.spelling)
                    self.includes.add_include_for(tname)
                    method = Method(node.spelling, tname, self.classes[-1].name)
                    self.classes[-1].methods.append(method)
                    self.last_function = method
            elif node.kind == ci.CursorKind.CONSTRUCTOR:
                if node.access_specifier == ci.AccessSpecifier.PUBLIC:
                    constructor = Constructor(self.last_type.name)
                    self.last_type.constructors.append(constructor)
                    self.last_function = constructor
            elif node.kind == ci.CursorKind.CLASS_DECL:
                clazz = Clazz(include_file, self.namespace, node.displayname)
                self.classes.append(clazz)
                self.last_type = clazz
            elif node.kind == ci.CursorKind.STRUCT_DECL:
                if node.displayname == "" and self.unnamed_struct is None:
                    self.unnamed_struct = Clazz(
                        include_file, self.namespace, node.displayname)
                    self.last_type = self.unnamed_struct
                else:
                    clazz = Clazz(include_file, self.namespace, node.displayname)
                    self.classes.append(clazz)
                    self.last_type = clazz
            elif node.kind == ci.CursorKind.FIELD_DECL:
                if node.access_specifier == ci.AccessSpecifier.PUBLIC:
                    tname = cythontype_from_cpptype(node.type.spelling)
                    self.includes.add_include_for(tname)
                    field = Field(node.displayname, tname, self.last_type.name)
                    self.last_type.fields.append(field)
            elif node.kind == ci.CursorKind.TYPEDEF_DECL:
                tname = node.displayname
                underlying_tname = node.underlying_typedef_type.spelling
                if "struct " + tname == underlying_tname:
                    if self.unnamed_struct is None:
                        raise LookupError("Struct typedef does not match any "
                                          "unnamed struct")
                    self.unnamed_struct.name = tname
                    self.classes.append(self.unnamed_struct)
                    self.unnamed_struct = None
                    self.last_type = None
                    parse_children = False
                else:
                    self.includes.add_include_for(underlying_tname)
                    self.typedefs.append(Typedef(
                        include_file, self.namespace, tname,
                        cythontype_from_cpptype(underlying_tname)))
            elif node.kind == ci.CursorKind.ENUM_DECL:
                enum = Enum(include_file, self.namespace, node.displayname)
                self.last_enum = enum
                self.enums.append(enum)
            elif node.kind == ci.CursorKind.ENUM_CONSTANT_DECL:
                self.last_enum.constants.append(node.displayname)
            elif node.kind == ci.CursorKind.COMPOUND_STMT:
                parse_children = False
            else:
                if verbose:
                    print("Ignored node: %s, %s" % (node.kind, node.displayname))
        except NotImplementedError as e:
            warnings.warn(e.message + " Ignoring node '%s'" % node.displayname)
            parse_children = False

        if parse_children:
            for child in node.get_children():
                self.parse(child, parsable_file, include_file, verbose)

        self.namespace = namespace

    def accept(self, exporter):
        for enum in self.enums:
            enum.accept(exporter)
        for typedef in self.typedefs:
            typedef.accept(exporter)
        for clazz in self.classes:
            clazz.accept(exporter)
        for fun in self.functions:
            fun.accept(exporter)
        exporter.visit_ast(self)


class Includes:
    def __init__(self):
        self.numpy = False
        self.stl = {"vector": False,
                    "string": False,
                    "deque": False,
                    "list": False,
                    "map": False,
                    "pair": False,
                    "queue": False,
                    "set": False,
                    "stack": False}
        self.deref = False

    def add_include_for(self, tname):
        if self._part_of_tname(tname, "bool"):
            self.boolean = True
        for t in self.stl.keys():
            if self._part_of_tname(tname, t):
                self.stl[t] = True

    def add_include_for_deref(self):
        self.deref = True

    def _part_of_tname(self, tname, subtname):
        return (tname == subtname or tname.startswith(subtname) or
                ("<" + subtname + ">") in tname or
                ("<" + subtname + ",") in tname or
                (", " + subtname + ">") in tname or
                ("[" + subtname + "]") in tname or
                ("[" + subtname + ",") in tname or
                (", " + subtname + "]") in tname)

    def declarations_import(self):
        includes = "from libcpp cimport bool" + os.linesep

        for t in self.stl.keys():
            if self.stl[t]:
                includes += ("from libcpp.%(type)s cimport %(type)s"
                             % {"type": t}) + os.linesep

        return includes

    def implementations_import(self):
        includes = "from libcpp cimport bool" + os.linesep
        if self.numpy:
            includes += "cimport numpy as np" + os.linesep
            includes += "import numpy as np" + os.linesep

        for t in self.stl.keys():
            if self.stl[t]:
                includes += ("from libcpp.%(type)s cimport %(type)s"
                             % {"type": t}) + os.linesep

        if self.deref:
            includes += ("from cython.operator cimport dereference as deref" +
                         os.linesep)
        includes += "cimport _declarations as cpp" + os.linesep
        return includes


class Enum:
    def __init__(self, filename, namespace, tipe):
        self.filename = filename
        self.namespace = namespace
        self.tipe = tipe
        self.constants = []

    def accept(self, exporter):
        exporter.visit_enum(self)


class Typedef:
    def __init__(self, filename, namespace, tipe, underlying_type):
        self.filename = filename
        self.namespace = namespace
        self.tipe = tipe
        self.underlying_type = underlying_type

    def accept(self, exporter):
        exporter.visit_typedef(self)


class Clazz:
    def __init__(self, filename, namespace, name):
        self.filename = filename
        self.namespace = namespace
        self.name = name
        self.constructors = []
        self.methods = []
        self.fields = []

    def accept(self, exporter):
        for field in self.fields:
            field.accept(exporter)
        for ctor in self.constructors:
            ctor.accept(exporter)
        for method in self.methods:
            method.accept(exporter)
        exporter.visit_class(self)


class FunctionBase(object):
    def __init__(self, name):
        self.name = name
        self.arguments = []
        self.ignored = False

    def accept(self, exporter):
        for arg in self.arguments:
            arg.accept(exporter)


class Function(FunctionBase):
    def __init__(self, filename, namespace, name, result_type):
        super(self.__class__, self).__init__(name)
        self.filename = filename
        self.namespace = namespace
        self.result_type = result_type

    def accept(self, exporter):
        super(Function, self).accept(exporter)
        exporter.visit_function(self)


class Constructor(FunctionBase):
    def __init__(self, class_name):
        super(self.__class__, self).__init__(None)
        self.class_name = class_name

    def accept(self, exporter):
        super(Constructor, self).accept(exporter)
        exporter.visit_constructor(self)


class Method(FunctionBase):
    def __init__(self, name, result_type, class_name):
        super(self.__class__, self).__init__(name)
        self.result_type = result_type
        self.class_name = class_name

    def accept(self, exporter):
        super(Method, self).accept(exporter)
        exporter.visit_method(self)


class DummyFunction(FunctionBase):
    def __init__(self):
        super(DummyFunction, self).__init__("")

    def accept(self, exporter):
        pass


class Param:
    def __init__(self, name, tipe):
        self.name = name
        self.tipe = tipe

    def accept(self, exporter):
        exporter.visit_param(self)


class Field:
    def __init__(self, name, tipe, class_name):
        self.name = name
        self.tipe = tipe
        self.class_name = class_name
        self.ignored = False

    def accept(self, exporter):
        exporter.visit_field(self)
