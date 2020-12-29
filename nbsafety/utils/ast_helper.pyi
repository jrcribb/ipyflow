# -*- coding: utf-8 -*-
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any
    import ast

class FastAst:
    @staticmethod
    def location_of(*args, **kwargs) -> 'Any': ...

    @staticmethod
    def Call(*args, **kwargs) -> 'ast.Call': ...
    @staticmethod
    def Name(*args, **kwargs) -> 'ast.Name': ...
    @staticmethod
    def NameConstant(*args, **kwargs) -> 'ast.NameConstant': ...

    if sys.version_info <= (3, 8):
        @staticmethod
        def Num(*args, **kwargs) -> 'ast.Num': ...
        @staticmethod
        def Str(*args, **kwargs) -> 'ast.Str': ...
    else:
        @staticmethod
        def Num(*args, **kwargs) -> 'ast.Constant': ...
        @staticmethod
        def Str(*args, **kwargs) -> 'ast.Constant': ...
        @staticmethod
        def Constant(*args, **kwargs) -> 'ast.Constant': ...