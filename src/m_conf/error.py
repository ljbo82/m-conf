# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

def assert_type(obj: object, class_or_tuple:  type | tuple[type, ...], prefix: str = '', msg: str = ''):
    if not isinstance(obj, class_or_tuple):
        if prefix:
            prefix = f"[{prefix.strip(' :')}] "

        if not msg:
            msg = f"Invalid type: {'None' if type(obj) == type(None) else type(obj).__name__}"

        raise TypeError(f"{prefix}{msg}")

class Error(Exception):
    pass

class PathError(Error):
    pass

class AssignmentError(Error):
    pass

class ContextError(Error):
    pass

class ParsingError(ContextError):
    pass
