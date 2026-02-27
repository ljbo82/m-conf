# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from .      import assert_exception
from m_conf import *
from pytest import fixture

import os

@fixture(scope='module')
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

    cfg = Parser().load_str(cfg)
    assert cfg == {'section': {'key1': 'value1'}}

def test_config_multiple():
    cfg1 = """
    [section1]
    key1 = value1
    """

    cfg2 = """
    [section2]
    key2 = value2
    """

    cfg = Parser().batch_load_str(cfg1, cfg2)
    assert cfg == {'section1': {'key1': 'value1'}, 'section2': {'key2': 'value2'}}

def test_config_empty_sections():
    cfg = """\
    [empty]

    [section]
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {}

def test_explode_value():
    cfg = """\
    [section]
    value = 'value with spaces' another\\ value\\ with\\ spaces one two three "value\\nwith\\nnew\\nline"
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'section': {
            'value': [
                'value with spaces',
                'another value with spaces',
                'one',
                'two',
                'three',
                'value\nwith\nnew\nline'
            ]
        }
    }

    print(cfg['section']['value'][5]) # type: ignore

def test_config_single_from_file(cwd):
    cfg = Parser().load_file('configs/valid/001.cfg')
    assert cfg == {'section': {'key1': 'value1'}}

def test_config_multiple_from_file(cwd):
    cfg = Parser().batch_load_file('configs/valid/002/001.cfg', 'configs/valid/002/002.cfg')
    assert cfg == {'section1': {'key1': 'value1'}, 'section2': {'key2': 'value2'}}

def test_config_single_invalid_from_file(cwd):
    with assert_exception(ParsingError, "configs/invalid/001.cfg:3: Path 'key' is already assigned"):
        Parser().load_file('configs/invalid/001.cfg')

    with assert_exception(ParsingError, "configs/invalid/001.cfg:4: Path 'nested.section.key' is already assigned"):
        Parser(set_is_replace=True).load_file('configs/invalid/001.cfg')

def test_config_multiple_invalid_from_file(cwd):
    files = ('configs/invalid/002/001.cfg','configs/invalid/002/002.cfg')

    with assert_exception(ParsingError, "configs/invalid/002/001.cfg > configs/invalid/002/002.cfg:5: Path 'section1.key1' is already assigned"):
        Parser().batch_load_file(*files)

    cfg = Parser(set_is_replace=True).batch_load_file(*files)
    assert cfg == {
        'section1': {
            'key1': 'another1' # This value came from 002.cfg
        },
        'section2': {
            'key2': 'value2',
        }
    }

def test_config_context_str_custom_prefix():
    cfg = """ \
    [section]
    key = value
    """

    with assert_exception(ParsingError, "cfg-1 > cfg-2:2: Path 'section.key' is already assigned"):
        Parser().batch_load_str(cfg, cfg, ctx_id_prefix="cfg-")

def test_config_single_explicit_default_section():
    cfg = """ \
    []
    key = value
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {'key': 'value'}

def test_config_single_implicity_default_section():
    cfg = """ \
    key = value
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {'key': 'value'}

def test_config_single_split_default_section():
    cfg = """ \
    key1 = value1
    []
    key2 = value2
    """
    cfg = Parser().load_str(cfg)
    assert cfg == {'key1': 'value1', 'key2': 'value2'}

def test_config_single_set_override_in_implicit_default_section():
    cfg = """ \
    key1 = value
    key1 = another_value
    """

    with assert_exception(ParsingError, "str:2: Path 'key1' is already assigned"):
        Parser().load_str(cfg)

    cfg = Parser(set_is_replace=True).load_str(cfg)
    assert cfg == {'key1': 'another_value'}

def test_config_single_set_override_in_splitted_default_section():
    cfg = """ \
    key1 = value
    []
    key1 = another_value
    """

    with assert_exception(ParsingError, "str:3: Path 'key1' is already assigned"):
        Parser().load_str(cfg)

    cfg = Parser(set_is_replace=True).load_str(cfg)
    assert cfg == {'key1': 'another_value'}

def test_config_single_set_override_in_explicit_default_section():
    cfg = """ \
    []
    key1 = value
    key1 = another_value
    """

    with assert_exception(ParsingError, "str:3: Path 'key1' is already assigned"):
        Parser().load_str(cfg)

    cfg = Parser(set_is_replace=True).load_str(cfg)
    assert cfg == {'key1': 'another_value'}

