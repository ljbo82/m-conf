# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from m_conf.config import Parser
import os
import pytest

@pytest.fixture(scope='module')
def cwd():
    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    yield
    os.chdir(cwd)
    print()

def test_config_single():
    cfg = """ \
    [section]
    key1 = value1
    """

    d = Parser().load_str(cfg)
    assert d == {'section': {'key1': 'value1'}}

def test_config_multiple():
    cfg1 = """
    [section1]
    key1 = value1
    """

    cfg2 = """
    [section2]
    key2 = value2
    """

    d = Parser().batch_load_str(cfg1, cfg2)
    assert d == {'section1': {'key1': 'value1'}, 'section2': {'key2': 'value2'}}

def test_config_single_from_file(cwd):
    d = Parser().load_file('configs/valid/001.cfg')
    assert d == {'section': {'key1': 'value1'}}

def test_config_multiple_from_file(cwd):
    d = Parser().batch_load_file('configs/valid/002/001.cfg', 'configs/valid/002/002.cfg')
    assert d == {'section1': {'key1': 'value1'}, 'section2': {'key2': 'value2'}}

def test_config_single_invalid_from_file(cwd):
    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_file('configs/invalid/001.cfg')

    assert 'configs/invalid/001.cfg:1: Expected a section' == str(ex_info.value)

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True).load_file('configs/invalid/001.cfg')

    assert "configs/invalid/001.cfg:3: Duplicate section: ''" == str(ex_info.value)

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True, allow_section_split=True).load_file('configs/invalid/001.cfg')

    assert "configs/invalid/001.cfg:4: Value already set for key 'key'" == str(ex_info.value)

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True, allow_section_split=True, set_is_replace=True).load_file('configs/invalid/001.cfg')

    assert "configs/invalid/001.cfg:5: Empty value" == str(ex_info.value)

    d = Parser(enable_default_section=True, allow_section_split=True, set_is_replace=True, allow_empty_values=True).load_file('configs/invalid/001.cfg')
    assert d == {
        '': {
            'key': ['another', 'value'],
            'empty': ''
        }
    }

def test_config_multiple_invalid_from_file(cwd):
    files = ('configs/invalid/002/001.cfg','configs/invalid/002/002.cfg')
    with pytest.raises(Parser.Error) as ex_info:
        Parser().batch_load_file(*files)

    assert "configs/invalid/002/001.cfg > configs/invalid/002/002.cfg:3: Empty value" == str(ex_info.value)

    d = Parser(allow_empty_values=True).batch_load_file(*files)
    assert d == {
        'section1': {
            'key1': 'value1'
        },
        'section2': {
            'key2': 'value2',
            'empty': ''
        }
    }

def test_config_context_str():
    cfg = """ \
    [section]
    key = value
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser().batch_load_str(cfg, cfg)

    assert "str#1 > str#2:1: Duplicate section: 'section'" == str(ex_info.value)

def test_config_context_str_custom_prefix():
    cfg = """ \
    [section]
    key = value
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser().batch_load_str(cfg, cfg, ctx_id_prefix="cfg-")

    assert "cfg-1 > cfg-2:1: Duplicate section: 'section'" == str(ex_info.value)

def test_config_single_explicit_default_section():
    cfg = """ \
    []
    key = value
    """
    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_str(cfg)
    assert 'str:1: Default/Empty section not allowed' == str(ex_info.value)

    d = Parser(enable_default_section=True).load_str(cfg)
    assert d == {'': {'key': 'value'}}

def test_config_single_implicity_default_section():
    cfg = """ \
    key = value
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_str(cfg)
    assert 'str:1: Expected a section' == str(ex_info.value)

    d = Parser(enable_default_section=True).load_str(cfg)
    assert d == {'': {'key': 'value'}}

def test_config_single_split_default_section():
    cfg = """ \
    key1 = value1
    []
    key2 = value2
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True).load_str(cfg)
    assert "str:2: Duplicate section: ''" == str(ex_info.value)

    d = Parser(enable_default_section=True, allow_section_split=True).load_str(cfg)
    assert d == {'': {'key1': 'value1', 'key2': 'value2'}}

