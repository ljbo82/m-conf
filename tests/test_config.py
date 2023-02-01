from pathlib import Path

import m_conf.config as config
import os
import pytest

@pytest.fixture(scope='module')
def cwd():
    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    yield
    os.chdir(cwd)
    print()

def path_list(*paths: str):
    _paths = []
    for path in paths:
        _paths.append(Path(path))

    return _paths

def test_config_single():
    cfg = """
    [section]
    key1 = value1
    """

    d = config.load(cfg)
    assert d == {'section': {'key1': ['value1']}}

def test_config_multiple():
    cfg1 = """
    [section1]
    key1 = value1
    """

    cfg2 = """
    [section2]
    key2 = value2
    """

    d = config.load(cfg1, cfg2)
    assert d == {'section1': {'key1': ['value1']}, 'section2': {'key2': ['value2']}}

def test_config_single_from_file(cwd):
    d = config.load(Path('configs/valid/001.cfg'))
    assert d == {'section': {'key1': ['value1']}}

def test_config_multiple_from_file(cwd):
    d = config.load(*path_list(
        'configs/valid/002/001.cfg',
        'configs/valid/002/002.cfg')
    )

    assert d == {'section1': {'key1': ['value1']}, 'section2': {'key2': ['value2']}}

def test_config_single_invalid_from_file(cwd):
    with pytest.raises(config.ParsingError) as ex_info:
        config.load(Path('configs/invalid/001.cfg'))

    assert 'configs/invalid/001.cfg:1: Expected a section' == str(ex_info.value)

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(Path('configs/invalid/001.cfg'), enable_default_section=True)

    assert "configs/invalid/001.cfg:3: Duplicate section: ''" == str(ex_info.value)

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(Path('configs/invalid/001.cfg'), enable_default_section=True, allow_section_split=True)

    assert "configs/invalid/001.cfg:4: Value already set for key 'key'" == str(ex_info.value)

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(Path('configs/invalid/001.cfg'), enable_default_section=True, allow_section_split=True, set_is_replace=True)

    assert "configs/invalid/001.cfg:5: Attempt to set an empty value for key 'empty'" == str(ex_info.value)

    d = config.load(Path('configs/invalid/001.cfg'), enable_default_section=True, allow_section_split=True, set_is_replace=True, allow_empty_values=True)
    assert d == {
        '': {
            'key': ['another', 'value'],
            'empty': []
        }
    }

def test_config_multiple_invalid_from_file(cwd):
    paths = path_list(
        'configs/invalid/002/001.cfg',
        'configs/invalid/002/002.cfg'
    )

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(*paths)

    assert "configs/invalid/002/001.cfg > configs/invalid/002/002.cfg:3: [section2] Attempt to set an empty value for key 'empty'" == str(ex_info.value)

    d = config.load(*paths, allow_empty_values=True, avoid_list_values=True)
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

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, cfg)

    assert "str#1 > str#2:1: Duplicate section: 'section'" == str(ex_info.value)

def test_config_context_str_custom_prefix():
    cfg = """ \
    [section]
    key = value
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, cfg, str_prefix="cfg-")

    assert "cfg-1 > cfg-2:1: Duplicate section: 'section'" == str(ex_info.value)

def test_config_context_named_strings():
    cfg = ''' \
    [section]
    key = value
    '''

    with pytest.raises(config.ParsingError) as ex_info:
        config.load((cfg, 'file1'), (cfg, 'another_file'))

    assert "file1 > another_file:1: Duplicate section: 'section'" == str(ex_info.value)

def test_config_single_explicit_default_section():
    cfg = """ \
    []
    key = value
    """
    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg)
    assert 'str#1:1: Default/Empty section not allowed' == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True)
    assert d == {'': {'key': ['value']}}

def test_config_single_implicity_default_section():
    cfg = """ \
    key = value
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg)
    assert 'str#1:1: Expected a section' == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True)
    assert d == {'': {'key': ['value']}}

def test_config_single_split_default_section():
    cfg = """ \
    key1 = value1
    []
    key2 = value2
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True)
    assert "str#1:2: Duplicate section: ''" == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True, allow_section_split=True)
    assert d == {'': {'key1': ['value1'], 'key2': ['value2']}}

def test_config_single_set_override_in_implicit_default_section():
    cfg = """ \
    key1 = value
    key1 = another_value
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True)
    assert "str#1:2: Value already set for key 'key1'" == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True, set_is_replace=True)
    assert d == {'': {'key1': ['another_value']}}

