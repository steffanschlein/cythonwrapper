from pywrap.exporter import (MethodDefinition, SetterDefinition,
                             GetterDefinition, ConstructorDefinition,
                             FunctionDefinition, CythonDeclarationExporter)
from pywrap.cython import TypeInfo
from pywrap.ast import (Includes, Param, Function, Clazz, Constructor, Method,
                        Field)
from pywrap.utils import lines
from pywrap.defaultconfig import Config
from pywrap.ast import Field
from nose.tools import assert_equal, assert_multi_line_equal


def test_simple_function_def():
    method = MethodDefinition(
        "Testclass", "testfun", [], Includes(),
        "void", TypeInfo({}), Config()).make()
    assert_multi_line_equal(
        method,
        lines("cpdef testfun(Testclass self):",
              "    self.thisptr.testfun()")
    )


def test_array_arg_function_def():
    method = MethodDefinition(
        "Testclass", "testfun", [Param("a", "double *"),
                                 Param("aSize", "unsigned int")],
        Includes(), "void", TypeInfo({}), Config()).make()
    assert_multi_line_equal(
        method,
        lines("cpdef testfun(Testclass self, np.ndarray[double, ndim=1] a):",
              "    self.thisptr.testfun(&a[0], a.shape[0])")
    )


def test_setter_definition():
    field = Field("myField", "double", "MyClass")
    setter = SetterDefinition(
        "MyClass", field, Includes(), TypeInfo(), Config()).make()
    assert_multi_line_equal(
        setter,
        lines(
            "cpdef set_my_field(MyClass self, double myField):",
            "    cdef double cpp_myField = myField",
            "    self.thisptr.myField = cpp_myField"
        )
    )


def test_getter_definition():
    field = Field("myField", "double", "MyClass")
    getter = GetterDefinition(
        "MyClass", field, Includes(), TypeInfo(), Config()).make()
    assert_multi_line_equal(
        getter,
        lines(
            "cpdef get_my_field(MyClass self):",
            "    cdef double result = self.thisptr.myField",
            "    return result"
        )
    )

def test_default_ctor_def():
    ctor = ConstructorDefinition("MyClass", [], Includes(), TypeInfo(),
                                 Config(), "MyClass").make()
    assert_multi_line_equal(
        ctor,
        lines(
            "def __init__(MyClass self):",
            "    self.thisptr = new cpp.MyClass()"
        )
    )


def test_function_def():
    fun = FunctionDefinition("myFun", [], Includes(), "void", TypeInfo(),
                             Config()).make()
    assert_multi_line_equal(
        fun,
        lines(
            "cpdef my_fun():",
            "    cpp.myFun()"
        )
    )


def test_function_def_with_another_cppname():
    fun = FunctionDefinition("myFunInt", [], Includes(), "void", TypeInfo(),
                             Config(), cppname="myFun").make()
    assert_multi_line_equal(
        fun,
        lines(
            "cpdef my_fun_int():",
            "    cpp.myFun()"
        )
    )


def test_function_decl():
    fun = Function("test.hpp", "", "myFun", "void")
    ignored_fun = Function("test.hpp", "", "myFun", "void")
    ignored_fun.ignored = True
    exporter = CythonDeclarationExporter(Includes(), Config())
    exporter.visit_function(fun)
    exporter.visit_function(ignored_fun)
    exporter.visit_ast(None)
    decl = exporter.export()
    assert_multi_line_equal(
        decl.strip(),
        lines(
            "cdef extern from \"test.hpp\" namespace \"\":",
            "    void myFun()"
        )
    )


def test_class_decl():
    clazz = Clazz("test.hpp", "", "MyClass")
    exporter = CythonDeclarationExporter(Includes(), Config())
    exporter.visit_class(clazz)
    exporter.visit_ast(None)
    decl = exporter.export()
    assert_multi_line_equal(
        decl.strip(),
        lines(
            "cdef extern from \"test.hpp\" namespace \"\":",
            "    cdef cppclass MyClass:",
            "        pass"
        )
    )


def test_ctor_decl():
    clazz = Clazz("test.hpp", "", "MyClass")
    ctor = Constructor("MyClass")
    ignored_ctor = Constructor("MyClass")
    ignored_ctor.ignored = True
    exporter = CythonDeclarationExporter(Includes(), Config())
    exporter.visit_constructor(ctor)
    exporter.visit_constructor(ignored_ctor)
    exporter.visit_class(clazz)
    exporter.visit_ast(None)
    decl = exporter.export()
    assert_multi_line_equal(
        decl.strip(),
        lines(
            "cdef extern from \"test.hpp\" namespace \"\":",
            "    cdef cppclass MyClass:",
            "        MyClass()"
        )
    )


def test_method_decl():
    clazz = Clazz("test.hpp", "", "MyClass")
    method = Method("myMethod", "void", "MyClass")
    ignored_method = Method("", "", "")
    ignored_method.ignored = True
    exporter = CythonDeclarationExporter(Includes(), Config())
    exporter.visit_param(Param("myParam", "double"))
    exporter.visit_method(method)
    exporter.visit_method(ignored_method)
    exporter.visit_class(clazz)
    exporter.visit_ast(None)
    decl = exporter.export()
    assert_multi_line_equal(
        decl.strip(),
        lines(
            "cdef extern from \"test.hpp\" namespace \"\":",
            "    cdef cppclass MyClass:",
            "        void myMethod(double myParam)"
        )
    )


def test_field_decl():
    clazz = Clazz("test.hpp", "", "MyClass")
    field = Field("myField", "double", "MyClass")
    ignored_field = Field("myField", "double", "MyClass")
    ignored_field.ignored = True
    exporter = CythonDeclarationExporter(Includes(), Config())
    exporter.visit_field(field)
    exporter.visit_field(ignored_field)
    exporter.visit_class(clazz)
    exporter.visit_ast(None)
    decl = exporter.export()
    assert_multi_line_equal(
        decl.strip(),
        lines(
            "cdef extern from \"test.hpp\" namespace \"\":",
            "    cdef cppclass MyClass:",
            "        double myField"
        )
    )
