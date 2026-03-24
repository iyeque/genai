"""
ALGOL 26 Interpreter

Evaluates AST with environment, scopes, and built-in functions.
Implements the runtime semantics for MVP subset.
"""
import os

from src.ast import (
    ASTNode, Program, Expr, Stmt,
    LiteralExpr, IdentifierExpr, BinaryOpExpr, UnaryOpExpr, CallExpr,
    ArrayIndexExpr, RecordAccessExpr, ArrayConstructorExpr, RecordConstructorExpr,
    ParenExpr,
    VarDeclStmt, ConstDeclStmt, TypeDeclStmt, AssignmentStmt, ProcCallStmt,
    IfStmt, WhileStmt, ForStmt, ReturnStmt, BlockStmt, ExprStmt, SkipStmt, AssertStmt,
    ProcDeclStmt, Param, ProbBindStmt, ProbExpr, SampleExpr, GivenExpr, ProbBlockExpr,
    ProbBlockStmt, CausalBlockStmt, VerifyBlockStmt,
    Token,
)
from src.builtins import Builtins
from src.lexer import Lexer
from src.parser import Parser

from src.lexer import TokenType
from src.type_system import PrimitiveType, ArrayType, RecordType
from typing import Any, List, Dict, Optional, Union
import math
from src.distributions import Distribution


