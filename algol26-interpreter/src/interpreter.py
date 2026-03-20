"""
ALGOL 26 Interpreter

Evaluates AST with environment, scopes, and built-in functions.
Implements the runtime semantics for MVP subset.
"""

from src.ast import (
    ASTNode, Program, Expr, Stmt,
    LiteralExpr, IdentifierExpr, BinaryOpExpr, UnaryOpExpr, CallExpr,
    ArrayIndexExpr, RecordAccessExpr, ArrayConstructorExpr, RecordConstructorExpr,
    ParenExpr,
    VarDeclStmt, ConstDeclStmt, TypeDeclStmt, AssignmentStmt, ProcCallStmt,
    IfStmt, WhileStmt, ForStmt, ReturnStmt, BlockStmt, ExprStmt, SkipStmt, AssertStmt,
    ProcDeclStmt, Param, ProbBlockStmt, CausalBlockStmt, VerifyBlockStmt,
    Token,
)
from src.builtins import Builtins
from src.lexer import TokenType
from typing import Any, List, Dict, Optional, Union
import math


class InterpreterError(Exception):
    def __init__(self, message, node=None):
        self.node = node
        super().__init__(message)


class Environment:
    """Symbol table with nested scopes."""
    def __init__(self, parent=None):
        self.vars: Dict[str, Any] = {}
        self.consts: Dict[str, Any] = {}
        self.types: Dict[str, Any] = {}  # Store type info (primitives, records, arrays, procs)
        self.functions: Dict[str, Any] = {}
        self.parent = parent

    def define(self, name: str, value: Any, is_const: bool = False):
        if is_const:
            if name in self.consts:
                raise InterpreterError(f"Constant '{name}' already defined")
            self.consts[name] = value
        else:
            if name in self.vars:
                raise InterpreterError(f"Variable '{name}' already defined")
            self.vars[name] = value

    def undefined(self, name: str) -> bool:
        return (name not in self.vars and name not in self.consts and
                (self.parent is None or self.parent.undefined(name)))

    def get(self, name: str) -> Any:
        if name in self.vars:
            return self.vars[name]
        if name in self.consts:
            return self.consts[name]
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get(name)
        raise InterpreterError(f"Undefined identifier '{name}'")

    def set(self, name: str, value: Any):
        if name in self.vars:
            self.vars[name] = value
        elif self.parent:
            self.parent.set(name, value)
        else:
            raise InterpreterError(f"Undefined variable '{name}' for assignment")

    def define_type(self, name: str, type_info):
        self.types[name] = type_info

    def get_type(self, name: str):
        if name in self.types:
            return self.types[name]
        if self.parent:
            return self.parent.get_type(name)
        raise InterpreterError(f"Undefined type '{name}'")

    def define_function(self, name: str, func):
        self.functions[name] = func

    def get_function(self, name: str):
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get_function(name)
        raise InterpreterError(f"Undefined function '{name}'")