def test_config_single_set_override_in_implicit_default_section():
    cfg = """ \
    key1 = value
    key1 = another_value
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True).load_str(cfg)
    assert "str:2: Value already set for key 'key1'" == str(ex_info.value)

    d = Parser(enable_default_section=True, set_is_replace=True).load_str(cfg)
    assert d == {'': {'key1': 'another_value'}}

def test_config_single_set_override_in_splitted_default_section():
    cfg = """ \
    key1 = value
    []
    key1 = another_value
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True, allow_section_split=True).load_str(cfg)
    assert "str:3: Value already set for key 'key1'" == str(ex_info.value)

    d = Parser(enable_default_section=True, allow_section_split=True, set_is_replace=True).load_str(cfg)
    assert d == {'': {'key1': 'another_value'}}

def test_config_single_set_override_in_explicit_default_section():
    cfg = """ \
    []
    key1 = value
    key1 = another_value
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True).load_str(cfg)
    assert "str:3: Value already set for key 'key1'" == str(ex_info.value)

    d = Parser(enable_default_section=True, set_is_replace=True).load_str(cfg)
    assert d == {'': {'key1': 'another_value'}}

def test_config_single_empty_value_in_implicit_default_section():
    cfg = """ \
    key1 =
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True).load_str(cfg)
    assert "str:1: Empty value" == str(ex_info.value)

    d = Parser(enable_default_section=True, allow_empty_values=True).load_str(cfg)
    assert d == {'': {'key1': ''}}

    cfg = """ \
    key1 = ''
    """

    d = Parser(enable_default_section=True, allow_empty_values=True).load_str(cfg)
    assert d == {'': {'key1': ''}}

def test_config_single_empty_value_override_in_implicit_default_section():
    cfg = """ \
    key1 = value
    key1 =
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True).load_str(cfg)
    assert "str:2: Empty value" == str(ex_info.value)

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True, allow_empty_values=True).load_str(cfg)
    assert "str:2: Value already set for key 'key1'" == str(ex_info.value)

    d = Parser(enable_default_section=True, set_is_replace=True, allow_empty_values = True).load_str(cfg)
    assert d == {'': {'key1': ''}}

def test_config_single_empty_value_override_in_splitted_default_section():
    cfg = """ \
    key1 = value
    []
    key1 =
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True, allow_section_split=True).load_str(cfg)
    assert "str:3: Empty value" == str(ex_info.value)

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True, allow_section_split=True, allow_empty_values=True).load_str(cfg)
    assert "str:3: Value already set for key 'key1'" == str(ex_info.value)

    d = Parser(enable_default_section=True, allow_section_split=True, set_is_replace=True, allow_empty_values=True).load_str(cfg)
    assert d == {'': {'key1': ''}}

def test_config_single_empty_value_is_trimmed():
    cfg = '''\
    [section]
    key = '    '
    '''

    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_str(cfg)

    assert 'str:2: Empty value' == str(ex_info.value)

    d = Parser(allow_empty_values=True).load_str(cfg)
    assert d == {'section': {'key': ''}}

def test_config_single_empty_elements_are_trimmed():
    cfg = '''\
    [section]
    key = '   value one   ' '   value two   '
    '''

    d = Parser().load_str(cfg)
    assert d == {'section': {'key': ['value one', 'value two']}}

def test_config_single_set_override():
    cfg = """\
    [section]
    key = original
    key = replaced
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_str(cfg)
    assert "str:3: [section] Value already set for key 'key'" == str(ex_info.value)


    d = Parser(set_is_replace=True).load_str(cfg)
    assert d == {'section': {'key': 'replaced'}}

def test_config_single_set_override_in_splitted_section():
    cfg = """\
    [section1]
    key = original

    [section2]
    some = value

    [section3]

    [section1]
    key = replaced
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(allow_section_split=True).load_str(cfg)
    assert "str:10: [section1] Value already set for key 'key'" == str(ex_info.value)

    d = Parser(allow_section_split=True, set_is_replace=True).load_str(cfg)
    assert d == {
        'section1': {
            'key': 'replaced'
        },
        'section2': {
            'some': 'value'
        },
        'section3': {}
    }

