# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from .      import assert_exception
from m_conf import *

def test_from_str():
    assert AssignmentMode.from_str('=') is AssignmentMode.SET
    assert AssignmentMode.from_str('!=') is AssignmentMode.REPLACE
    assert AssignmentMode.from_str('?=') is AssignmentMode.FALLBACK
    assert AssignmentMode.from_str('+=') is AssignmentMode.APPEND
    assert AssignmentMode.from_str('^=') is AssignmentMode.UNION

    assert AssignmentMode.from_str('!!=') is None

def test_from_str_arg_type():
    with assert_exception(TypeError, "[assignment] Invalid type: None"):
        AssignmentMode.from_str(None) # type: ignore
