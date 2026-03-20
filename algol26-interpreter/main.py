#!/usr/bin/env python3
"""
ALGOL 26 Interpreter - Main Entry Point

Usage: python main.py <source_file>
"""

import os
import sys
from src.lexer import Lexer, LexerError
from src.parser import Parser, ParserError
from src.interpreter import Interpreter, InterpreterError
from typechecker.typecheck import typecheck_program, TypeCheckError as TCError


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <source_file>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    try:
        lexer = Lexer(source)
        parser = Parser(lexer)
        ast = parser.parse()

        # Type checking phase
        try:
            base_path = os.path.dirname(os.path.abspath(filename)) or '.'
            type_env = typecheck_program(ast, base_path=base_path)
            # Type checking passed
        except TCError as e:
            print(f"Type error: {e}")
            sys.exit(1)

        interpreter = Interpreter()
        result = interpreter.eval(ast)
    except InterpreterError as e:
        print(f"Runtime error: {e}")
        sys.exit(1)
    except ParserError as e:
        print(f"Parse error: {e}")
        sys.exit(1)
    except LexerError as e:
        print(f"Lexer error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