def test_config_single_fallback():
    cfg = """\
    [section]
    some = value
    some ?= replacement
    another ?= value
    """

    d = Parser().load_str(cfg)
    assert d == {
        'section': {
            'some':  'value',
            'another': 'value'
        }
    }

def test_config_single_fallback_in_splitted_section():
    cfg = """\
    [section]
    some = value

    [another_section]

    [section]
    some ?= replacement
    another ?= value
    """

    d = Parser(allow_section_split=True).load_str(cfg)
    assert d == {
        'section': {
            'some':  'value',
            'another': 'value'
        },
        'another_section': {}
    }

def test_config_single_replace():
    cfg = """\
    [section]
    some = value
    some != replacement
    """

    d = Parser().load_str(cfg)
    assert d == {
        'section': {
            'some':  'replacement'
        }
    }

def test_config_single_replace_in_splitted_section():
    cfg = """\
    [section]
    some = value

    [section]
    some != replacement
    """

    d = Parser(allow_section_split=True).load_str(cfg)
    assert d == {
        'section': {
            'some':  'replacement'
        }
    }

def test_config_single_add_empty_once():
    cfg = """\
    [section]
    some +=
    """

    d = Parser(allow_empty_values=True).load_str(cfg)
    assert d == {
        'section': {
            'some':  ['']
        }
    }

def test_config_single_add_empty_twice():
    cfg = """\
    [section]
    some +=
    some +=
    """

    d = Parser(allow_empty_values=True).load_str(cfg)
    assert d == {
        'section': {
            'some':  ['', '']
        }
    }

def test_config_single_add():
    cfg = """\
    [section]
    some = value1
    some += value2
    """

    d = Parser().load_str(cfg)
    assert d == {
        'section': {
            'some':  ['value1', 'value2']
        }
    }

def test_config_single_add_in_splitted_section():
    cfg = """\
    [section]
    some = value1

    [section]
    some += value2
    """

    d = Parser(allow_section_split=True).load_str(cfg)
    assert d == {
        'section': {
            'some':  ['value1', 'value2']
        }
    }

def test_config_single_union_empty_once():
    cfg = """\
    [section]
    some ^=
    """

    d = Parser(allow_empty_values=True).load_str(cfg)
    assert d == {
        'section': {
            'some':  ['']
        }
    }

def test_config_single_union_empty_twice():
    cfg = """\
    [section]
    some ^=
    some ^=
    """

    d = Parser(allow_empty_values=True).load_str(cfg)
    assert d == {
        'section': {
            'some':  ['']
        }
    }

def test_config_single_union():
    cfg = """\
    [section]
    key = a c
    key ^= a b c d
    """

    d = Parser().load_str(cfg)
    assert d == {
        'section': {
            'key':  ['a', 'c', 'b', 'd']
        }
    }

def test_config_single_union_in_splitted_section():
    cfg = """\
    [section]
    key = a c

    [section]
    key ^= a b c d
    """

    d = Parser(allow_section_split=True).load_str(cfg)
    assert d == {
        'section': {
            'key':  ['a', 'c', 'b', 'd']
        }
    }

def test_config_single_assignment_continuation():
    cfg = """\
    [section1]
    key = a b   \
      c d \
      e f\
      g

    [section2]
    key = a \
    b
    """

    d = Parser(allow_section_split=True).load_str(cfg)
    assert d == {
        'section1': {
            'key':  ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        },
        'section2': {
            'key':  ['a', 'b']
        }
    }

def test_config_single_valid_exotic_section_names():
    cfg = """\
    [*]
    key = a

    [*.*]
    key = b

    [*.a.*.c]
    key = c
    """

    d = Parser().load_str(cfg)
    assert d == {
        '*':  {'key': 'a'},
        '*.*': {'key': 'b'},
        '*.a.*.c': {'key': 'c'}
    }

