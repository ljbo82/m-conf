# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from __future__       import annotations
from .assignment_mode import AssignmentMode
from .config          import Config
from .error           import *

class Context:
    def __init__(self, ctx_id: str = 'ctx', cfg: Config | None = None):
        assert_type(ctx_id, str, 'ctx_id')
        if not ctx_id:
            raise ValueError('ctx_id: Value cannot be empty')

        if cfg is None:
            cfg = Config()

        assert_type(cfg, Config, 'ctx')

        self.__ctx_id: str = ctx_id
        self.__cfg = cfg
        self.__line_number: int = 0
        self.__section: str = ""
        self.__reset()

    def __repr__(self):
        return f"{self.ctx_id}:{self.line_number}"

    @property
    def ctx_id(self) -> str:
        return self.__ctx_id

    @property
    def cfg(self) -> Config:
        return self.__cfg

    @property
    def path(self) -> str | None:
        return self.__path

    @property
    def assignment_mode(self) -> AssignmentMode | None:
        return self.__assignment_mode

    @property
    def value(self) -> str | None:
        return self.__value

    @property
    def continuation(self) -> bool:
        return self.__continuation

    @property
    def line_number(self) -> int:
        return self.__line_number

    @property
    def section(self )-> str | None:
        return self.__section

    @section.setter
    def section(self, path: str):
        assert_type(path, str, 'path')

        if not path:
            self.__section = ""
            return

        entry = self.cfg.get(path, create_intermediate=True)
        if entry is None or isinstance(entry.value, Config):
            self.__section = path
            return

        raise ContextError(f"Path '{path}' is already assigned")

    def __reset(self):
        self.__path: str | None = None
        self.__value: str | None = None
        self.__assignment_mode: AssignmentMode | None = None
        self.__continuation: bool = False

    def __assert(self, condition: bool):
        if not condition:
            raise ContextError('Invalid state')

    def apply(self):
        self.__assert(self.path is not None)
        self.__assert(self.value is not None)
        self.__assert(self.assignment_mode is not None)

        prefix = "" if not self.section else f"{self.section}."

        try:
            self.cfg.assign(f"{prefix}{self.path}", self.value, self.assignment_mode, explode_value=True) # type: ignore
        except Error as ex:
            raise ContextError(f"{self}: {str(ex)}")

        self.__reset()

    def increment_line_number(self) -> int:
        self.__line_number += 1
        return self.__line_number

    def assign(self, path: str, value: str, mode: AssignmentMode = AssignmentMode.SET, continues: bool = False):
        self.__assert(self.path is None)
        self.__assert(self.value is None)
        self.__assert(self.assignment_mode is None)
        self.__assert(self.continuation is False)

        assert_type(path, str, 'path')
        assert_type(value, str, 'value')
        assert_type(mode, AssignmentMode, 'mode')
        assert_type(continues, bool, 'continues')

        self.__path = path
        self.__value = value
        self.__assignment_mode = mode
        self.__continuation = continues

        if not continues:
            self.apply()

    def continue_assignment(self, value: str, continues: bool = False):
        self.__assert(self.path is not None)
        self.__assert(self.value is not None)
        self.__assert(self.assignment_mode is not None)
        self.__assert(self.continuation)

        assert_type(value, str, 'value')
        assert_type(continues, bool, 'continues')

        value = value.strip()

        if value:
            self.__value = f"{self.value} {value.strip()}"

        self.__continuation = continues

        if not continues:
            self.apply()
