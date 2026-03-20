#!/usr/bin/env python3
"""
ALGOL 26 Command-line Interface

Usage:
  algo run <file>       - Parse, type check, and run an ALGOL 26 program
  algo test             - Run test suite
  algo check <file>     - Type check only (no execution)
"""

import sys
from pathlib import Path
from parser import parse
from typechecker import TypeChecker, TypeCheckError
from interpreter import Evaluator


def run_file(filename: str):
    """Parse, type check, and evaluate an ALGOL 26 source file"""
    path = Path(filename)
    if not path.exists():
        print(f"Error: File not found: {filename}")
        return 1
    
    print(f"Running {filename}...")
    source = path.read_text()
    
    try:
        # Parse
        print("  Parsing...")
        ast = parse(source)
        print("  ✓ Parsed successfully")
        
        # Type check
        print("  Type checking...")
        checker = TypeChecker()
        typed_ast = checker.check_module(ast)
        print("  ✓ Type check passed")
        
        # Execute
        print("  Evaluating...")
        evaluator = Evaluator()
        result = evaluator.eval_module(typed_ast)
        print("  ✓ Evaluation completed")
        
        return 0
    except TypeCheckError as e:
        print(f"  ✗ Type error: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def type_check_only(filename: str):
    """Type check an ALGOL 26 source file without executing"""
    path = Path(filename)
    if not path.exists():
        print(f"Error: File not found: {filename}")
        return 1
    
    print(f"Type checking {filename}...")
    source = path.read_text()
    
    try:
        ast = parse(source)
        checker = TypeChecker()
        typed_ast = checker.check_module(ast)
        print("✓ Type check passed")
        return 0
    except TypeCheckError as e:
        print(f"✗ Type error: {e}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


def run_tests():
    """Run the test suite"""
    import tests.test_phase2
    return 0 if tests.test_phase2.main() else 1


def print_usage():
    print(__doc__)
    print("""
Examples:
  algo run examples/demo1.algol26
  algo check examples/demo1.algol26
  algo test
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    command = sys.argv[1]
    if command == "run" and len(sys.argv) >= 3:
        return run_file(sys.argv[2])
    elif command == "check" and len(sys.argv) >= 3:
        return type_check_only(sys.argv[2])
    elif command == "test":
        return run_tests()
    else:
        print(f"Unknown command: {command}")
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
