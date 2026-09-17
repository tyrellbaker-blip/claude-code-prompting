# A tiny command-line calculator.
# Usage:  python calc.py add 2 3   ->  prints 5.0

import sys  # gives access to the words typed after "python calc.py"


# --- The math operations ---
# Each one takes two numbers and returns a result.

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b


# --- The lookup table ---
# Maps the word the user types ("add", "sub") to the function that does the work.
# To add a new operation, write a function above and add one line here.

OPS = {"add": add, "sub": subtract}


# --- The entry point ---
# Reads three things from the command line: the operation name and two numbers.
# Looks up the operation in OPS, runs it, and prints the answer.

def main(argv):
    op, a, b = argv[0], float(argv[1]), float(argv[2])
    print(OPS[op](a, b))


# Only run main() when this file is executed directly (not when imported by the tests).
if __name__ == "__main__":
    main(sys.argv[1:])
