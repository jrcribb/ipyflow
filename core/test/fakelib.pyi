# -*- coding: utf-8 -*-
from ipyflow.annotations import Mutated, __module__, handler_for, module, self

foo = bar = None

class OnlyPresentSoThatHandlersCanBeRegistered:
    def method_for_method_stub_presence(self) -> Mutated[self]: ...
    #
    @handler_for("method_a", "method_b")
    def handler_by_a_different_name(self) -> Mutated[self]: ...

def function_for_function_stub_presence() -> Mutated[__module__]: ...

#
def fun_for_testing_kwarg(foo, bar) -> Mutated[bar]: ...

#
def fun_for_testing_kwonlyarg(foo, *, bar) -> Mutated[bar]: ...

#
""":sys.version_info >= (3, 8)
def fun_for_testing_posonlyarg(foo, /, bar) -> Mutated[foo]: ...
"""

#
@module("non_fakelib_module")
def function_in_another_module() -> Mutated[__module__]: ...

#
@module("non_fakelib_module")
class ClassInAnotherModule:
    def method_in_another_module(self) -> Mutated[self]: ...
