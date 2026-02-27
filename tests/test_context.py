# Copyright (c) 2023-2026 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from .      import assert_exception
from m_conf import *

def test_assign():
    ctx = Context()

    ctx.assign('key', 'value')
    assert ctx.cfg == {'key': 'value'}

    with assert_exception(ContextError, "ctx:0: Path 'key' is already assigned"):
        ctx.assign('key', 'value')

def test_section_assignment():
    ctx = Context()

    ctx.section = 'section1'
    ctx.assign('key1', 'value1')
    ctx.assign('key2', 'value2')

    assert ctx.cfg == {'section1': {'key1': 'value1', 'key2': 'value2'}}

    ctx.section = 'section2'
    ctx.assign('sub.key3', 'value3')
    ctx.assign('sub.key4', 'value4')
    ctx.assign('keyx', 'valuex')

    assert ctx.cfg == {
        'section1': {
            'key1': 'value1',
            'key2': 'value2'
        },
        'section2': {
            'sub': {
                'key3': 'value3',
                'key4': 'value4',
            },
            'keyx': 'valuex'
        }
    }

    ctx.section = ''
    ctx.assign('another', 'value')

    assert ctx.cfg == {
        'another': 'value',
        'section1': {
            'key1': 'value1',
            'key2': 'value2'
        },
        'section2': {
            'sub': {
                'key3': 'value3',
                'key4': 'value4',
            },
            'keyx': 'valuex'
        }
    }

def test_continuation():
    ctx = Context()

    ctx.assign('key', 'value1', continues=True)
    ctx.continue_assignment('value2', False)

    assert ctx.cfg == {'key': ['value1', 'value2']}

    ctx.cfg.clear()
    assert ctx.cfg == {}

    ctx.assign('key', 'value1', continues=True)
    ctx.continue_assignment('value2', False)
    assert ctx.cfg == {'key': ['value1', 'value2']}

    ctx.cfg.clear()
    assert ctx.cfg == {}

    ctx.assign('key', 'value1', continues=True)
    ctx.continue_assignment('value2', True)
    ctx.continue_assignment('value3', False)
    assert ctx.cfg == {'key': ['value1', 'value2', 'value3']}

def test_value_explode():
    ctx = Context()
    ctx.assign('key', 'value1 \'value with spaces\'')
    assert ctx.cfg == {'key': ['value1', 'value with spaces']}

def test_value_escaping():
    ctx = Context()
    ctx.assign('key', 'value\\ with\\ spaces')
    assert ctx.cfg == {'key': 'value with spaces'}

def test_empty_value_set():
    ctx = Context()
    ctx.assign('key', '')
    assert ctx.cfg == {'key': ''}

def test_apply():
    ctx = Context()
    ctx.assign('a.b.c', 'd', continues=True)
    assert ctx.cfg == {}

    ctx.apply()
    assert ctx.cfg == {'a': {'b': {'c': 'd'}}}

def test_illegal_apply():
    with assert_exception(ContextError, 'Invalid state'):
        Context().apply()

def test_illegal_continue():
    with assert_exception(ContextError, 'Invalid state'):
        Context().continue_assignment('value', False)

def test_section_split():
    ctx = Context()

    ctx.section = 'section1'
    ctx.assign('key1', 'value1')
    ctx.section = 'section2'
    ctx.assign('key2', 'value2')

    assert ctx.cfg == {
        'section1': {
            'key1': 'value1'
        },
        'section2': {
            'key2': 'value2'
        }
    }

    ctx.section = 'section1' # Return to previous section
    ctx.assign('key3', 'value3')

    assert ctx.cfg == {
        'section1': {
            'key1': 'value1',
            'key3': 'value3'
        },
        'section2': {
            'key2': 'value2'
        }
    }
