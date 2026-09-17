# Automated tests for calc.py.
# Run with:  pytest -q
# Each function starting with "test_" is one check. If an "assert" is false, the test fails.

from calc import add, subtract  # pull the functions in from calc.py


def test_add():
    assert add(2, 3) == 5        # 2 + 3 should be 5

def test_subtract():
    assert subtract(5, 3) == 2   # 5 - 3 should be 2
