# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from .      import assert_exception
from m_conf import *

def test_default():
    cfg = Config()

    assert len(cfg) == 0
    assert cfg.key == ''
    assert cfg.parent is None
    assert cfg.path == ''

def test_construction_from_dict():
    cfg = Config({'abc': 'def'})
    assert cfg == {'abc': 'def'}
    assert cfg.assignment_mode('abc') == AssignmentMode.SET
    assert cfg['abc'] == 'def'

    cfg = Config({'abc': {'def': 'ghi'}})
    assert cfg == {'abc': {'def': 'ghi'}}

    assert cfg.assignment_mode('abc') == AssignmentMode.UNION
    assert cfg.assignment_mode('abc.def') == AssignmentMode.SET

    assert isinstance(cfg['abc'], Config)
    assert cfg['abc'] == {'def': 'ghi'}

    assert cfg['abc.def'] == 'ghi'

def test_path_must_be_a_string():
    cfg = Config()

    with assert_exception(TypeError, "[path] Invalid type: int"):
        cfg[12] = 'a' # type: ignore

def test_path_cannot_be_empty():
    cfg = Config()

    with assert_exception(PathError, 'Empty path'):
        cfg[''] = 'a'

def test_path_cannot_have_empty_sections():
    cfg = Config()

    with assert_exception(PathError, 'Invalid path'):
        cfg['a..b'] = 'a'

def test_entries_on_root_section():
    cfg = Config()

    cfg['key'] = 'value'
    assert cfg == {'key': 'value'}
    assert cfg.assignment_mode('key') == AssignmentMode.SET

def test_automatic_relativity():
    cfg = Config()

    cfg['nested.subsection.key'] = 'value'
    assert cfg == {'nested': {'subsection': {'key': 'value'}}}
    assert cfg.assignment_mode('nested.subsection.key') == AssignmentMode.SET
    assert cfg['nested.subsection.key'] == 'value'

    subsection = cfg['nested.subsection']
    assert isinstance(subsection, Config)
    assert cfg.assignment_mode('nested.subsection') == AssignmentMode.UNION
    assert subsection.assignment_mode('key') == AssignmentMode.SET
    assert subsection['key'] is cfg['nested.subsection.key']
    assert subsection == {'key': 'value'}
    assert subsection['key'] == 'value'

    nested = cfg['nested']
    assert isinstance(nested, Config)
    assert cfg.assignment_mode('nested') == AssignmentMode.UNION
    assert nested.assignment_mode('subsection') == AssignmentMode.UNION
    assert nested['subsection.key'] is cfg['nested.subsection.key']
    assert nested['subsection'] is subsection
    assert nested == {'subsection': {'key': 'value'}}

def test_del():
    cfg = Config()

    cfg['nested.subsection.key'] = 'value'
    assert cfg == {'nested': {'subsection': {'key': 'value'}}}
    assert cfg['nested.subsection.key'] is not None
    assert cfg.assignment_mode('nested.subsection.key') == AssignmentMode.SET
    assert cfg['nested.subsection'] is not None
    assert cfg.assignment_mode('nested.subsection') == AssignmentMode.UNION
    assert cfg['nested'] is not None
    assert cfg.assignment_mode('nested') == AssignmentMode.UNION

    del cfg['nested.subsection.key']
    assert cfg['nested.subsection.key'] is None
    assert cfg.assignment_mode('nested.subsection.key') is None
    assert cfg == {'nested': {'subsection': {}}}

    del cfg['nested.subsection']
    assert cfg['nested.subsection'] is None
    assert cfg.assignment_mode('nested.subsection') is None
    assert cfg == {'nested': {}}

    del cfg['nested']
    assert cfg['nested'] is None
    assert cfg.assignment_mode('nested') is None
    assert cfg == {}

def test_nested_sections_and_key_conflicts():
    cfg = Config()

    cfg['subsection.key'] = 'value'
    assert cfg == {'subsection': {'key': 'value'}}

    with assert_exception(PathError, "Path 'subsection.key' is already assigned"):
        cfg['subsection.key.sub'] = 'value'

    cfg.clear()
    assert len(cfg) == 0
    assert cfg == {}

    cfg['nested.subsection.key'] = 'value'
    assert cfg == {'nested': {'subsection': {'key': 'value'}}}

    with assert_exception(AssignmentError, "Path 'nested.subsection' is already assigned"):
        cfg['nested.subsection'] = 'value'

    del cfg['nested.subsection']
    cfg['nested.subsection'] = 'value'
    assert cfg == {'nested': {'subsection': 'value'}}

def test_assign_set_cannot_replace():
    cfg = Config()
    cfg['key'] = 'value'

    with assert_exception(AssignmentError, "Path 'key' is already assigned"):
        cfg['key'] = 'another'

def test_get_create_intermediate():
    cfg = Config()
    assert cfg == {}

    assert cfg.get('some.nested.section.key') is None
    assert cfg == {}

    assert cfg.get('some.nested.section.key', create_intermediate=True) is None
    assert cfg == {'some': {'nested': {'section': {}}}}

    cfg.clear()
    assert cfg == {}

def test_assign_set_default():
    cfg = Config()
    cfg.assign('key', 'value')

    assert cfg.assignment_mode('key') == AssignmentMode.SET
    assert cfg == {'key': 'value'}

    with assert_exception(AssignmentError, "Path 'key' is already assigned"):
        cfg.assign('key', 'another value')

    del cfg['key']
    cfg.assign('key', 'another value')
    assert cfg == {'key': 'another value'}

