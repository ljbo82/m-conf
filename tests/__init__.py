# Copyright (c) 2023 Leandro José Britto de Oliveira
# Licensed under the MIT License.

from  m_conf.error import assert_type

def assert_exception(ex_type: type | None = None, msg: str | None = None):
    assert_type(ex_type, (type(None), type), 'ex_type')
    if ex_type is not None:
        assert issubclass(ex_type, Exception)
    assert_type(msg, (type(None), str), 'msg')

    class RaisesContext:
        def __init__(self, ex_type: type | None, msg: str | None):
            self.ex_type = ex_type
            self.msg = msg
            self.excinfo = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            # No exception raised → fail
            if exc_type is None:
                raise AssertionError(f"No exception was raised")

            # An exception was raised. Check type:
            if self.ex_type is not None and not issubclass(exc_type, self.ex_type):
                return False  # re-raise

            # Correct exception, check message
            if self.msg is not None:
                ex_msg = str(exc_value)
                if msg != ex_msg:
                    raise AssertionError(f"\nExpected message: {repr(msg)}\nGiven message: {repr(ex_msg)}")

            # store info and suppress it
            self.excinfo = (exc_type, exc_value, traceback)
            return True

    return RaisesContext(ex_type, msg)
