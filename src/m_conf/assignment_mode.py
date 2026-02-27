
# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from __future__  import annotations
from .error      import *
from enum        import Enum

class AssignmentMode(Enum):
    SET            = ('=')
    REPLACE        = ('!=')
    FALLBACK       = ('?=')
    APPEND         = ('+=')
    UNION          = ('^=')

    __map: dict[str, AssignmentMode] = {}

    @classmethod
    def from_str(cls, assignment: str) -> AssignmentMode | None:
        assert_type(assignment, str, 'assignment')
        return cls.__map.get(assignment)

    def __init__(self, assignment):
        self.__map[assignment] = self
