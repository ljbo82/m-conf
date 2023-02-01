from __future__  import annotations
from dataclasses import dataclass
from enum        import Enum
from io          import StringIO
from pathlib     import Path
from typing      import Final, IO, Any
from .dict       import ReadOnlyDict

import re
import shlex

class ParsingError(Exception):
    pass

def load(
    *files:                 Path | str | tuple[str, str],
    enable_default_section: bool = False, # [] section is allowed or assignments before any section are allowed.
    allow_section_split:    bool = False, # Section is declared multiple times inside the same configuration.
    set_is_replace:         bool = False, # Do NOT raise an error on attempt to replace an existing value without explicit '!='
    allow_empty_values:     bool = False, # Allow a key being assigned to nothing? NOTE: Elements are delimited by any number of whitespaces, to it is not possible to have an empty element inside a list of values.
    avoid_list_values:      bool = False, # If there is a single element in the list of values, list will be replaced by its single element. If array is empty, it will be replaced by an empty string.
    nested_sections:        bool = False,  # 'dotted.key = value' is interpreted as  as 'key = value' inside section 'dotted'. '[dotted.section]' will result in `{'dotted': {'section': {...}}}`. NOTE: 'dotted.key = value' cannot replace section [dotted.key]
    str_prefix:             str = "str#",  # Prefix used for unamed string values. It will preceed string index
) -> dict:
    class Assignment(Enum):
        SET            = ('=')
        REPLACE        = ('!=')
        FALLBACK       = ('?=')
        APPEND         = ('+=')
        UNION          = ('^=')

        __map: dict[str, Assignment] = {}

        @classmethod
        def from_str(cls, assignment: str) -> Assignment | None:
            assert isinstance(assignment, str)
            return cls.__map.get(assignment)

        def __init__(self, assignment):
            self.__map[assignment] = self

    class Dict(dict):
        def __init__(self, section: str | None = None):
            super().__init__()
            self.__assignments: dict[str, Assignment] = {}
            self.__ro_assignments = ReadOnlyDict(self.__assignments)
            self.__section = section

        def __getitem__(self, key: str):
            assert isinstance(key, str)

            if not nested_sections:
                return super().__getitem__(key)

            tokens = key.split('.')
            v = None
            for i in range(0, len(tokens)):
                token = tokens[i]
                if v is not None and not isinstance(v, Dict):
                    raise KeyError()

                v = super().__getitem__(token) if v is None else v[token]

            return v

        def __setitem__(self, key: str, value: str | Dict):
            assert isinstance(key, str)
            assert isinstance(value, str) or isinstance(value, Dict)

            if not nested_sections:
                super().__setitem__(key, value)
                return

            tokens = key.split('.')
            d = None
            for i in range(0, len(tokens) - 1):
                token = tokens[i]
                if d is not None and not isinstance(d, Dict):
                    raise KeyError()

                if d is None:
                    d = super().get(token, None)
                    if d is None:
                        d = Dict(token)
                        super().__setitem__(token, d)
                else:
                    _d = d.get(token, None)
                    if _d is None:
                        _d = Dict(f"{d.section}.{token}")
                        d[token] = _d
                    d = _d


            if d is None:
                super().__setitem__(key, value)
            else:
                if not isinstance(d, Dict):
                    raise KeyError(f"'{'.'.join(tokens[:-1])}' is not a dict")

                d[tokens[-1]] = value

        def __delitem__(self, key: str):
            self.__assignments.pop(key, None)
            super().pop(key, None)

        def __raise(self, msg: str):
            if self.section:
                prefix = f"[{self.section}] "
            else:
                prefix = ""

            raise ParsingError(f"{prefix}{msg}")

        @property
        def assignments(self) -> dict:
            return self.__ro_assignments

        @property
        def section(self) -> str | None:
            return self.__section

        def update(self, other: Any = None, **kwargs: Any) -> None:
            assert isinstance(other, dict)

            for k, v in other.items():
                if isinstance(v, dict):
                    d = self.get(k, None)

                    if d is None:
                        self[k] = v
                        continue

                    d.update(v)
                    continue

                self.assign(k, v, Assignment.SET if not isinstance(other, Dict) else other.assignments[k])

        def assign(self, key: str, value: str, assignment: Assignment):
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert isinstance(assignment, Assignment)

            v = self.get(key, None)
            value = value.strip()

            if v is not None:
                match assignment:
                    case Assignment.SET:
                        if not set_is_replace:
                            if isinstance(v, Dict):
                                self.__raise(f"Cannot replace section '{v.section}' by a value")
                            else:
                                self.__raise(f"Value already set for key '{key}'")

                    case Assignment.REPLACE:
                        pass

                    case Assignment.FALLBACK:
                        return

                    case Assignment.APPEND:
                        if isinstance(v, Dict):
                            self.__raise(f"Cannot add a section ('{v.section}') to a value")

                        if not value and not allow_empty_values:
                            self.__raise(f"Attempt to append an empty value for key '{key}'")

                        value = v + " " + value

                    case Assignment.UNION:
                        # shlex properly handles quoted elements.
                        try:
                            existing_elements = shlex.split(v)
                            new_elements = shlex.split(value)
                        except ValueError as ex:
                            self.__raise(str(ex))

                        _new_elements = []
                        for new_element in new_elements:
                            if new_element not in existing_elements:
                                new_element = new_element.strip()
                                if not new_element and not allow_empty_values:
                                    self.__raise(f"Attempt to append an empty element for key '{key}'")

                                if new_element:
                                    #new_elements.append(new_element.replace(" ", "\\ "))
                                    _new_elements.append(shlex.quote(new_element))

                        existing_elements.extend(_new_elements)
                        value = " ".join(existing_elements)

                    case _:
                        raise NotImplementedError(f"Assignment not supported: {assignment}")

            value = value.strip()
            if not value and not allow_empty_values:
                self.__raise(f"Attempt to set an empty value for key '{key}'")

            self[key] = value
            self.__assignments[key] = assignment

        def explode(self) -> dict:
            d = {}
            for k, v in self.items():
                if isinstance(v, Dict):
                    d[k] = v.explode()
                    continue

                v = shlex.split(v)
                if avoid_list_values:
                    match len(v):
                        case 0:
                            v = ""

                        case 1:
                            v = v[0]

                        case _:
                            pass
                d[k] = v
            return d

    class Context:
        def __init__(self, file_path: str, d: Dict = Dict()):
            assert isinstance(file_path, str) and file_path
            assert isinstance(d, Dict)

            self.__d = d
            self.__line_number: int = 0
            self.__file_path: str = file_path
            self.__current_section: str | None = None
            self.__restore_section = None
            self.__reset()

        def __repr__(self):
            return f"{self.file_path}:{self.line_number}"

        def __reset(self):
            self.__current_key: str | None = None
            self.__current_value: str | None = None
            self.__current_assignment: Assignment | None = None
            self.__continuation: bool = False
            if self.__restore_section is not None:
                self.__current_section = self.__restore_section
                self.__restore_section = None

        def apply(self):
            assert enable_default_section or self.current_section

            try:
                d = self.d[self.current_section]
            except KeyError:
                d = Dict(self.current_section)
                self.d[self.current_section] = d

            if self.current_key is not None:
                assert isinstance(self.current_key, str)
                assert isinstance(self.current_value, str)
                assert self.current_assignment
                assert not self.continuation

                try:
                    d.assign(self.current_key, self.current_value, self.current_assignment)
                except ParsingError as ex:
                    raise ParsingError(f"{self}: {str(ex)}")

            self.__reset()

        def increment_line_number(self) -> int:
            self.__line_number += 1
            return self.__line_number

        def set_current_assignment(
            self,
            key: str,
            value: str,
            assignment: Assignment,
            continues: bool
        ):
            assert self.current_section is not None
            assert self.current_key is None
            assert self.current_value is None
            assert self.current_assignment is None
            assert self.continuation is False

            assert isinstance(key, str)
            assert isinstance(value, str)
            assert isinstance(assignment, Assignment)
            assert isinstance(continues, bool)

            self.__current_key = key
            self.__current_value = value
            self.__current_assignment = assignment
            self.__continuation = continues

            if not continues:
                self.apply()

        def continue_assignment(self, value: str, continues: bool):
            assert self.current_key is not None
            assert self.current_value is not None
            assert self.current_assignment is not None
            assert self.continuation

            assert isinstance(value, str)
            assert isinstance(continues, bool)

            if value:
                self.__current_value = self.current_value + " " + value.strip()

            self.__continuation = continues

            if not continues:
                self.apply()

        def set_nested_section(self, section: str):
            assert isinstance(section, str) and section
            assert self.current_section is not None
            assert self.__restore_section is None

            self.__restore_section = self.current_section
            self.__current_section = f"{self.current_section}.{section}"

            try:
                v = self.d[self.current_section]
                if not isinstance(v, Dict):
                    raise ParsingError(f"{self}: Key '{self.current_section}' is already assigned to a value")
            except KeyError:
                pass

        @property
        def d(self) -> Dict:
            return self.__d

        @property
        def current_key(self) -> str | None:
            return self.__current_key

        @property
        def current_assignment(self) -> Assignment | None:
            return self.__current_assignment

        @property
        def current_value(self) -> str | None:
            return self.__current_value

        @property
        def continuation(self) -> bool:
            return self.__continuation

        @property
        def line_number(self) -> int:
            return self.__line_number

        @property
        def file_path(self) -> str:
            return self.__file_path

        @property
        def current_section(self )-> str | None:
            return self.__current_section

        @current_section.setter
        def current_section(self, section: str):
            assert isinstance(section, str)
            assert self.__restore_section is None
            assert self.current_key is None
            assert self.current_assignment is None
            assert self.current_value is None

            if not section and not enable_default_section:
                raise ParsingError(f"{self}: Default/Empty section not allowed")

            self.__current_section = section
            try:
                v = self.d[section]
                if isinstance(v, Dict) and not allow_section_split:
                    raise ParsingError(f"{self}: Duplicate section: '{section}'")

                if not isinstance(v, Dict):
                    raise ParsingError(f"{self}: Key '{section}' is already assigned to a value")
            except KeyError:
                self.apply()

    # $1: Effective line. $2: Comment.
    LINE: Final = re.compile(r"^(.*?)(?:(?<!\\)(#.*))?$")

    # $1: Section name
    SECTION: Final = re.compile(r"^\[\s*(.*)\s*]$")

    # $1: Section name
    SECTION_NAME: Final = re.compile(r"^((?:\.?[\w-]+|\.?\*)*)$")

    # $1: Key. $2 Assignment operator. $3: Value
    ASSIGNMENT: Final = re.compile(r"^([^?!=+^\s]*)\s*(=|!=|\?=|\+=|\^=)\s*(.*)(\\?)$")

    # $1: Key
    KEY: Final = re.compile(r"^([\w-]+(?:\.[\w-]+)*)$")

    # $1: Value, $2: Continuation backlash
    VALUE: Final = re.compile(r"^((?:[^\\]|\\\\|\\\s|\\'|\\\")*)(\\?)$")

    def parse_empty(ctx: Context, line: str) -> bool:
        if line:
            return False

        if ctx.current_key:
            ctx.apply()

        return True

    def parse_continuation(ctx: Context, line: str) -> bool:
        if not ctx.continuation:
            return False

        m = VALUE.match(line)
        if not m:
            raise ParsingError(f"{ctx}: Malformed value")

        ctx.continue_assignment(m.group(1).strip(), bool(m.group(2)))

        return True

    def parse_assignment(ctx: Context, line: str) -> bool:
        m = ASSIGNMENT.match(line)

        if not m:
            return False

        if ctx.current_section is None:
            if not enable_default_section:
                raise ParsingError(f"{ctx}: Expected a section")

            parse_section(ctx, "[]")

        key: str = m.group(1)

        assignment = Assignment.from_str(m.group(2))
        if assignment is None:
            raise ParsingError(f"Unknown assignment: '{assignment}'")

        value = m.group(3)

        m = KEY.match(key)
        if not m:
            raise ParsingError(f"{ctx}: Invalid key: '{key}'")

        if '.' in key and nested_sections:
            tokens = key.split('.')
            key = tokens[-1]
            ctx.set_nested_section(".".join(tokens[:-1]))

        m = VALUE.match(value)
        if not m:
            raise ParsingError(f"{ctx}: Malformed value")

        value = m.group(1).strip()
        continues = bool(m.group(2))

        ctx.set_current_assignment(key, value, assignment, continues)
        return True

    def parse_section(ctx: Context, line: str) -> bool:
        m = SECTION.match(line)
        if not m:
            return False

        name = m.group(1)

        m = SECTION_NAME.match(name)
        if not m or (name.startswith('.') and not enable_default_section and not nested_sections):
            raise ParsingError(f"{ctx}: Invalid section name: '{name}'")

        ctx.current_section = name
        return True

    result: dict = Dict()
    parsed_files: list[str] = []
    str_count: int = 1
    io: IO | None = None

    try:
        for f in files:
            if isinstance(f, Path):
                ctx = Context(str(f), result)
                io = f.open("r")
            elif isinstance(f, str):
                assert isinstance(str_prefix, str)
                ctx = Context(f"{str_prefix}{str_count}", result)
                io = StringIO(f)
                str_count += 1
            elif isinstance(f, tuple):
                assert len(f) == 2
                assert isinstance(f[0], str)
                assert isinstance(f[1], str)
                ctx = Context(f"{f[1] if f[1] else f'{str_prefix}{str_count}'}", result)
                str_count +=1
                io = StringIO(f[0])
            else:
                raise ValueError(f"Invalid type for file: {type(f)}")

            for line in io:
                ctx.increment_line_number()

                # Discard trailing comments and strip line.
                line = LINE.match(line).group(1).strip() # type: ignore

                #Is line empty?
                if parse_empty(ctx, line):
                    continue

                if parse_continuation(ctx, line):
                    continue

                if parse_assignment(ctx, line):
                    continue

                if parse_section(ctx, line):
                    continue

                raise ParsingError(f"{ctx}: Malformed line")

            if ctx.continuation: # EOF without no empty line
                ctx.apply()

            io.close()

            parsed_files.append(ctx.file_path)

    except ParsingError as ex:
        msg = str(ex)

        if parsed_files:
            msg = f"{' > '.join(parsed_files)} > {msg}"

        raise ParsingError(msg)

    finally:
        if io is not None:
            io.close

    return result.explode()