def test_config_single_invalid_section_names():
    cfg = """\
    [*.] # invalid
    key = a
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_str(cfg)

    assert "str:1: Invalid section name: '*.'" == str(ex_info.value)

    cfg = """\
    [.abc] # This is valid only if default section is enabled and nested sections are enabled.
    key = a
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_str(cfg)

    assert "str:1: Invalid section name: '.abc'" == str(ex_info.value)

    cfg = """\
    [abc.] # invalid even with nested sections
    key = a
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_str(cfg)

    assert "str:1: Invalid section name: 'abc.'" == str(ex_info.value)

    with pytest.raises(Parser.Error) as ex_info:
        Parser(nested_sections=True).load_str(cfg)

    assert "str:1: Invalid section name: 'abc.'" == str(ex_info.value)

def test_config_single_invalid_key_values():
    cfg = """\
    .a.b.c = value
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True, nested_sections=True).load_str(cfg)

    assert "str:1: Invalid key: '.a.b.c'" == str(ex_info.value)

    cfg = """\
    [section]
    .a.b.c = value
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(enable_default_section=True, nested_sections=True).load_str(cfg)

    assert "str:2: Invalid key: '.a.b.c'" == str(ex_info.value)

def test_config_single_nested_sections():
    cfg = """\
    [section]
    sub.key = value
    """

    d = Parser().load_str(cfg)
    assert d == {'section': {'sub.key' : 'value'}}

    d = Parser(nested_sections=True).load_str(cfg)
    assert d == {
        'section': {
            'sub': {
                'key' : 'value'
            }
        }
    }

def test_config_single_nested_sections_on_implicit_default_section():
    cfg = """\
    a.b.c = value
    """

    d = Parser(enable_default_section=True, nested_sections=True).load_str(cfg)
    assert d == {
        "": {
            'a': {
                'b': {
                    'c': 'value'
                }
            }
        }
    }

    #assert "str#1:1: Invalid key: '.a.b.c'" == str(ex_info.value)

def test_config_single_nested_sections_on_explicit_default_section():
    # [.not.valid.section] is valid only if default section is enabled and
    # nested sections are enabled.
    cfg = """\
    [.a.b.c]
    key = value
    a.b = c

    []
    x.y += z # NOTE: it will become an array
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser().load_str(cfg)

    assert "str:1: Invalid section name: '.a.b.c'" == str(ex_info.value)

    d = Parser(nested_sections=True, enable_default_section=True, allow_section_split=True).load_str(cfg)
    assert d == {
        '': {
            'a': {
                'b': {
                    'c' : {
                        'key' : 'value',
                        'a' : {
                            'b': 'c'
                        },
                    }
                }
            },
            'x': {
                'y': ['z']
            }
        }
    }

def test_config_single_nested_section_never_cannot_override_value():
    cfg = """\
    [section]
    key = value

    [section.key]
    b = c
    """

    d = Parser().load_str(cfg)
    assert d == {
        'section': {
            'key': 'value'
        },
        'section.key': {
            'b': 'c'
        }
    }

    with pytest.raises(Parser.Error) as ex_info:
        Parser(nested_sections=True).load_str(cfg)
    assert "str:4: Key 'section.key' is already assigned to a value" == str(ex_info.value)

    cfg = """\
    [section]
    key = value

    [section]
    key.sub = test
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(nested_sections=True, allow_section_split=True).load_str(cfg)
    assert "str:5: Key 'section.key' is already assigned to a value" == str(ex_info.value)

def test_config_single_value_cannot_override_section():
    cfg = """\
    [section]
    key = value

    [section.sub]
    a = b

    [section]
    sub = test
    """

    with pytest.raises(Parser.Error) as ex_info:
        Parser(allow_section_split=True, nested_sections=True).load_str(cfg)
    assert "str:8: Cannot replace section 'section.sub' by a value" == str(ex_info.value)

def test_config_single_value_override_section():
    cfg = """\
    [section]
    key = value

    [section.sub]
    a = b

    [section]
    sub != test # This will cause section 'section.sub' to be replaced by a value!
    """

    d = Parser(allow_section_split=True, nested_sections=True).load_str(cfg)
    assert d == {
        'section': {
            'key': 'value',
            'sub': 'test' # Entire section 'section.sub' was replaced by value 'test'
        }
    }