class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        self.current_env = self.global_env
        self._setup_builtins()

    def _setup_builtins(self):
        # Register built-in functions
        for name in dir(Builtins):
            if not name.startswith('_') and callable(getattr(Builtins, name)):
                self.global_env.define_function(name, getattr(Builtins, name))

    def eval(self, node):
        """Dispatch to appropriate eval method."""
        method_name = f'eval_{type(node).__name__}'
        if hasattr(self, method_name):
            return getattr(self, method_name)(node)
        else:
            raise InterpreterError(f"No eval method for {type(node).__name__}")

    def eval_Program(self, program: Program):
        # First pass: register types and function declarations (for forward refs)
        for decl in program.declarations:
            if isinstance(decl, TypeDeclStmt):
                self.eval_type_decl(decl)
            elif isinstance(decl, ProcDeclStmt):
                # Register function with a placeholder that will be filled later
                self.current_env.define_function(decl.name, self._make_proc_function(decl))

        # Second pass: evaluate top-level statements (including var/const init and function calls)
        result = None
        for stmt in program.statements:
            result = self.eval(stmt)
        return result

    def _make_proc_function(self, decl: ProcDeclStmt):
        """Create a callable function object for a proc declaration."""
        def proc_func(*args):
            # Create new environment with closure over current scope? For now, no closures beyond global.
            # In MVP, we don't support nested functions, so closure is just global.
            old_env = self.current_env
            self.current_env = Environment(parent=self.global_env if decl.name not in self.global_env.functions else old_env)
            # Actually, for top-level procs, parent should be global_env (so they can access globals).
            self.current_env = Environment(parent=self.global_env)

            # Bind parameters
            if len(args) != len(decl.params):
                raise InterpreterError(f"Proc '{decl.name}' expects {len(decl.params)} arguments, got {len(args)}")
            for param, arg_val in zip(decl.params, args):
                self.current_env.define(param.name, arg_val, is_const=False)

            # Execute body
            try:
                if isinstance(decl.body, BlockStmt):
                    result = self.eval(decl.body)
                else:
                    result = self.eval(decl.body)
                # If proc has return type and body is block, we look for return statements
                # For expression form, result is the expression value.
                # We'll treat return from expression body as implicit return.
                # But if we encountered a ReturnStmt inside, it would have raised ReturnException.
                # Instead we use exception to break execution.
                # We'll implement return via exception in block handling.
                return result
            except ReturnValue as rv:
                return rv.value
            finally:
                self.current_env = old_env
        return proc_func

    def eval_type_decl(self, decl: TypeDeclStmt):
        # For simple primitive type aliases, we just store the alias.
        # For composite types (arrays, records, procs), we need to parse the type_def.
        # In our TypeDeclStmt, type_def could be None for primitive alias.
        # We'll handle store of type info as needed.
        # For MVP, we might not need full type info stored separately; we can just remember that a type name exists.
        self.current_env.define_type(decl.name, None)  # placeholder
        # Actually we could parse the type_def here; but type_def may be already parsed in parser
        # We can just store that name is a type.
        pass

    def eval_VarDeclStmt(self, stmt: VarDeclStmt):
        if stmt.init_expr:
            init_val = self.eval(stmt.init_expr)
        else:
            # Default initialization: 0 for numeric, false for bool, "" for string, etc.
            # We need to know declared type. For inferred: use init_val's type.
            if stmt.type_name:
                init_val = self.default_value(stmt.type_name)
            else:
                init_val = None  # Should not happen if type inference
        self.current_env.define(stmt.name, init_val, is_const=False)
        # Store type info if present
        if stmt.type_name:
            # Could store in env.types for later checking, but we already enforced during semantic?
            pass

    def eval_ConstDeclStmt(self, stmt: ConstDeclStmt):
        value = self.eval(stmt.init_expr)
        self.current_env.define(stmt.name, value, is_const=True)

    def eval_AssignmentStmt(self, stmt: AssignmentStmt):
        value = self.eval(stmt.value)
        if isinstance(stmt.target, IdentifierExpr):
            self.current_env.set(stmt.target.name, value)
        elif isinstance(stmt.target, ArrayIndexExpr):
            array = self.eval(stmt.target.array)
            index = self.eval(stmt.target.index)
            # Convert index to 0-based for Python list
            if isinstance(index, int):
                idx0 = index - 1
                if idx0 < 0 or idx0 >= len(array):
                    raise InterpreterError(f"Array index {index} out of bounds")
                array[idx0] = value
            else:
                raise InterpreterError("Array index must be integer")
        elif isinstance(stmt.target, RecordAccessExpr):
            record = self.eval(stmt.target.record)
            if isinstance(record, dict):
                record[stmt.target.field] = value
            else:
                raise InterpreterError(f"Cannot access field on non-record type")
        else:
            raise InterpreterError("Invalid assignment target")

    def eval_ProcCallStmt(self, stmt: ProcCallStmt):
        callee = self.eval(stmt.callee)
        args = [self.eval(arg) for arg in stmt.args]
        if callable(callee):
            result = callee(*args)
            return result
        else:
            raise InterpreterError(f"'{callee}' is not callable")

    def eval_CallExpr(self, expr: CallExpr) -> Any:
        callee = self.eval(expr.callee)
        args = [self.eval(arg) for arg in expr.args]
        if callable(callee):
            return callee(*args)
        else:
            raise InterpreterError(f"'{callee}' is not callable")

    def eval_IfStmt(self, stmt: IfStmt):
        condition = self.eval(stmt.condition)
        if not isinstance(condition, bool):
            raise InterpreterError("Condition must be boolean")
        if condition:
            return self.eval(stmt.then_branch)
        elif stmt.else_branch:
            return self.eval(stmt.else_branch)

    def eval_WhileStmt(self, stmt: WhileStmt):
        while True:
            condition = self.eval(stmt.condition)
            if not isinstance(condition, bool):
                raise InterpreterError("While condition must be boolean")
            if not condition:
                break
            self.eval(stmt.body)

    def eval_ForStmt(self, stmt: ForStmt):
        start_val = self.eval(stmt.start)
        end_val = self.eval(stmt.end)
        step_val = self.eval(stmt.step) if stmt.step else (1 if stmt.direction == 'to' else -1)
        if not all(isinstance(v, int) for v in (start_val, end_val, step_val)):
            raise InterpreterError("For loop indices must be integers")
        # Create a new scope for iterator variable
        self.current_env = Environment(parent=self.current_env)
        try:
            if stmt.direction == 'to':
                i = start_val
                while i <= end_val:
                    self.current_env.define(stmt.iterator, i, is_const=False)
                    self.eval(stmt.body)
                    i += step_val
            else:  # downto
                i = start_val
                while i >= end_val:
                    self.current_env.define(stmt.iterator, i, is_const=False)
                    self.eval(stmt.body)
                    i += step_val  # step should be negative
        finally:
            self.current_env = self.current_env.parent

    def eval_ReturnStmt(self, stmt: ReturnStmt):
        value = self.eval(stmt.value) if stmt.value else None
        raise ReturnValue(value)

    def eval_BlockStmt(self, stmt: BlockStmt):
        # New scope
        old_env = self.current_env
        self.current_env = Environment(parent=old_env)
        try:
            result = None
            for s in stmt.statements:
                result = self.eval(s)
            return result
        finally:
            self.current_env = old_env

    def eval_ExprStmt(self, stmt: ExprStmt):
        return self.eval(stmt.expr)

    def eval_SkipStmt(self, stmt: SkipStmt):
        pass

    def eval_AssertStmt(self, stmt: AssertStmt):
        condition = self.eval(stmt.condition)
        if not isinstance(condition, bool):
            raise InterpreterError("Assert condition must be boolean")
        if not condition:
            raise InterpreterError("Assertion failed")

    def eval_ProbBlockStmt(self, stmt: ProbBlockStmt):
        # MVP stub: just execute statements sequentially, ignoring probabilistic semantics
        for s in stmt.statements:
            self.eval(s)

    def eval_CausalBlockStmt(self, stmt: CausalBlockStmt):
        # MVP stub: execute statements
        for s in stmt.statements:
            self.eval(s)

    def eval_VerifyBlockStmt(self, stmt: VerifyBlockStmt):
        # MVP stub: optionally runtime check? We'll just eval the condition but not enforce
        # For debugging, we could assert
        condition = self.eval(stmt.condition)
        if not isinstance(condition, bool):
            raise InterpreterError("Verify condition must be boolean")
        if not condition:
            # In debug mode, we could raise error; in release, ignore
            # For MVP, we'll just print a warning
            print(f"VERIFICATION FAILED: {stmt.message or ''}")

    # Expressions
    def eval_LiteralExpr(self, expr: LiteralExpr):
        return expr.value

    def eval_IdentifierExpr(self, expr: IdentifierExpr):
        return self.current_env.get(expr.name)

    def eval_BinaryOpExpr(self, expr: BinaryOpExpr) -> Any:
        left = self.eval(expr.left)
        right = self.eval(expr.right)
        op = expr.op.type

        # Arithmetic
        if op == TokenType.PLUS:
            return left + right
        elif op == TokenType.MINUS:
            return left - right
        elif op == TokenType.STAR:
            return left * right
        elif op == TokenType.SLASH:
            if right == 0:
                raise InterpreterError("Division by zero")
            return left / right
        elif op == TokenType.PERCENT:
            if right == 0:
                raise InterpreterError("Modulo by zero")
            return left % right
        elif op == TokenType.CARET:
            return left ** right
        # Comparison
        elif op == TokenType.EQ:
            return left == right
        elif op == TokenType.NEQ:
            return left != right
        elif op == TokenType.LT:
            return left < right
        elif op == TokenType.LTE:
            return left <= right
        elif op == TokenType.GT:
            return left > right
        elif op == TokenType.GTE:
            return left >= right
        # Logical
        elif op == TokenType.AND:
            return left and right
        elif op == TokenType.OR:
            return left or right
        elif op == TokenType.AMP:
            # Bitwise AND
            return left & right
        elif op == TokenType.PIPE:
            return left | right
        elif op == TokenType.TILDE:
            return ~right
        elif op == TokenType.DOUBLE_COLON:
            # List cons: left :: right
            # For MVP: treat as list concatenation? Or cons (prepends)
            # We'll implement as [left] + right if right is list
            if isinstance(right, list):
                return [left] + right
            else:
                raise InterpreterError("Right operand of :: must be a list")
        else:
            raise InterpreterError(f"Unknown binary operator {op.name}")

    def eval_UnaryOpExpr(self, expr: UnaryOpExpr) -> Any:
        operand = self.eval(expr.operand)
        op = expr.op.type
        if op == TokenType.MINUS:
            return -operand
        elif op == TokenType.NOT:
            return not operand
        elif op == TokenType.AMP:
            # Address-of? In MVP not implemented; could be used for ref
            # We'll return operand as is
            return operand
        elif op == TokenType.STAR:
            # Dereference? Not implemented
            if isinstance(operand, list):
                # Perhaps treat as array?
                raise InterpreterError("Dereference not supported")
            return operand
        else:
            raise InterpreterError(f"Unknown unary operator {op.name}")

    def eval_ArrayIndexExpr(self, expr: ArrayIndexExpr) -> Any:
        array = self.eval(expr.array)
        index = self.eval(expr.index)
        if not isinstance(array, list):
            raise InterpreterError("Indexing into non-array")
        if not isinstance(index, int):
            raise InterpreterError("Array index must be integer")
        idx0 = index - 1  # Convert 1-based to 0-based
        if idx0 < 0 or idx0 >= len(array):
            raise InterpreterError(f"Array index {index} out of bounds (size {len(array)})")
        return array[idx0]

    def eval_RecordAccessExpr(self, expr: RecordAccessExpr) -> Any:
        record = self.eval(expr.record)
        if not isinstance(record, dict):
            raise InterpreterError(f"Cannot access field on non-record")
        if expr.field not in record:
            raise InterpreterError(f"Record has no field '{expr.field}'")
        return record[expr.field]

    def eval_ArrayConstructorExpr(self, expr: ArrayConstructorExpr) -> List[Any]:
        return [self.eval(elem) for elem in expr.elements]

    def eval_RecordConstructorExpr(self, expr: RecordConstructorExpr) -> Dict[str, Any]:
        # Need to look up the record type to validate fields
        try:
            type_info = self.current_env.get_type(expr.type_name)
            # For now, type_info may not be fully structured; we'll skip validation in MVP
        except:
            pass
        result = {}
        for field, value_expr in expr.field_values.items():
            result[field] = self.eval(value_expr)
        return result

    def eval_ParenExpr(self, expr: ParenExpr):
        return self.eval(expr.expr)

    # Utility
    def default_value(self, type_name: str) -> Any:
        """Return default zero value for a type."""
        if type_name == 'int':
            return 0
        elif type_name == 'real':
            return 0.0
        elif type_name == 'bool':
            return False
        elif type_name == 'char':
            return '\0'
        elif type_name == 'string':
            return ""
        elif type_name.startswith('array['):
            # Parse array type string? In MVP we might not have it stored properly.
            # Return empty array of some size? Not needed.
            return []
        elif type_name.startswith('record('):
            # Need to construct record with default fields
            return {}
        else:
            # User-defined type? Not sure.
            return None


# Exception for early return
class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value