def test_assign_str_explode():
    cfg = Config()
    cfg.assign('key', 'one two three', explode_value=True)
    assert cfg == {'key': ['one', 'two', 'three']}

    cfg.clear()
    cfg.assign('key', "one two\\ three", explode_value=True)
    assert cfg == {'key': ['one', 'two three']}

def test_assign_set_explicitly():
    cfg = Config()
    cfg.assign('key', 'value', AssignmentMode.SET)

    assert cfg.assignment_mode('key') == AssignmentMode.SET
    assert cfg == {'key': 'value'}

    with assert_exception(AssignmentError, "Path 'key' is already assigned"):
        cfg.assign('key', 'another value', AssignmentMode.SET)

    del cfg['key']
    cfg.assign('key', 'another value', AssignmentMode.SET)
    assert cfg == {'key': 'another value'}

def test_assign_set_list_trim_elements():
    cfg = Config()
    cfg.assign('key', ['  value one  ', '   value two   '], AssignmentMode.SET)

    # Values are trimmed
    assert cfg == {'key': ['value one', 'value two']}

def test_assign_set_list_invalid_element():
    cfg = Config()

    with assert_exception(TypeError, 'Non-string element at index 1'):
        cfg.assign('key', ['  value one  ', 2], AssignmentMode.SET) # type: ignore (purpose of test is just to check issue)

def test_assign_replace():
    cfg = Config()
    assert cfg.assign('key', 'value', AssignmentMode.SET)

    assert cfg.assignment_mode('key') == AssignmentMode.SET

    assert cfg.assign('key', 'another value', AssignmentMode.REPLACE)
    assert cfg.assignment_mode('key') == AssignmentMode.REPLACE
    assert cfg == {'key': 'another value'}

def test_assign_append_first_is_list():
    cfg = Config()
    assert cfg.assign('key', 'value', AssignmentMode.APPEND)

    assert cfg.assignment_mode('key') == AssignmentMode.APPEND
    assert cfg == {'key': ['value']}

    assert cfg.assign('key', 'value', AssignmentMode.APPEND)
    assert cfg.assignment_mode('key') == AssignmentMode.APPEND
    assert cfg == {'key': ['value', 'value']}

def test_assign_fallback():
    cfg = Config()
    cfg['key'] = 'value'
    assert not cfg.assign('key', 'another', AssignmentMode.FALLBACK)
    assert cfg == {'key': 'value'}
    assert cfg.assignment_mode('key') == AssignmentMode.SET

def test_assign_union_str():
    cfg = Config()
    value = 'value'
    alt_value = "".join(["val", "ue"])
    assert value == alt_value
    assert not value is alt_value

    cfg['key'] = value
    assert cfg.assign('key', [alt_value, 'another'], AssignmentMode.UNION)
    assert cfg == {'key': ['value', 'another']}
    assert cfg['key'][0] == value #type: ignore
    assert cfg['key'][0] == alt_value #type: ignore
    assert cfg['key'][0] is value # type: ignore
    assert cfg['key'][0] is not alt_value # type: ignore

def test_assign_union_list():
    cfg = Config()
    value1 = 'value1'
    alt_value1 = "".join(["val", "ue1"])

    value2 = 'value2'
    alt_value2 = "".join(["val", "ue2"])

    assert value1 != value2

    assert value1 == alt_value1
    assert not value1 is alt_value1

    assert value2 == alt_value2
    assert not value2 is alt_value2

    cfg['key'] = [value1, value2]

    assert cfg.assign('key', [alt_value1, alt_value2, 'another'], AssignmentMode.UNION)
    assert cfg == {'key': ['value1', 'value2', 'another']}

    assert cfg['key'][0] == value1 #type: ignore
    assert cfg['key'][0] == alt_value1 #type: ignore
    assert cfg['key'][0] is value1 # type: ignore
    assert cfg['key'][0] is not alt_value1 # type: ignore

    assert cfg['key'][1] == value2 #type: ignore
    assert cfg['key'][1] == alt_value2 #type: ignore
    assert cfg['key'][1] is value2 # type: ignore
    assert cfg['key'][1] is not alt_value2 # type: ignore

def test_assign_union_list_no_new_elements():
    cfg = Config()
    value1 = 'value1'
    alt_value1 = "".join(["val", "ue1"])

    value2 = 'value2'
    alt_value2 = "".join(["val", "ue2"])

    assert value1 != value2

    assert value1 == alt_value1
    assert not value1 is alt_value1

    assert value2 == alt_value2
    assert not value2 is alt_value2

    cfg['key'] = [value1, value2]

    assert not cfg.assign('key', [alt_value1, alt_value2], AssignmentMode.UNION)
    assert cfg == {'key': ['value1', 'value2']}

    assert cfg['key'][0] == value1 #type: ignore
    assert cfg['key'][0] == alt_value1 #type: ignore
    assert cfg['key'][0] is value1 # type: ignore
    assert cfg['key'][0] is not alt_value1 # type: ignore

    assert cfg['key'][1] == value2 #type: ignore
    assert cfg['key'][1] == alt_value2 #type: ignore
    assert cfg['key'][1] is value2 # type: ignore
    assert cfg['key'][1] is not alt_value2 # type: ignore