def test_config_single_set_override_in_splitted_default_section():
    cfg = """ \
    key1 = value
    []
    key1 = another_value
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True, allow_section_split=True)
    assert "str#1:3: Value already set for key 'key1'" == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True, allow_section_split=True, set_is_replace=True)
    assert d == {'': {'key1': ['another_value']}}

def test_config_single_set_override_in_explicit_default_section():
    cfg = """ \
    []
    key1 = value
    key1 = another_value
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True)
    assert "str#1:3: Value already set for key 'key1'" == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True, set_is_replace=True)
    assert d == {'': {'key1': ['another_value']}}

def test_config_single_empty_value_in_implicit_default_section():
    cfg = """ \
    key1 =
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True)
    assert "str#1:1: Attempt to set an empty value for key 'key1'" == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True, allow_empty_values=True)
    assert d == {'': {'key1': []}}

def test_config_single_empty_value_override_in_implicit_default_section():
    cfg = """ \
    key1 = value
    key1 =
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True)
    assert "str#1:2: Value already set for key 'key1'" == str(ex_info.value)

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True, set_is_replace=True)
    assert "str#1:2: Attempt to set an empty value for key 'key1'" == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True, set_is_replace=True, allow_empty_values = True)
    assert d == {'': {'key1': []}}

