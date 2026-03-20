"""
ALGOL 26 Interpreter

Executes type-checked ALGOL 26 programs.
Provides runtime environment and evaluation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

# Import parser and typechecker
from parser import (
    parse, ModuleDecl, FuncDecl, LetDecl, LetBinding,
    IntLiteral, FloatLiteral, BoolLiteral, StringLiteral,
    Identifier, Lambda, Application, Param, Expr, NamedType
)
from typechecker import TypeChecker, TypeCheckError, ModuleResolver


class RuntimeError(Exception):
    """Runtime error during evaluation"""
    pass


@dataclass
class Value:
    """Base value in the runtime"""
    pass


@dataclass
class IntValue(Value):
    """Integer value"""
    value: int


@dataclass
class FloatValue(Value):
    """Float value"""
    value: float


@dataclass
class BoolValue(Value):
    """Boolean value"""
    value: bool


@dataclass
class StringValue(Value):
    """String value"""
    value: str


@dataclass
class ClosureValue(Value):
    """Closure (function + environment)"""
    params: List[Param]
    body: Expr
    env: Environment  # Captured environment


@dataclass
class UnitValue(Value):
    """Unit value (void)"""
    pass


class Environment:
    """
    Runtime environment mapping identifiers to values.
    Supports nested scopes (for let, lambda).
    """
    
    def __init__(self, parent: Optional[Environment] = None):
        self.bindings: Dict[str, Value] = {}
        self.parent = parent
    
    def lookup(self, name: str) -> Optional[Value]:
        """Look up a name in the environment"""
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
    
    def extend(self, name: str, value: Value) -> Environment:
        """Create new environment with extended binding"""
        new_env = Environment(self)
        new_env.bindings[name] = value
        return new_env
    
    def extend_many(self, names: List[str], values: List[Value]) -> Environment:
        """Extend with multiple bindings"""
        new_env = Environment(self)
        for name, val in zip(names, values):
            new_env.bindings[name] = val
        return new_env
    
    def update(self, name: str, value: Value):
        """Update existing binding (for mutable vars)"""
        if name in self.bindings:
            self.bindings[name] = value
        elif self.parent:
            self.parent.update(name, value)
        else:
            raise RuntimeError(f"Undefined variable: {name}")


class Evaluator:
    """
    Evaluates ALGOL 26 expressions in a typed environment.
    Assumes type checking has already been performed.
    """
    
    def __init__(self):
        self.global_env = Environment()
        self._setup_builtins()
    
    def _setup_builtins(self):
        """Initialize built-in functions and values"""
        # Primitive operations
        def add_fn(x: IntValue, y: IntValue) -> IntValue:
            return IntValue(x.value + y.value)
        
        def sub_fn(x: IntValue, y: IntValue) -> IntValue:
            return IntValue(x.value - y.value)
        
        def mul_fn(x: IntValue, y: IntValue) -> IntValue:
            return IntValue(x.value * y.value)
        
        def div_fn(x: IntValue, y: IntValue) -> IntValue:
            if y.value == 0:
                raise RuntimeError("Division by zero")
            return IntValue(x.value // y.value)  # Integer division
        
        # Store built-ins as closures
        self.global_env.bindings["+"] = ClosureValue(
            params=[Param("x", None), Param("y", None)],
            body=Application(Identifier(""), Identifier("")),  # placeholder
            env=self.global_env
        )
        self.global_env.bindings["-"] = ClosureValue(
            params=[Param("x", None), Param("y", None)],
            body=Application(Identifier(""), Identifier("")),
            env=self.global_env
        )
        self.global_env.bindings["*"] = ClosureValue(
            params=[Param("x", None), Param("y", None)],
            body=Application(Identifier(""), Identifier("")),
            env=self.global_env
        )
        self.global_env.bindings["/"] = ClosureValue(
            params=[Param("x", None), Param("y", None)],
            body=Application(Identifier(""), Identifier("")),
            env=self.global_env
        )
        
        # Print function
        def print_fn(val: Value) -> UnitValue:
            if isinstance(val, IntValue):
                print(val.value)
            elif isinstance(val, FloatValue):
                print(val.value)
            elif isinstance(val, BoolValue):
                print("true" if val.value else "false")
            elif isinstance(val, StringValue):
                print(val.value)
            else:
                print(val)
            return UnitValue(None)
        
        self.global_env.bindings["print"] = ClosureValue(
            params=[Param("x", None)],
            body=Application(Identifier(""), Identifier("")),
            env=self.global_env
        )
    
    def eval_module(self, module: ModuleDecl) -> Value:
        """Evaluate a module, executing top-level declarations"""
        env = self.global_env
        
        for decl in module.declarations:
            if isinstance(decl, FuncDecl):
                # Create a closure and bind it
                closure = ClosureValue(decl.params, decl.body, env)
                env = env.extend(decl.name, closure)
            elif isinstance(decl, LetDecl):
                # Evaluate all bindings (recursive if multiple)
                if decl.is_recursive():
                    # For recursive, we need to extend environment first with fresh bindings
                    names = [b.name for b in decl.bindings]
                    values = [self._eval(b.expr, env) for b in decl.bindings]
                    new_env = env.extend_many(names, values)
                    env = new_env
                else:
                    # Sequential evaluation
                    for binding in decl.bindings:
                        val = self._eval(binding.expr, env)
                        env = env.extend(binding.name, val)
        
        # Evaluate module body (if any) - for now, just return unit
        return UnitValue(None)
    
    def _eval(self, expr: Expr, env: Environment) -> Value:
        """Evaluate an expression in an environment"""
        if isinstance(expr, IntLiteral):
            return IntValue(expr.value)
        elif isinstance(expr, FloatLiteral):
            return FloatValue(expr.value)
        elif isinstance(expr, BoolLiteral):
            return BoolValue(expr.value)
        elif isinstance(expr, StringLiteral):
            return StringValue(expr.value)
        elif isinstance(expr, Identifier):
            val = env.lookup(expr.name)
            if val is None:
                raise RuntimeError(f"Undefined identifier: {expr.name}")
            return val
        elif isinstance(expr, Lambda):
            return ClosureValue([expr.param], expr.body, env)
        elif isinstance(expr, LetDecl):
            # Nested let expression
            for binding in expr.bindings:
                val = self._eval(binding.expr, env)
                env = env.extend(binding.name, val)
            return self._eval(expr.body, env)
        elif isinstance(expr, Application):
            fun_val = self._eval(expr.function, env)
            arg_val = self._eval(expr.argument, env)
            return self._apply_function(fun_val, [arg_val])
        else:
            raise RuntimeError(f"Unsupported expression type: {type(expr).__name__}")
    
    def _apply_function(self, fun: Value, args: List[Value]) -> Value:
        """Apply a function value to arguments"""
        if not isinstance(fun, ClosureValue):
            raise RuntimeError(f"Cannot apply non-function: {type(fun).__name__}")
        
        if len(fun.params) != len(args):
            raise RuntimeError(f"Arity mismatch: expected {len(fun.params)} args, got {len(args)}")
        
        # Extend closure environment with argument bindings
        arg_names = [p.name for p in fun.params]
        call_env = fun.env.extend_many(arg_names, args)
        
        # Evaluate body in extended environment
        return self._eval(fun.body, call_env)
    
    def evaluate(self, source: str) -> Value:
        """
        Full pipeline: parse -> type check -> evaluate.
        This is the main entry point.
        """
        # Parse
        ast = parse(source)
        
        # Type check
        checker = TypeChecker()
        try:
            typed_ast = checker.check_module(ast)
        except TypeCheckError as e:
            print(f"Type checking failed: {e}")
            raise
        
        # Evaluate
        return self.eval_module(typed_ast)


# Convenience function
def eval(source: str) -> Value:
    """Evaluate ALGOL 26 source code"""
    evaluator = Evaluator()
    return evaluator.evaluate(source)
