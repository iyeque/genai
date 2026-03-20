"""
ALGOL 26 Interpreter Package

Provides runtime evaluation of ALGOL 26 programs.
"""

from .interpreter import (
    Value, IntValue, FloatValue, BoolValue, StringValue,
    ClosureValue, UnitValue, Environment, Evaluator, eval
)

__all__ = [
    'Value', 'IntValue', 'FloatValue', 'BoolValue', 'StringValue',
    'ClosureValue', 'UnitValue', 'Environment', 'Evaluator', 'eval'
]
