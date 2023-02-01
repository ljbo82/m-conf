# Copyright (c) 2023 Leandro José Britto de Oliveira
# Licensed under the MIT License.

class ReadOnlyDict(dict):
    def __init__(self, wrapped: dict):
        assert isinstance(wrapped, dict)
        self.__wrapped = wrapped

    def __getitem__(self, key):
        return self.__wrapped[key]

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def __ior__(self, other):
        raise NotImplementedError()

    def update(self, *args, **kwargs):
        raise NotImplementedError()
