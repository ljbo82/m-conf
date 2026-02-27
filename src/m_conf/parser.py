
# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from __future__       import annotations
from .assignment_mode import AssignmentMode
from .config          import Config
from .context         import Context
from .error           import *
from io               import StringIO
from typing           import Final, IO

import re

class Parser:
    # [OK] $1: Effective line. $2: Comment.
    LINE: Final = re.compile(r"^(.*?)(?:(?<!\\)(#.*))?$")

    # [OK] $1: Section name
    SECTION: Final = re.compile(r"^\[\s*(.*)\s*]$")

    # [OK] $1: Path. $2 Assignmen operator. $3: Value
    ASSIGNMENT: Final = re.compile(r"^([^?!=+^\s]*)\s*(=|!=|\?=|\+=|\^=)\s*(.*)(\\?)$")

    # [OK] $1: Path
    PATH: Final = re.compile(r"^((?:\*|[\w-]+)(?:\.(?:[\w-]+|\*))*)$")

    # [OK] $1: Value, $2: Continuation backlash
    VALUE: Final = re.compile(r"^((?:[^\\]|\\\\|\\\s|\\'|\\n|\\\")*)(\\?)$")

    def __init__(self, set_is_replace: bool = False):
        self.__set_is_replace = set_is_replace

    @property
    def set_is_replace(self) -> bool:
        return self.__set_is_replace

    def __parse_empty(self, ctx: Context, line: str) -> bool:
        if line:
            return False

        if ctx.continuation:
            ctx.apply()
        return True

    def __parse_continuation(self, ctx: Context, line: str) -> bool:
        if not ctx.continuation:
            return False

        m = Parser.VALUE.match(line)
        if not m:
            raise ParsingError(f"{ctx}: Malformed value")

        try:
            ctx.continue_assignment(m.group(1).strip(), bool(m.group(2)))
            return True
        except ContextError as ex:
            raise ParsingError(str(ex))

    def __parse_assignment(self, ctx: Context, line: str) -> bool:
        m = Parser.ASSIGNMENT.match(line)

        if not m:
            return False

        path: str = m.group(1)

        mode = AssignmentMode.from_str(m.group(2))
        if mode is None:
            raise ParsingError(f"{ctx}: Unknown assignment operator: '{mode}'")

        if mode == AssignmentMode.SET and self.set_is_replace:
            mode = AssignmentMode.REPLACE

        value = m.group(3)

        m = Parser.PATH.match(path)
        if not m:
            raise ParsingError(f"{ctx}: Invalid path: '{path}'")

        m = Parser.VALUE.match(value)
        if not m:
            raise ParsingError(f"{ctx}: Malformed value")

        value = m.group(1).strip()
        continues = bool(m.group(2))

        ctx.assign(path, value, mode, continues)
        return True

    def __parse_section(self, ctx: Context, line: str) -> bool:
        m = Parser.SECTION.match(line)
        if not m:
            return False

        path = m.group(1)

        if path:
            m = Parser.PATH.match(path)
            if not m:
                raise ParsingError(f"{ctx}: Invalid path: '{path}'")

            entry = ctx.cfg.get(path, create_intermediate=True)
            if entry is not None:
                if not isinstance(entry.value, Config):
                    raise ParsingError(f"{ctx}: Path '{path}' is already assigned")

        ctx.section = path
        return True

    def __load(self, io: IO, ctx_id: str, cfg: Config | None = None) -> Config:
        try:
            if cfg is None:
                cfg = Config()

            assert_type(cfg, Config, 'cfg')

            ctx: Final = Context(ctx_id, cfg)

            for line in io:
                ctx.increment_line_number()

                # Discard trailing comments and strip line.
                line = Parser.LINE.match(line).group(1).strip() # type: ignore

                if self.__parse_empty(ctx, line):
                    continue

                if self.__parse_continuation(ctx, line):
                    continue

                if self.__parse_assignment(ctx, line):
                    continue

                if self.__parse_section(ctx, line):
                    continue

                raise ParsingError(f"{ctx}: Malformed line")

            if ctx.continuation: # EOF without no empty line
                ctx.apply()

            return cfg
        except ContextError as ex:
            raise ParsingError(str(ex))

    def load_file(self, f: str, cfg: Config | None = None) -> Config:
        with open(f, 'r') as io:
            return self.__load(io, f, cfg)

    def load_str(self, s: str, cfg: Config | None = None, ctx_id: str = 'str') -> Config:
        return self.__load(StringIO(s), ctx_id, cfg)

    def batch_load_file(self, *files: str, cfg: Config | None = None) -> Config:
        if not files:
            raise ValueError(f'[files] Missing elements')

        _files = []

        try:
            for f in files:
                cfg = self.load_file(f, cfg)
                _files.append(f)

            # Due to assert len(files), it is sure cfg will not be None
            return cfg # type: ignore
        except Error as ex:
            raise ParsingError(f"{' > '.join(_files)} > {str(ex)}")

    def batch_load_str(self, *strings: str, cfg: Config | None = None, ctx_id_prefix = 'str#') -> Config:
        if not strings:
            raise ValueError(f'[strings] Missing elements')

        ctx_ids = []
        counter = 1
        try:
            for s in strings:
                ctx_id = f'{ctx_id_prefix}{counter}'
                cfg = self.load_str(s, cfg, ctx_id)
                ctx_ids.append(ctx_id)
                counter += 1

            # Due to assert len(files), it is sure cfg will not be None
            return cfg # type: ignore
        except Error as ex:
            raise ParsingError(f"{' > '.join(ctx_ids)} > {str(ex)}")
