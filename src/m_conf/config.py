
# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from __future__  import annotations
from enum        import Enum
from io          import StringIO
from typing      import Final, IO, Any

import re
import shlex

class Parser:
    class Error(Exception):
        pass

    class AssignmentMode(Enum):
        SET            = ('=')
        REPLACE        = ('!=')
        FALLBACK       = ('?=')
        APPEND         = ('+=')
        UNION          = ('^=')

        __map: dict[str, Parser.AssignmentMode] = {}

        @classmethod
        def from_str(cls, assignment: str) -> Parser.AssignmentMode | None:
            assert isinstance(assignment, str)
            return cls.__map.get(assignment)

        def __init__(self, assignment):
            self.__map[assignment] = self

    class Dict(dict):
        def __init__(self, parser: Parser, section: str = "", d: dict[str, Any] = {}):
            assert isinstance(parser, Parser)
            assert isinstance(section, str)
            assert isinstance(d, dict)

            self.__parser = parser
            self.__section = section

            if d and not isinstance(d, Parser.Dict):
                _d = Parser.Dict(parser, section)
                _d.update(d)
                d = _d

            super().__init__(d)

        def __getitem__(self, key: str):
            if not self.parser.nested_sections:
                return super().__getitem__(key)

            tokens = key.split('.')
            v = None
            for i in range(0, len(tokens)):
                token = tokens[i]
                if v is not None and not isinstance(v, Parser.Dict):
                    raise KeyError()

                v = super().__getitem__(token) if v is None else v[token]

            return v

        def __setitem__(self, key: str, value: str | list[str] | Parser.Dict):
            assert isinstance(key, str)
            assert isinstance(value, (str, list, Parser.Dict))

            key = key.strip()
            if not key:
                assert self.parser.enable_default_section
                assert isinstance(value, Parser.Dict)

            if isinstance(value, str):
                value = [v.strip() for v in shlex.split(value.strip())]

                _len = len(value)
                if _len == 0 or _len == 1:
                    value = '' if not _len else value[0]

                if not value and not self.parser.allow_empty_values:
                    raise Parser.Error('Empty value')

            elif isinstance(value, list):
                invalid = next((i for i, x in enumerate(value) if not isinstance(x, str)), None)

                if invalid is not None:
                    raise ValueError(f'Non string element at index {invalid}')

                value = [v.strip() for v in value]

            if isinstance(value, list) and not self.parser.allow_empty_values and '' in value:
                raise Parser.Error(f"Empty element at index {value.index('')}")

            if not self.parser.nested_sections:
                super().__setitem__(key, value)
                return

            tokens = key.split('.')
            d = None
            for i in range(0, len(tokens) - 1):
                token = tokens[i].strip()
                assert token or (i == 0 and self.parser.enable_default_section)

                if d is not None and not isinstance(d, Parser.Dict):
                    raise KeyError()

                if d is None:
                    d = super().get(token, None)
                    if d is None:
                        d = Parser.Dict(self.parser, token)
                        super().__setitem__(token, d)
                else:
                    _d = d.get(token, None)
                    if _d is None:
                        _d = Parser.Dict(self.parser, f"{d.section}.{token}")
                        d[token] = _d
                    d = _d

            if d is None:
                super().__setitem__(key, value)
            else:
                if not isinstance(d, Parser.Dict):
                    raise KeyError(f"'{'.'.join(tokens[:-1])}' is not a dict")

                d[tokens[-1]] = value

        def __delitem__(self, key: str):
            super().pop(key, None)

        @property
        def parser(self) -> Parser:
            return self.__parser

        @property
        def section(self) -> str:
            return self.__section

        def update(self, other: Any = None, **kwargs: Any) -> None:
            assert isinstance(other, dict)

            for k, v in other.items():
                assert isinstance(k, str)
                assert isinstance(v, (str, list, dict))

                if isinstance(v, (str, list)):
                    self[k] = v
                else:
                    self[k] = v if isinstance(v, Parser.Dict) else Parser.Dict(self.parser, f'{self.section}.{k}', v)

        def assign(self, key: str, value: str | list[str], mode: Parser.AssignmentMode):
            assert isinstance(key, str)
            assert isinstance(value, (str, list))
            assert isinstance(mode, Parser.AssignmentMode)

            key = key.strip()

            if isinstance(value, str):
                value = [v.strip() for v in shlex.split(value.strip())]

                _len = len(value)
                if _len == 0 or _len == 1:
                    value = '' if not _len else value[0]

                if not value and not self.parser.allow_empty_values:
                    raise Parser.Error('Empty value')

            elif isinstance(value, list):
                invalid = next((i for i, x in enumerate(value) if not isinstance(x, str)), None)

                if invalid is not None:
                    raise ValueError(f'Non string element at index {invalid}')

                value = [v.strip() for v in value]

            if isinstance(value, list) and not self.parser.allow_empty_values and '' in value:
                raise Parser.Error(f"Empty element at index {value.index('')}")

            v = self.get(key, None)

            # Key is alreay present in self...
            if v is not None:
                match mode:
                    case Parser.AssignmentMode.SET:
                        if not self.parser.set_is_replace:
                            if isinstance(v, Parser.Dict):
                                raise Parser.Error(f"Cannot replace section '{v.section}' by a value")
                            else:
                                prefix = "" if not self.section else f"[{self.section}] "
                                raise Parser.Error(f"{prefix}Value already set for key '{key}'")

                        self[key] = value

                    case Parser.AssignmentMode.REPLACE:
                        self[key] = value

                    case Parser.AssignmentMode.FALLBACK:
                        pass

                    case Parser.AssignmentMode.APPEND:
                        if isinstance(v, Parser.Dict):
                            raise Parser.Error(f"Cannot add a value to section '{v.section}' without a key")

                        if isinstance(v, str):
                            v = [v] # Promote string to a list
                            super().__setitem__(key, v)

                        v.extend(value if isinstance(value, list) else [value])

                    case Parser.AssignmentMode.UNION:
                        if isinstance(v, Parser.Dict):
                            raise Parser.Error(f"Cannot add a value to section '{v.section}' without a key")

                        if isinstance(v, str):
                            v = [v] # Promote string to a list
                            super().__setitem__(key, v)

                        _new_elements = []
                        for new_element in value if isinstance(value, list) else [value]:
                            if new_element not in v:
                                _new_elements.append(new_element)

                        v.extend(_new_elements)

                    case _:
                        raise NotImplementedError(f"AssignmentMode not supported: {mode}")
                return

            # Key is not present in self...
            match mode:
                case Parser.AssignmentMode.APPEND | Parser.AssignmentMode.UNION:
                    self[key] = [value] if isinstance(value, str) else value

                case Parser.AssignmentMode.SET | Parser.AssignmentMode.REPLACE | Parser.AssignmentMode.FALLBACK:
                    self[key] = value

                case _:
                    raise NotImplementedError()

    class Context:
        def __init__(self, ctx_id: str, d: Parser.Dict):
            assert isinstance(ctx_id, str) and ctx_id
            assert isinstance(d, Parser.Dict)

            self.__d = d
            self.__line_number: int = 0
            self.__ctx_id: str = ctx_id
            self.__section: str | None = None
            self.__restore_section = None
            self.__reset()

        def __repr__(self):
            return f"{self.ctx_id}:{self.line_number}"

        @property
        def parser(self) -> Parser:
            return self.d.parser

        @property
        def d(self) -> Parser.Dict:
            return self.__d

        @property
        def key(self) -> str | None:
            return self.__key

        @property
        def assignment_mode(self) -> Parser.AssignmentMode | None:
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
        def ctx_id(self) -> str:
            return self.__ctx_id

        @property
        def section(self )-> str | None:
            return self.__section

        @section.setter
        def section(self, section: str):
            assert isinstance(section, str)
            assert self.__restore_section is None
            assert self.key is None
            assert self.assignment_mode is None
            assert self.value is None

            if not section and not self.parser.enable_default_section:
                raise Parser.Error(f"{self}: Default/Empty section not allowed")

            self.__section = section
            try:
                v = self.d[section]
                if isinstance(v, Parser.Dict) and not self.parser.allow_section_split:
                    raise Parser.Error(f"{self}: Duplicate section: '{section}'")

                if not isinstance(v, Parser.Dict):
                    raise Parser.Error(f"{self}: Key '{section}' is already assigned to a value")
            except KeyError:
                self.apply()

        def __reset(self):
            self.__key: str | None = None
            self.__value: str | None = None
            self.__assignment_mode: Parser.AssignmentMode | None = None
            self.__continuation: bool = False
            if self.__restore_section is not None:
                self.__section = self.__restore_section
                self.__restore_section = None

        def apply(self):
            assert self.section is not None
            assert self.parser.enable_default_section or self.section

            try:
                d = self.d[self.section]
                assert isinstance(d, Parser.Dict)
            except KeyError:
                d = Parser.Dict(self.parser, self.section)
                self.d[self.section] = d

            if self.key is not None:
                assert isinstance(self.key, str)
                assert isinstance(self.value, str)
                assert self.assignment_mode
                assert not self.continuation

                try:
                    d.assign(self.key, self.value, self.assignment_mode)
                except Parser.Error as ex:
                    raise Parser.Error(f"{self}: {str(ex)}")

            self.__reset()

        def increment_line_number(self) -> int:
            self.__line_number += 1
            return self.__line_number

        def assign(self, key: str, value: str, mode: Parser.AssignmentMode, continues: bool):
            assert self.section is not None
            assert self.key is None
            assert self.value is None
            assert self.assignment_mode is None
            assert self.continuation is False

            assert isinstance(key, str)
            assert isinstance(value, str)
            assert isinstance(mode, Parser.AssignmentMode)
            assert isinstance(continues, bool)

            self.__key = key
            self.__value = value
            self.__assignment_mode = mode
            self.__continuation = continues

            if not continues:
                self.apply()

        def continue_assignment(self, value: str, continues: bool):
            assert self.key is not None
            assert self.value is not None
            assert self.assignment_mode is not None
            assert self.continuation

            assert isinstance(value, str)
            assert isinstance(continues, bool)

            value = value.strip()

            if value:
                self.__value = f"{self.value} {value.strip()}"

            self.__continuation = continues

            if not continues:
                self.apply()

        def set_nested_section(self, section: str):
            assert isinstance(section, str) and section
            assert self.section is not None
            assert self.__restore_section is None

            self.__restore_section = self.section
            self.__section = f"{self.section}.{section}"

            try:
                v = self.d[self.section]
                if not isinstance(v, Parser.Dict):
                    raise Parser.Error(f"{self}: Key '{self.section}' is already assigned to a value")
            except KeyError:
                pass

    # $1: Effective line. $2: Comment.
    LINE: Final = re.compile(r"^(.*?)(?:(?<!\\)(#.*))?$")

    # $1: Section name
    SECTION: Final = re.compile(r"^\[\s*(.*)\s*]$")

    # $1: Section name
    SECTION_NAME: Final = re.compile(r"^((?:\.?[\w-]+|\.?\*)*)$")

    # $1: Key. $2 Assignmen operator. $3: Value
    ASSIGNMENT: Final = re.compile(r"^([^?!=+^\s]*)\s*(=|!=|\?=|\+=|\^=)\s*(.*)(\\?)$")

    # $1: Key
    KEY: Final = re.compile(r"^([\w-]+(?:\.[\w-]+)*)$")

    # $1: Value, $2: Continuation backlash
    VALUE: Final = re.compile(r"^((?:[^\\]|\\\\|\\\s|\\'|\\\")*)(\\?)$")

    def __init__(
            self,
            enable_default_section: bool = False, # [] section is allowed or assignments before any section are allowed.
            allow_section_split:    bool = False, # Section is declared multiple times inside the same configuration.
            set_is_replace:         bool = False, # Do NOT raise an error on attempt to replace an existing value without explicit '!='
            allow_empty_values:     bool = False, # Allow a key being assigned to nothing?
            nested_sections:        bool = False  # 'dotted.key = value' is interpreted as  as 'key = value' inside section 'dotted'. '[dotted.section]' will result in `{'dotted': {'section': {...}}}`. NOTE: 'dotted.key = value' cannot replace section [dotted.key]) -> None:
    ):
        self.__enable_default_section = enable_default_section
        self.__allow_section_split = allow_section_split
        self.__set_is_replace = set_is_replace
        self.__allow_empty_values = allow_empty_values
        self.__nested_sections = nested_sections

    @property
    def enable_default_section(self) -> bool:
        return self.__enable_default_section

    @property
    def allow_section_split(self) -> bool:
        return self.__allow_section_split

    @property
    def set_is_replace(self) -> bool:
        return self.__set_is_replace

    @property
    def allow_empty_values(self) -> bool:
        return self.__allow_empty_values

    @property
    def nested_sections(self) -> bool:
        return self.__nested_sections

    def __parse_empty(self, ctx: Parser.Context, line: str) -> bool:
        if line:
            return False

        if ctx.key:
            ctx.apply()

        return True

    def __parse_continuation(self, ctx: Parser.Context, line: str) -> bool:
        if not ctx.continuation:
            return False

        m = Parser.VALUE.match(line)
        if not m:
            raise Parser.Error(f"{ctx}: Malformed value")

        ctx.continue_assignment(m.group(1).strip(), bool(m.group(2)))

        return True

    def __parse_assignment(self, ctx: Parser.Context, line: str) -> bool:
        m = Parser.ASSIGNMENT.match(line)

        if not m:
            return False

        if ctx.section is None:
            if not self.enable_default_section:
                raise Parser.Error(f"{ctx}: Expected a section")

            self.__parse_section(ctx, "[]")

        key: str = m.group(1)

        mode = Parser.AssignmentMode.from_str(m.group(2))
        if mode is None:
            raise Parser.Error(f"Unknown assignment operator: '{mode}'")

        value = m.group(3)

        m = Parser.KEY.match(key)
        if not m:
            raise Parser.Error(f"{ctx}: Invalid key: '{key}'")

        if '.' in key and self.nested_sections:
            tokens = key.split('.')
            key = tokens[-1]
            ctx.set_nested_section(".".join(tokens[:-1]))

        m = Parser.VALUE.match(value)
        if not m:
            raise Parser.Error(f"{ctx}: Malformed value")

        value = m.group(1).strip()
        continues = bool(m.group(2))

        ctx.assign(key, value, mode, continues)
        return True

    def __parse_section(self, ctx: Parser.Context, line: str) -> bool:
        m = Parser.SECTION.match(line)
        if not m:
            return False

        name = m.group(1)

        m = Parser.SECTION_NAME.match(name)
        if not m or (name.startswith('.') and not self.enable_default_section and not self.nested_sections):
            raise Parser.Error(f"{ctx}: Invalid section name: '{name}'")

        ctx.section = name
        return True

    def __load(self, io: IO, ctx_id: str, d: dict = {}) -> dict:
        result: Final = Parser.Dict(self, d=d)
        ctx: Final = Parser.Context(ctx_id, result)

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

            raise Parser.Error(f"{ctx}: Malformed line")

        if ctx.continuation: # EOF without no empty line
            ctx.apply()

        return result

    def load_file(self, f: str, d: dict = {}) -> dict:
        with open(f, 'r') as io:
            return self.__load(io, f, d)

    def load_str(self, s: str, d: dict = {}, ctx_id: str = 'str') -> dict:
        return self.__load(StringIO(s), ctx_id, d)

    def batch_load_file(self, *files: str, d: dict = {}) -> dict:
        _files = []
        result = Parser.Dict(self)
        try:
            for f in files:
                result = self.load_file(f, result)
                _files.append(f)

            return result
        except Parser.Error as ex:
            raise Parser.Error(f"{' > '.join(_files)} > {str(ex)}")

    def batch_load_str(self, *strings: str, d: dict = {}, ctx_id_prefix = 'str#') -> dict:
        ctx_ids = []
        counter = 1
        result = Parser.Dict(self)
        try:
            for s in strings:
                ctx_id = f'{ctx_id_prefix}{counter}'
                result = self.load_str(s, result, ctx_id)
                ctx_ids.append(ctx_id)
                counter += 1

            return result
        except Parser.Error as ex:
            raise Parser.Error(f"{' > '.join(ctx_ids)} > {str(ex)}")
