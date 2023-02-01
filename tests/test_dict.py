from m_conf.dict import ReadOnlyDict

import pytest

def test_assignment():
    d = {}

    d[1] = 2
    d[2] = 4
    d[3] = 6

    ro = ReadOnlyDict(d)
    assert ro[1] == 2
    assert ro[2] == 4
    assert ro[3] == 6

    with pytest.raises(NotImplementedError):
        ro[4] = 8

    with pytest.raises(KeyError):
        ro[4]

    d[4] = 8

    assert ro[4] == 8

def test_delete():
    d = {
        1: 2,
        2: 4,
        3: 6
    }

    ro = ReadOnlyDict(d)
    assert ro[3] == 6
    with pytest.raises(NotImplementedError):
        del ro[3]

    del d[3]
    with pytest.raises(KeyError):
        ro[3]

def test_update():
    d = {
        1: 2,
        2: 4,
        3: 6
    }

    other = {
        4: 8,
        5: 10,
        6: 12
    }

    ro = ReadOnlyDict(d)
    with pytest.raises(NotImplementedError):
        ro.update(other)

    with pytest.raises(KeyError):
        ro[5]

    d.update(other)
    assert ro[5] == 10

def test_ior():
    d = {1: 2}
    ro = ReadOnlyDict(d)

    with pytest.raises(KeyError):
        ro[3]

    with pytest.raises(NotImplementedError):
        ro |= {3: 4}

    d |= {3: 4}
    assert ro[3] == 4
