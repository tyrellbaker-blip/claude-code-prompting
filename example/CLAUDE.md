# calc-demo

Small command-line calculator used as a prompting example.

- `calc.py` holds the operations. `OPS` maps a command name to a function. New operations go in as a function plus one entry in `OPS`.
- `test_calc.py` holds the tests. Run with `pytest -q`. Every operation gets at least one test.
- Do not change existing operations when adding new ones.
