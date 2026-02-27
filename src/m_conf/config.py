# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from __future__       import annotations
from .assignment_mode import AssignmentMode
from .error           import *
from dataclasses      import dataclass
from typing           import Any

import shlex

class Config(dict):
    @dataclass(frozen=True)
    class Entry:
        key: str
        value: str | list[str] | Config
        section: Config

        @property
        def path(self):
            return self.key if not self.section.path else f"{self.section.path}.{self.key}"

    def __init__(self, d: dict[str, Any] | None = None, *, parent: Config | None = None, key: str = ''):
        if d is None:
            d = {}

        assert_type (d, dict, 'd')
        assert_type(parent, (Config, type(None)), 'parent')
        assert_type(key, str, 'key')

        assert (key and parent is not None) or (not key and parent is None)

        self.__parent = parent
        self.__key = key
        self.__assignment_mode: dict[str, AssignmentMode] = {}

        self.update(d)

    def __getitem__(self, path: str) -> str | list[str] | Config | None:
        entry = self.get(path)
        if entry is None:
            return None

        return entry.value

    def __setitem__(self, path: str, value: str | list[str]):
        self.assign(path, value)

    def __delitem__(self, path: str):
        self.del_item(path)

    @property
    def parent(self) -> Config | None:
        return self.__parent

    @property
    def key(self) -> str:
        return self.__key

    @property
    def path(self) -> str:
        path = []
        cfg = self
        while cfg is not None and cfg.key:
            path.insert(0, cfg.key)
            cfg = cfg.parent

        return '.'.join(path)

    def assignment_mode(self, path: str) -> AssignmentMode | None:
        assert_type(path, str, 'path')

        entry = self.get(path)

        if entry is None:
            return None

        return entry.section.__assignment_mode[entry.key]

    def __super_setitem(self, key, value):
        super().__setitem__(key, value)

    def __super_get(self, key, default):
        return super().get(key, default)

    def __super_delitem(self, key):
        super().__delitem__(key)

    def get(self, path: str, *, create_intermediate:bool = False) -> Config.Entry | None: # type: ignore
        assert_type(create_intermediate, bool, 'create_intermediate')
        assert_type(path, str, 'path')

        path = path.strip()

        if not path:
            raise PathError('Empty path')

        v = None
        section = self
        _path = ''
        tokens = path.split('.')
        token = ''
        last_token_index = len(tokens) - 1

        for i in range(0, last_token_index + 1):
            token = tokens[i]

            if not token:
                raise PathError('Invalid path')

            _path = token if not _path else f"{_path}.{token}"

            v = section.__super_get(token, None)

            if v is None:
                if not create_intermediate or i == last_token_index:
                    return None

                v = Config(parent=section, key=token)
                section.__super_setitem(token, v)
                section.__assignment_mode[token] = AssignmentMode.UNION

            if i != last_token_index:
                if not isinstance(v, Config):
                    raise PathError(f"Path '{_path}' is already assigned")

                section = v

        if v is None:
            return None

        return Config.Entry(token, v, section)

    def del_item(self, path: str) -> bool:
        entry = self.get(path)

        if entry is None:
            return False

        entry.section.__super_delitem(entry.key)
        del entry.section.__assignment_mode[entry.key]
        return True

    def update(self, other: dict | None = None): # type: ignore
        assert_type(other, dict, 'other')

        for k, v in other.items(): # type: ignore
            assert_type(k, str, f"other[{k}]", f"Invalid key type: {type(k).__name__ }")
            assert_type(v, (str, list, dict), f"other[{k}]", f"Invalid value type: {type(v).__name__ }")

            if isinstance(v, (str, list)):
                self.assign(k, v, AssignmentMode.SET if not isinstance(other, Config) else other.assignment_mode(k)) # type: ignore (if there is a value, there is an associated assignment_mode)
            else:
                d = self.get(k)
                if d is None:
                    v = Config(v, parent=self, key=k)
                    self.__super_setitem(k, v)
                    self.__assignment_mode[k] = AssignmentMode.UNION
                else:
                    if not isinstance(d, Config):
                        raise AssignmentError(f"Path '{self.path}' is already assigned")
                    d.update(v)

    def assign(self, path: str, value: str | list[str], mode: AssignmentMode = AssignmentMode.SET, explode_value: bool = False) -> bool:
        assert_type(path, str, 'path')
        assert_type(value, (str, list), 'value')
        assert_type(mode, AssignmentMode, 'mode')

        if isinstance(value, str):
            value = value.strip()
            if explode_value:
                value = [v.strip().replace('\\n', '\n') for v in shlex.split(value)]

                _len = len(value)
                if _len == 0 or _len == 1:
                    value = '' if not _len else value[0]

        elif isinstance(value, list):
            invalid = next((i for i, x in enumerate(value) if not isinstance(x, str)), None)

            if invalid is not None:
                raise TypeError(f'Non-string element at index {invalid}')

            value = [v.strip() for v in value]

        entry = self.get(path, create_intermediate=True)

        # Key is already present...
        if entry is not None:
            match mode:
                case AssignmentMode.SET:
                    raise AssignmentError(f"Path '{path}' is already assigned")

                case AssignmentMode.REPLACE:
                    entry.section.__super_setitem(entry.key, value)

                case AssignmentMode.FALLBACK:
                    return False

                case AssignmentMode.APPEND:
                    if isinstance(entry.value, Config):
                        raise AssignmentError(f"Path '{path}' points to a section")

                    if isinstance(entry.value, str):
                        # Promote string to a list
                        entry = Config.Entry(entry.key, [entry.value], entry.section)
                        entry.section.__super_setitem(entry.key, entry.value)

                    entry.value.extend(value if isinstance(value, list) else [value]) # type: ignore

                case AssignmentMode.UNION:
                    if isinstance(entry.value, Config):
                        raise AssignmentError(f"Path '{path}' points to a section")

                    if isinstance(entry.value, str):
                        # Promote string to a list
                        entry = Config.Entry(entry.key, [entry.value], entry.section)
                        entry.section.__super_setitem(entry.key, entry.value)

                    _new_elements = []
                    for new_element in value if isinstance(value, list) else [value]:
                        if new_element not in entry.value:
                            _new_elements.append(new_element)

                    if len(_new_elements) == 0:
                        return False
                    entry.value.extend(_new_elements) # type: ignore

                case _:
                    raise NotImplementedError(f"AssignmentMode not supported: {mode}")

            entry.section.__assignment_mode[entry.key] = mode
            return True

        # Key is not present...
        tokens = path.split('.')
        key = tokens[-1]
        parent_section_path = '.'.join(tokens[:-1])

        if not parent_section_path:
            section = self
        else:
            entry = self.get(parent_section_path, create_intermediate=True)
            assert entry is not None
            section = entry.value

        match mode:
            case AssignmentMode.APPEND | AssignmentMode.UNION:
                value = [value] if isinstance(value, str) else value

            case AssignmentMode.SET | AssignmentMode.REPLACE | AssignmentMode.FALLBACK:
                pass

            case _:
                raise NotImplementedError()

        section.__super_setitem(key, value) # type: ignore
        section.__assignment_mode[key] = mode # type: ignore
        return True