def test_config_single_empty_value_in_implicit_default_section():
    cfg = """ \
    key1 =
    """
    d = Parser().load_str(cfg)
    assert d == {'key1': ''}

    cfg = """ \
    key1 = ''
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {'key1': ''}

def test_config_single_empty_value_override_in_implicit_default_section():
    cfg = """ \
    key1 = value
    key1 =
    """

    with assert_exception(ParsingError, "str:2: Path 'key1' is already assigned"):
        Parser().load_str(cfg)

    cfg = Parser(set_is_replace=True).load_str(cfg)
    assert cfg == {'key1': ''}

def test_config_single_empty_value_override_in_splitted_default_section():
    cfg = """ \
    key1 = value
    []
    key1 =
    """

    with assert_exception(ParsingError, "str:3: Path 'key1' is already assigned"):
        Parser().load_str(cfg)

    cfg = Parser(set_is_replace=True).load_str(cfg)
    assert cfg == {'key1': ''}

def test_config_single_empty_value_is_trimmed():
    cfg = '''\
    [section]
    key = '    '
    '''

    cfg = Parser().load_str(cfg)
    assert cfg == {'section': {'key': ''}}

def test_config_single_empty_elements_are_trimmed():
    cfg = '''\
    [section]
    key = '   value one   ' '   value two   '
    '''

    cfg = Parser().load_str(cfg)
    assert cfg == {'section': {'key': ['value one', 'value two']}}

def test_config_single_set_override():
    cfg = """\
    [section]
    key = original
    key = replaced
    """

    with assert_exception(ParsingError, "str:3: Path 'section.key' is already assigned"):
        Parser().load_str(cfg)

    cfg = Parser(set_is_replace=True).load_str(cfg)
    assert cfg == {'section': {'key': 'replaced'}}

def test_config_single_set_override_in_splitted_section():
    cfg = """\
    [section1]
    key = original

    [section2]
    some = value

    [section3] # This will be skipped since it is empty

    [section1]
    key = replaced
    """

    with assert_exception(ParsingError, "str:10: Path 'section1.key' is already assigned"):
        Parser().load_str(cfg)

    cfg = Parser(set_is_replace=True).load_str(cfg)
    assert cfg == {
        'section1': {
            'key': 'replaced'
        },
        'section2': {
            'some': 'value'
        },
    }

def test_config_single_fallback():
    cfg = """\
    [section]
    some = value
    some ?= replacement
    another ?= value
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'section': {
            'some':  'value',
            'another': 'value'
        }
    }

def test_config_single_fallback_in_splitted_section():
    cfg = """\
    [section]
    some = value

    [another_section] # this is skipped since there are no entries

    [section]
    some ?= replacement
    another ?= value
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'section': {
            'some':  'value',
            'another': 'value'
        }
    }

def test_config_single_replace():
    cfg = """\
    [section]
    some = value
    some != replacement
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'section': {
            'some':  'replacement'
        }
    }

def test_config_single_add_empty_once():
    cfg = """\
    [section]
    some +=
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'section': {
            'some':  ['value1', 'value2']
        }
    }

def test_config_single_union_empty_once():
    cfg = """\
    [section]
    some ^=
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'section': {
            'key':  ['a', 'c', 'b', 'd']
        }
    }

def test_config_single_assignment_continuation():
    cfg = """\
    [section1]
    key = a b   \\
      c d \\
      e f\\
      g

    [section2]
    key = a \\
    b
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
        '*':  {
            'key': 'a',
            '*' : {
                'key': 'b'
            },
            'a': {
                '*': {
                    'c': {
                        'key': 'c'
                    }
                }
            }
        }
    }

def test_config_single_invalid_section_names():
    cfg = """\
    [*.] # invalid
    key = a
    """

    with assert_exception(ParsingError, "str:1: Invalid path: '*.'"):
        Parser().load_str(cfg)


    cfg = """\
    [.abc]
    key = a
    """

    with assert_exception(ParsingError, "str:1: Invalid path: '.abc'"):
        Parser().load_str(cfg)

    cfg = """\
    [abc.]
    key = a
    """

    with assert_exception(ParsingError, "str:1: Invalid path: 'abc.'"):
        Parser().load_str(cfg)

def test_config_single_invalid_path_on_assignment():
    cfg = """\
    .a.b.c = value
    """

    with assert_exception(ParsingError, "str:1: Invalid path: '.a.b.c'"):
        Parser().load_str(cfg)

    cfg = """\
    [section]
    .a.b.c = value
    """

    with assert_exception(ParsingError, "str:2: Invalid path: '.a.b.c'"):
        Parser().load_str(cfg)

def test_config_single_nested_sections():
    cfg = """\
    [section]
    sub.key = value
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
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

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'a': {
            'b': {
                'c': 'value'
            }
        }
    }

def test_config_single_nested_sections_on_explicit_default_section():
    # [.not.valid.section] is valid only if default section is enabled and
    # nested sections are enabled.
    cfg = """\
    []
    x.y += z # NOTE: it will become an array
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'x': {
            'y': ['z']
        }
    }

def test_config_single_nested_section_never_cannot_override_value():
    cfg = """\
    [section]
    key = value

    [section.key]
    b = c
    """

    with assert_exception(ParsingError, "str:4: Path 'section.key' is already assigned"):
        Parser().load_str(cfg)

    cfg = """\
    [section]
    key = value

    [section]
    key.sub = test
    """

    with assert_exception(ParsingError, "str:5: Path 'section.key' is already assigned"):
        Parser().load_str(cfg)

def test_config_single_value_cannot_override_section():
    cfg = """\
    [section]
    key = value

    [section.sub]
    a = b

    [section]
    sub = test
    """

    with assert_exception(ParsingError, "str:8: Path 'section.sub' is already assigned"):
        Parser().load_str(cfg)

    cfg = Parser(set_is_replace=True).load_str(cfg)
    assert cfg == {
        'section': {
            'key': 'value',
            'sub': 'test' # Entire section 'section.sub' was replaced by 'test'
        }
    }

def test_config_single_value_override_section():
    cfg = """\
    [section]
    key = value

    [section.sub]
    a = b

    [section]
    sub != test # This will cause section 'section.sub' to be replaced by a value!
    """

    cfg = Parser().load_str(cfg)
    assert cfg == {
        'section': {
            'key': 'value',
            'sub': 'test' # Entire section 'section.sub' was replaced by 'test'
        }
    }
