import pytest
import traceback
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname( __file__ ), "..", "rebound"))
import rebound

# Constants and helper functions
EXCEPTION_DETAILS = "Exception details"

def gen_python_exception(exception_type):
    stack_trace = None
    try:
        raise exception_type(EXCEPTION_DETAILS)
    except Exception:
        stack_trace = traceback.format_exc()
    return stack_trace

def gen_expected_message(exception_type_str):
    return exception_type_str + ": " + EXCEPTION_DETAILS

# Tests
@pytest.mark.parametrize("exception_type, exception_type_str", [
    (StopIteration, "StopIteration"),
    (StopAsyncIteration, "StopAsyncIteration"),
    (ArithmeticError, "ArithmeticError"),
    (AssertionError, "AssertionError"),
    (AttributeError, "AttributeError"),
    (BufferError, "BufferError"),
    (EOFError, "EOFError"),
    (ImportError, "ImportError"),
    (MemoryError, "MemoryError"),
    (NameError, "NameError"),
    (OSError, "OSError"),
    (ReferenceError, "ReferenceError"),
    (RuntimeError, "RuntimeError"),
    (SyntaxError, "SyntaxError"),
    (SystemError, "SystemError"),
    (TypeError, "TypeError"),
    (ValueError, "ValueError"),
    (Warning, "Warning")
])
def test_get_error_message(exception_type, exception_type_str):
    error_message = rebound.get_error_message(gen_python_exception(exception_type), "python3")
    expected_error_message = gen_expected_message(exception_type_str)
    assert error_message == expected_error_message