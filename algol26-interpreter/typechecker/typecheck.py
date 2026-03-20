"""
ALGOL 26 Type Checker

Provides type checking as a separate phase before interpretation.
"""

from .inference import ConstraintGenerator, TypeCheckError


def typecheck_program(program, base_path=None):
    """
    Run type inference on the given AST program.
    Returns the completed environment (with types resolved) if successful.
    Raises TypeCheckError on failure.
    """
    cg = ConstraintGenerator(base_path=base_path)
    env = cg.infer_program(program)
    return env