def test_config_single_empty_value_override_in_splitted_default_section():
    cfg = """ \
    key1 = value
    []
    key1 =
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True, allow_section_split=True)
    assert "str#1:3: Value already set for key 'key1'" == str(ex_info.value)

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True, allow_section_split=True, set_is_replace=True)
    assert "str#1:3: Attempt to set an empty value for key 'key1'" == str(ex_info.value)

    d = config.load(cfg, enable_default_section=True, allow_section_split=True, set_is_replace=True, allow_empty_values=True)
    assert d == {'': {'key1': []}}

def test_config_single_set_override():
    cfg = """\
    [section]
    key = original
    key = replaced
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg)
    assert "str#1:3: [section] Value already set for key 'key'" == str(ex_info.value)


    d = config.load(cfg, set_is_replace=True)
    assert d == {'section': {'key': ['replaced']}}

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

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, allow_section_split=True)
    assert "str#1:10: [section1] Value already set for key 'key'" == str(ex_info.value)

    d = config.load(cfg, allow_section_split=True, set_is_replace=True)
    assert d == {
        'section1': {
            'key': ['replaced']
        },
        'section2': {
            'some': ['value']
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

    d = config.load(cfg)
    assert d == {
        'section': {
            'some':  ['value'],
            'another': ['value']
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

    d = config.load(cfg, allow_section_split=True)
    assert d == {
        'section': {
            'some':  ['value'],
            'another': ['value']
        },
        'another_section': {}
    }

def test_config_single_replace():
    cfg = """\
    [section]
    some = value
    some != replacement
    """

    d = config.load(cfg)
    assert d == {
        'section': {
            'some':  ['replacement']
        }
    }

def test_config_single_replace_in_splitted_section():
    cfg = """\
    [section]
    some = value

    [section]
    some != replacement
    """

    d = config.load(cfg, allow_section_split=True)
    assert d == {
        'section': {
            'some':  ['replacement']
        }
    }

def test_config_single_add():
    cfg = """\
    [section]
    some = value1
    some += value2
    """

    d = config.load(cfg)
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

    d = config.load(cfg, allow_section_split=True)
    assert d == {
        'section': {
            'some':  ['value1', 'value2']
        }
    }

def test_config_single_union():
    cfg = """\
    [section]
    key = a c
    key ^= a b c d
    """

    d = config.load(cfg)
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

    d = config.load(cfg, allow_section_split=True)
    assert d == {
        'section': {
            'key':  ['a', 'c', 'b', 'd']
        }
    }

def test_config_single_avoid_list():
    cfg = '''\
    [mysection]
    single_element = element
    multiple_elements = e1 e2 'e3 and e4' e5\\ and\\ e6
    another = 'value with spaces'
    empty =
    '''

    d = config.load(cfg, allow_empty_values=True)
    # Default: use list in values
    assert d == {
        'mysection': {
            'single_element': ['element'],
            'multiple_elements': [
                'e1',
                'e2',
                'e3 and e4',
                'e5 and e6',
            ],
            'another': ['value with spaces'],
            'empty': []
            }
        }

    d = config.load(cfg, allow_empty_values=True, avoid_list_values=True)
    # Default: use list in values
    assert d == {
        'mysection': {
            'single_element': 'element',
            'multiple_elements': [
                'e1',
                'e2',
                'e3 and e4',
                'e5 and e6'
            ],
            'another': 'value with spaces',
            'empty': ""
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

    d = config.load(cfg, allow_section_split=True)
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

    d = config.load(cfg)
    assert d == {
        '*':  {'key': ['a']},
        '*.*': {'key': ['b']},
        '*.a.*.c': {'key': ['c']}
    }

def test_config_single_invalid_section_names():
    cfg = """\
    [*.] # invalid
    key = a
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg)

    assert "str#1:1: Invalid section name: '*.'" == str(ex_info.value)

    cfg = """\
    [.abc] # This is valid only if default section is enabled and nested sections are enabled.
    key = a
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg)

    assert "str#1:1: Invalid section name: '.abc'" == str(ex_info.value)

    cfg = """\
    [abc.] # invalid even with nested sections
    key = a
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg)

    assert "str#1:1: Invalid section name: 'abc.'" == str(ex_info.value)

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, nested_sections=True)

    assert "str#1:1: Invalid section name: 'abc.'" == str(ex_info.value)

def test_config_single_invalid_key_values():
    cfg = """\
    .a.b.c = value
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True, nested_sections=True)

    assert "str#1:1: Invalid key: '.a.b.c'" == str(ex_info.value)

    cfg = """\
    [section]
    .a.b.c = value
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, enable_default_section=True, nested_sections=True)

    assert "str#1:2: Invalid key: '.a.b.c'" == str(ex_info.value)

def test_config_single_nested_sections():
    cfg = """\
    [section]
    sub.key = value
    """

    d = config.load(cfg)
    assert d == {'section': {'sub.key' : ['value']}}

    d = config.load(cfg, nested_sections=True)
    assert d == {
        'section': {
            'sub': {
                'key' : ['value']
            }
        }
    }

def test_config_single_nested_sections_on_implicit_default_section():
    cfg = """\
    a.b.c = value
    """

    d = config.load(cfg, enable_default_section=True, nested_sections=True)
    assert d == {
        "": {
            'a': {
                'b': {
                    'c': ['value']
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
    x.y = z
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg)

    assert "str#1:1: Invalid section name: '.a.b.c'" == str(ex_info.value)

    d = config.load(cfg, nested_sections=True, enable_default_section=True, allow_section_split=True)
    assert d == {
        '': {
            'a': {
                'b': {
                    'c' : {
                        'key' : ['value'],
                        'a' : {
                            'b': ['c']
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

    d = config.load(cfg, avoid_list_values=True)
    assert d == {
        'section': {
            'key': 'value'
        },
        'section.key': {
            'b': 'c'
        }
    }

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, nested_sections=True)
    assert "str#1:4: Key 'section.key' is already assigned to a value" == str(ex_info.value)

    cfg = """\
    [section]
    key = value

    [section]
    key.sub = test
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, nested_sections=True, allow_section_split=True)
    assert "str#1:5: Key 'section.key' is already assigned to a value" == str(ex_info.value)

def test_config_single_value_cannot_override_section():
    cfg = """\
    [section]
    key = value

    [section.sub]
    a = b

    [section]
    sub = test
    """

    with pytest.raises(config.ParsingError) as ex_info:
        config.load(cfg, allow_section_split=True, nested_sections=True)
    assert "str#1:8: [section] Cannot replace section 'section.sub' by a value" == str(ex_info.value)

def test_config_single_value_override_section():
    cfg = """\
    [section]
    key = value

    [section.sub]
    a = b

    [section]
    sub != test # This will cause section 'section.sub' to be replaced by a value!
    """

    d = config.load(cfg, allow_section_split=True, nested_sections=True)
    assert d == {
        'section': {
            'key': ['value'],
            'sub': ['test'] # Entire section 'section.sub' was replaced by value 'test'
        }
    }