class ProbModel(Distribution):
    """A distribution defined by a prob block: executes the block to sample."""
    def __init__(self, statements: List[Stmt], closure_env: Environment):
        self.statements = statements
        self.closure_env = closure_env

    def sample(self) -> Any:
        # Create a fresh environment for this sample, inheriting from closure
        sample_env = Environment(parent=self.closure_env)
        # Use a temporary interpreter to execute the block
        # We'll create a lightweight evaluator that can run statements and expressions
        # For simplicity, reuse Interpreter but override its global environment? Actually we can just set current_env.
        # We'll create a new Interpreter instance with the same base_path, and set its global_env to sample_env? But Interpreter uses global_env for top-level.
        # Simpler: directly evaluate statements using the interpreter's methods with a custom env.
        # We'll create a new Interpreter that shares builtins etc, but we set its current_env to sample_env.
        # However, we don't have direct access to private methods. We could copy the interpreter but that's heavy.
        # Instead, we'll define a helper within this method that evaluates a statement/expr using the closure's interpreter's logic but with our sample_env.
        # We can temporarily replace the interpreter's env? Not thread safe.
        # Let's instead create a fresh Interpreter instance and pre-populate its global environment with values from closure? That is complex.
        # Simpler approach: The prob block evaluation can be done by reusing the existing interpreter's eval methods but by temporarily swapping its current_env.
        # We'll get a reference to the interpreter instance that created this ProbModel? Not stored.
        # Hmm, we need a way to evaluate ALGOL 26 AST nodes with an environment. We could duplicate the evaluation code here, but that's messy.
        #
        # Alternative design: Instead of separate ProbModel, we can store a closure that directly samples by calling an interpreter function.
        # We can store a lambda that does the sampling using the same interpreter by temporarily pushing a new environment onto a stack. That requires the interpreter's cooperation.
        #
        # Given time constraints, let's simplify: The prob block is evaluated immediately when `sample` is called by using a fresh interpreter that has access to the closure's global values. We can pass a dict of the closure's global environment values to the new interpreter.
        # The closure_env is an Environment object. We can extract its vars/consts/functions and define them in a new Environment as top-level.
        # But we need to also have access to builtins. The Interpreter's __init__ sets up global_env with builtins. Good.
        # So we'll create a new Interpreter(base_path=os.getcwd()) and then manually copy closure_env's bindings into its global_env.
        #
        # However, the closure_env may be a nested environment, not just globals. The prob block can capture locals from surrounding scope? In ALGOL 26, nested functions can capture. But for now, only top-level prob blocks are likely. So closure_env is likely the global environment of the interpreter that created the ProbModel.
        # We can store that environment's dictionaries and set as the new interpreter's global_env.vars, consts, functions.
        # Let's do that.
        #
        from src.interpreter import Interpreter  # circular? We're inside interpreter.py. Can't.
        # Oops, we are inside interpreter.py, can't import Interpreter. But we can create a new interpreter by calling Interpreter's constructor, we are in same module so we can reference the class name directly.
        # We'll define a helper function that creates a new interpreter with the closure environment's contents.
        new_interp = Interpreter(base_path=os.getcwd())
        # Copy closure environment's contents into new_interp.global_env
        # closure_env.vars, consts, functions, types? We'll copy only the mutable bindings and functions.
        new_interp.global_env.vars.update(self.closure_env.vars)
        new_interp.global_env.consts.update(self.closure_env.consts)
        new_interp.global_env.functions.update(self.closure_env.functions)
        new_interp.global_env.types.update(self.closure_env.types)
        # For nested scopes, we only need to capture the top-level closure, so ok.
        # Execute block statements in new_interp
        result = None
        for stmt in self.statements:
            if isinstance(stmt, ExprStmt):
                # The last expression's value is the result
                result = new_interp.eval(stmt.expr)
            else:
                new_interp.eval(stmt)
        return result

    def __repr__(self):
        return f"ProbModel({self.statements})"


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
    def __init__(self, base_path=None):
        self.base_path = base_path or os.getcwd()
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
            if stmt.type_annot:
                init_val = self.default_value(stmt.type_annot)
            else:
                init_val = None  # Should not happen if type inference
        self.current_env.define(stmt.name, init_val, is_const=False)
        # Store type info if present
        if stmt.type_annot:
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

    def eval_ProbBindStmt(self, stmt: ProbBindStmt):
        # Evaluate the distribution expression to a Distribution object
        dist = self.eval(stmt.distribution)
        if not isinstance(dist, Distribution):
            raise InterpreterError(f"Expected distribution in binding, got {type(dist)}", stmt)
        # Sample from the distribution and bind the identifier in the current environment
        sample_val = dist.sample()
        self.current_env.define(stmt.identifier, sample_val, is_const=False)

    # Expressions

    def eval_ImportStmt(self, stmt: ImportStmt):
        """Import symbols from another module at runtime."""
        module_name = stmt.module_name
        # Compute search directories: base_path, local, vendor, stdlib
        search_dirs = [
            self.base_path,
            os.path.join(self.base_path, 'local'),
            os.path.join(self.base_path, 'vendor'),
            os.path.join(self.base_path, 'stdlib')
        ]
        file_path = None
        for d in search_dirs:
            candidate = os.path.join(d, *module_name.split('.')) + '.algol26'
            if os.path.exists(candidate):
                file_path = candidate
                break
        if file_path is None:
            raise InterpreterError(f"Module '{module_name}' not found", stmt)
        # For simplicity, evaluate the module in a fresh interpreter and merge its global env
        # In a more efficient implementation, we could cache the module's evaluated env.
        import_interpreter = Interpreter(base_path=os.path.dirname(file_path))
        # Parse and evaluate the module file
        with open(file_path, 'r') as f:
            source = f.read()
        lexer = Lexer(source)
        parser = Parser(lexer)
        ast = parser.parse()
        # Evaluate the module (its top-level statements will populate its global_env)
        import_interpreter.eval(ast)
        # Now bring in the module's globals into current env, respecting selective import/alias
        mod_env = import_interpreter.global_env
        if stmt.names is not None:
            # Selective import: only bring listed names
            for name in stmt.names:
                if name not in mod_env.vars and name not in mod_env.consts and name not in mod_env.functions:
                    raise InterpreterError(f"Module '{module_name}' does not export '{name}'", stmt)
                if name in mod_env.vars:
                    self.current_env.define(name, mod_env.vars[name], is_const=False)
                if name in mod_env.consts:
                    self.current_env.define(name, mod_env.consts[name], is_const=True)
                if name in mod_env.functions:
                    self.current_env.define_function(name, mod_env.functions[name])
        else:
            # Wildcard import: bring all top-level bindings
            for name, value in mod_env.vars.items():
                self.current_env.define(name, value, is_const=False)
            for name, value in mod_env.consts.items():
                self.current_env.define(name, value, is_const=True)
            for name, value in mod_env.functions.items():
                self.current_env.define_function(name, value)
        # Handle alias: bind the entire module namespace as a record-like object
        if stmt.alias:
            # Create a namespace object that proxies the module's env? We'll store a simple object that holds the module's env.
            # For simplicity, we'll bind alias to a dict containing the module's symbols, but for runtime, we need attribute access.
            # We'll just bind the module's environment under the alias; then uses like alias::symbol need to be handled by interpreter.
            # But our language syntax for alias likely expects module_name as namespace prefix. That would require handling in identifier lookups.
            # To keep MVP simple, we'll just stash the module interpreter's global env as a value, and later when accessing alias.name, we need a lookup.
            # Not implemented fully; for now, we'll ignore alias or store the interpreter's global_env as a namespace object.
            self.current_env.define(stmt.alias, mod_env, is_const=False)  # store the Environment itself as a value (non-standard)
    def eval_ExportStmt(self, stmt: ExportStmt):
        # No runtime effect
        pass

    def eval_ModuleDeclStmt(self, stmt: ModuleDeclStmt):
        # No runtime effect
        pass
    def eval_LiteralExpr(self, expr: LiteralExpr):
        tok = expr.token
        if tok.type == TokenType.INTEGER:
            return int(tok.value)
        elif tok.type == TokenType.REAL:
            return float(tok.value)
        elif tok.type in (TokenType.TRUE, TokenType.FALSE):
            return tok.type == TokenType.TRUE  # true if token is TRUE
        elif tok.type == TokenType.CHAR:
            return tok.value
        elif tok.type == TokenType.STRING:
            return tok.value
        elif tok.type == TokenType.NULL:
            return None
        else:
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

    def eval_ProbBlockExpr(self, expr: ProbBlockExpr) -> Distribution:
        # Return a ProbModel representing the probabilistic block, capturing current environment as closure
        return ProbModel(expr.statements, self.current_env)

    def eval_SampleExpr(self, expr: SampleExpr) -> Any:
        dist = self.eval(expr.distribution_expr)
        if not isinstance(dist, Distribution):
            raise InterpreterError(f"Cannot sample from non-distribution: {type(dist)}", expr)
        return dist.sample()

    def eval_GivenExpr(self, expr: GivenExpr) -> Distribution:
        # MVP: not implemented
        raise NotImplementedError("Conditional distributions (given) are not yet supported")

    # Utility
    def default_value(self, type_obj) -> Any:
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
