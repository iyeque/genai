"""
ALGOL 26 Type Inference Engine

Hindley-Milner based constraint generation and solving.
Supports:
- Parametric polymorphism
- Algebraic Data Types (ADT) - stub
- Row polymorphism for records
- Lightweight effect tracking (stub)
"""

from typing import List, Optional, Dict, Any, Set, Tuple
from dataclasses import dataclass, field

from src.type_system import (
    Type, TypeVar, FunctionType, ArrayType, RecordType, ADTType, ADTConstructor,
    PrimitiveType, TypeName, BuiltinType, Substitution, UnificationError,
    fresh_type_var, fresh_row_var,
    INT_TYPE, REAL_TYPE, BOOL_TYPE, STRING_TYPE, CHAR_TYPE, VOID_TYPE,
    apply_subst, compose_subst,
)
from src.ast import (
    ASTNode, Expr, Stmt,
    LiteralExpr, IdentifierExpr, BinaryOpExpr, UnaryOpExpr, CallExpr,
    ArrayIndexExpr, RecordAccessExpr, ArrayConstructorExpr, RecordConstructorExpr,
    ParenExpr, TernaryExpr, ProbExpr, SampleExpr,
    VarDeclStmt, ConstDeclStmt, TypeDeclStmt, AssignmentStmt, ProcCallStmt,
    IfStmt, WhileStmt, ForStmt, ReturnStmt, BlockStmt, ExprStmt, SkipStmt, AssertStmt,
    ProbBlockStmt, CausalBlockStmt, VerifyBlockStmt,
    ImportStmt, ExportStmt, ModuleDeclStmt,
    ProcDeclStmt, Param,
)
import os
from src.lexer import TokenType



class TypeCheckError(Exception):
    def __init__(self, message, node=None):
        self.node = node
        super().__init__(message)


@dataclass
class TypeScheme:
    """Universal quantification over type variables."""
    type_vars: List[TypeVar]
    mono_type: Type

    def instantiate(self) -> Type:
        """Replace quantified variables with fresh flexible variables."""
        subst = {}
        for var in self.type_vars:
            fresh = TypeVar(fresh_type_var(), is_rigid=False)
            subst[var] = fresh
        return apply_subst(self.mono_type, Substitution(subst))

    def free_vars(self) -> Set[TypeVar]:
        fv = self.mono_type.free_vars()
        quantified = set(self.type_vars)
        return fv - quantified

    def __str__(self):
        if not self.type_vars:
            return str(self.mono_type)
        tvars = ', '.join(str(tv) for tv in self.type_vars)
        return f"forall {tvars}. {self.mono_type}"


@dataclass
class Env:
    """Typing environment."""
    entries: Dict[str, TypeScheme] = field(default_factory=dict)
    parent: Optional['Env'] = field(default=None)

    def lookup(self, name: str) -> Optional[TypeScheme]:
        if name in self.entries:
            return self.entries[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def extend(self, name: str, scheme: TypeScheme):
        self.entries[name] = scheme


class ConstraintGenerator:
    """
    Generates type constraints and solves them.
    Works in two phases: first process type declarations, then rest.
    """

    def __init__(self, base_path=None):
        self.base_path = base_path or os.getcwd()
        self.module_cache: Dict[str, Tuple[Env, Set[str]]] = {}
        self.loading_stack: List[str] = []
        self.exports: Set[str] = set()  # Exported names for this module
        self.env = Env()
        self.constraints: List[tuple] = []  # (t1, t2, node)
        self.current_return_type: Optional[Type] = None
        self.builtins = {
            # Simple builtins with exact types
            'sqrt': FunctionType([REAL_TYPE], REAL_TYPE),
            'sin': FunctionType([REAL_TYPE], REAL_TYPE),
            'cos': FunctionType([REAL_TYPE], REAL_TYPE),
            'tan': FunctionType([REAL_TYPE], REAL_TYPE),
            'exp': FunctionType([REAL_TYPE], REAL_TYPE),
            'log': FunctionType([REAL_TYPE], REAL_TYPE),
            'log10': FunctionType([REAL_TYPE], REAL_TYPE),
            'floor': FunctionType([REAL_TYPE], INT_TYPE),
            'ceil': FunctionType([REAL_TYPE], INT_TYPE),
            'round': FunctionType([REAL_TYPE, INT_TYPE], REAL_TYPE),  # simplified: two args
            'abs': FunctionType([INT_TYPE], INT_TYPE),  # simplified; real overload not handled
            'len': FunctionType([TypeName('array')], INT_TYPE),  # placeholder; actual will be generic
            # Polymorphic builtins we'll handle specially in inference: println, print, int, real, char, string, bytes
        }
        # Special builtins that accept any arguments
        self.dynamic_builtins = {'println', 'print', 'int', 'real', 'char', 'string', 'bytes'}
        # Add primitive types to env
        for name, typ in [('int', INT_TYPE), ('real', REAL_TYPE), ('bool', BOOL_TYPE),
                          ('char', CHAR_TYPE), ('string', STRING_TYPE), ('void', VOID_TYPE)]:
            self.env.extend(name, TypeScheme([], typ))
        # Add builtin functions
        for name, typ in self.builtins.items():
            self.env.extend(name, TypeScheme([], typ))
        for name in self.dynamic_builtins:
            self.env.extend(name, TypeScheme([], BuiltinType(name)))

    def add_constraint(self, t1: Type, t2: Type, node=None):
        self.constraints.append((t1, t2, node))

    def resolve_type(self, typ: Type) -> Type:
        """Resolve TypeName by looking up in env."""
        if isinstance(typ, TypeName):
            scheme = self.env.lookup(typ.name)
            if scheme is None:
                raise TypeCheckError(f"Unknown type '{typ.name}'")
            return scheme.instantiate()
        elif isinstance(typ, (ArrayType, RecordType, FunctionType)):
            # Recursively resolve components
            if isinstance(typ, ArrayType):
                elem_resolved = self.resolve_type(typ.element_type)
                return ArrayType(elem_resolved, typ.size)
            elif isinstance(typ, RecordType):
                fields_resolved = {name: self.resolve_type(ft) for name, ft in typ.fields.items()}
                row = None
                if typ.row_var:
                    # row_var is TypeVar; no need to resolve
                    row = typ.row_var
                return RecordType(fields_resolved, row)
            elif isinstance(typ, FunctionType):
                params_resolved = [self.resolve_type(p) for p in typ.param_types]
                ret_resolved = self.resolve_type(typ.return_type)
                return FunctionType(params_resolved, ret_resolved, typ.effect)
        elif isinstance(typ, TypeVar):
            # Nothing to resolve
            return typ
        elif isinstance(typ, PrimitiveType) or isinstance(typ, BuiltinType) or isinstance(typ, ADTType):
            return typ
        else:
            raise TypeCheckError(f"Unsupported type during resolve: {type(typ)}")

    def process_type_decl(self, decl):
        """Handle type typeDeclStmt: alias or record, array, proc."""
        name = decl.name
        # Resolve the type annotation using current env (which may not yet contain name)
        # For forward references, we'd need to pre-register the name with a placeholder.
        # We'll first instantiate a placeholder TypeName? Actually we can just resolve the RHS; if it contains TypeName(name) (self-reference), that's an error unless it's an ADT (handled later). For now, disallow.
        resolved = self.resolve_type(decl.type_annot)
        self.env.extend(name, TypeScheme([], resolved))

    def process_var_decl(self, decl):
        if decl.init_expr is None:
            if decl.type_annot is None:
                raise TypeCheckError("Variable without initializer requires explicit type", decl)
            # No init, just annotate
            var_type = self.resolve_type(decl.type_annot)
            scheme = self.generalize(var_type, self.env)
            self.env.extend(decl.name, scheme)
        else:
            init_type = self.infer_expr(decl.init_expr)
            if decl.type_annot is not None:
                declared_type = self.resolve_type(decl.type_annot)
                self.unify(decl, init_type, declared_type)
                var_type = declared_type
            else:
                var_type = init_type
            scheme = self.generalize(var_type, self.env)
            self.env.extend(decl.name, scheme)

    def process_const_decl(self, decl):
        if decl.init_expr is None:
            raise TypeCheckError("Constant requires initializer", decl)
        init_type = self.infer_expr(decl.init_expr)
        declared_type = self.resolve_type(decl.type_annot)
        self.unify(decl, init_type, declared_type)
        scheme = self.generalize(declared_type, self.env)
        self.env.extend(decl.name, scheme)

    def process_proc_decl(self, decl):
        # Parameter types
        param_types = [self.resolve_type(p.type_annot) for p in decl.params]
        # Return type
        if decl.return_type is not None:
            return_type = self.resolve_type(decl.return_type)
        else:
            return_type = VOID_TYPE
        # Create function type
        func_type = FunctionType(param_types, return_type)
        # Generalize at top-level: quantify any free vars in func_type not in env
        scheme = self.generalize(func_type, self.env)
        self.env.extend(decl.name, scheme)

        # Type-check body in extended env with parameters
        old_return = self.current_return_type
        self.current_return_type = return_type
        body_env = Env(parent=self.env)
        for param, p_type in zip(decl.params, param_types):
            body_env.extend(param.name, TypeScheme([], p_type))
        old_env = self.env
        self.env = body_env
        try:
            if isinstance(decl.body, BlockStmt):
                self.infer_stmt(decl.body)
            else:
                # Expression body
                expr_type = self.infer_expr(decl.body)
                if return_type != VOID_TYPE:
                    self.unify(decl, expr_type, return_type)
        finally:
            self.env = old_env
            self.current_return_type = old_return

    def unify(self, node, t1, t2):
        """Unify two types, applying current substitution implicitly."""
        # Apply current accumulated substitution? We'll solve all at end, but we can also do on the fly.
        # For simplicity, we'll collect constraints and unify all at end.
        self.add_constraint(t1, t2, node)

    def generalize(self, typ: Type, env: Env) -> TypeScheme:
        fv = typ.free_vars()
        # Collect all quantified type variables from env (free in schemes)
        env_fvs = set()
        def walk(e):
            for sch in e.entries.values():
                env_fvs.update(sch.free_vars())
            if e.parent:
                walk(e.parent)
        walk(env)
        to_generalize = fv - env_fvs
        if not to_generalize:
            return TypeScheme([], typ)
        # Create substitution from each var to a new rigid TypeVar
        subst_map = {}
        for var in to_generalize:
            # Create a new rigid TypeVar with a fresh name
            fresh = TypeVar(fresh_type_var(), is_rigid=True)
            subst_map[var] = fresh
        new_typ = apply_subst(typ, Substitution(subst_map))
        quantified = list(subst_map.values())
        return TypeScheme(quantified, new_typ)

    def infer_program(self, program) -> Env:
        """Main entry: type-check program and return final environment."""
        # First pass: process all type declarations (top-level)
        for decl in program.declarations:
            if isinstance(decl, TypeDeclStmt):
                try:
                    self.process_type_decl(decl)
                except Exception as e:
                    raise TypeCheckError(f"Type declaration error: {e}", decl)

        # Second pass: process other declarations (var, const, proc)
        for decl in program.declarations:
            if isinstance(decl, (VarDeclStmt, ConstDeclStmt, ProcDeclStmt)):
                try:
                    if isinstance(decl, VarDeclStmt):
                        self.process_var_decl(decl)
                    elif isinstance(decl, ConstDeclStmt):
                        self.process_const_decl(decl)
                    elif isinstance(decl, ProcDeclStmt):
                        self.process_proc_decl(decl)
                except Exception as e:
                    raise TypeCheckError(f"Declaration error: {e}", decl)

        # Type-check top-level statements
        for stmt in program.statements:
            try:
                self.infer_stmt(stmt)
            except Exception as e:
                raise TypeCheckError(f"Statement error: {e}", stmt)

        # Solve constraints
        subst = self.solve_constraints()
        # Apply substitution to environment types
        self.apply_subst_to_env(subst)
        return self.env

    def solve_constraints(self) -> Substitution:
        subst = Substitution()
        for t1, t2, node in self.constraints:
            t1_sub = apply_subst(t1, subst)
            t2_sub = apply_subst(t2, subst)
            try:
                s = unify(t1_sub, t2_sub)
                subst = compose_subst(s, subst)
            except UnificationError as e:
                raise TypeCheckError(f"Type mismatch: {e}", node)
        return subst

    def apply_subst_to_env(self, subst: Substitution):
        def apply_scheme(sch):
            new_mono = apply_subst(sch.mono_type, subst)
            return TypeScheme(sch.type_vars, new_mono)
        def walk(env):
            for name, sch in env.entries.items():
                env.entries[name] = apply_scheme(sch)
            if env.parent:
                walk(env.parent)
        walk(self.env)

    # --- Inference for expressions and statements ---

    def infer_expr(self, expr: Expr) -> Type:
        if isinstance(expr, LiteralExpr):
            # Determine type from token
            tok = expr.token
            if tok.type == TokenType.INTEGER:
                return INT_TYPE
            elif tok.type == TokenType.REAL:
                return REAL_TYPE
            elif tok.type in (TokenType.TRUE, TokenType.FALSE):
                return BOOL_TYPE
            elif tok.type == TokenType.CHAR:
                return CHAR_TYPE
            elif tok.type == TokenType.STRING:
                return STRING_TYPE
            elif tok.type == TokenType.NULL:
                # null type; could be a special null type that unifies with any nullable? We'll treat as its own.
                return PrimitiveType('null')
            else:
                raise TypeCheckError(f"Unknown literal type", expr)

        elif isinstance(expr, IdentifierExpr):
            scheme = self.env.lookup(expr.name)
            if scheme is None:
                # Check if it's a builtin dynamic function
                if expr.name in self.dynamic_builtins:
                    # Return a builtin type; calls will be handled separately
                    return BuiltinType(expr.name)
                raise TypeCheckError(f"Undefined identifier '{expr.name}'", expr)
            return scheme.instantiate()

        elif isinstance(expr, BinaryOpExpr):
            left_type = self.infer_expr(expr.left)
            right_type = self.infer_expr(expr.right)
            result_type = TypeVar(fresh_type_var())
            op = expr.op.type
            if op in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT, TokenType.CARET):
                # Check that both operands are numeric (int or real) or type variables
                numeric_types = {INT_TYPE, REAL_TYPE}
                if (left_type not in numeric_types and not isinstance(left_type, TypeVar)) or (right_type not in numeric_types and not isinstance(right_type, TypeVar)):
                    raise TypeCheckError(f"Arithmetic operator expects numeric operands, got {left_type} and {right_type}", expr)
                # Result type determination:
                if op == TokenType.SLASH:
                    # Division always yields real
                    result_type = REAL_TYPE
                elif left_type == REAL_TYPE or right_type == REAL_TYPE:
                    result_type = REAL_TYPE
                else:
                    result_type = INT_TYPE
            elif op in (TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
                self.unify(expr, left_type, right_type)
                self.unify(expr, result_type, BOOL_TYPE)
            elif op in (TokenType.AND, TokenType.OR):
                self.unify(expr, left_type, BOOL_TYPE)
                self.unify(expr, right_type, BOOL_TYPE)
                self.unify(expr, result_type, BOOL_TYPE)
            else:
                raise TypeCheckError(f"Unsupported binary operator {op.name}", expr)
            return result_type

        elif isinstance(expr, UnaryOpExpr):
            operand_type = self.infer_expr(expr.operand)
            result_type = TypeVar(fresh_type_var())
            op = expr.op.type
            if op == TokenType.NOT:
                self.unify(expr, operand_type, BOOL_TYPE)
                self.unify(expr, result_type, BOOL_TYPE)
            elif op in (TokenType.PLUS, TokenType.MINUS):
                self.unify(expr, operand_type, result_type)
            else:
                raise TypeCheckError(f"Unsupported unary operator {op.name}", expr)
            return result_type

        elif isinstance(expr, CallExpr):
            callee_type = self.infer_expr(expr.callee)
            arg_types = [self.infer_expr(arg) for arg in expr.args]
            ret_type = TypeVar(fresh_type_var())
            # Special handling for builtin dynamic functions
            if isinstance(callee_type, BuiltinType):
                # For these, we skip argument checking; just return appropriate result.
                # For println/print, return VOID_TYPE
                if callee_type.name in ('println', 'print'):
                    return VOID_TYPE
                elif callee_type.name in ('int', 'real', 'char', 'string', 'bytes'):
                    # Conversion functions: one argument, return specific type
                    # We could still check arg count
                    if len(arg_types) != 1:
                        raise TypeCheckError(f"{callee_type.name} expects 1 argument", expr)
                    if callee_type.name == 'int':
                        return INT_TYPE
                    elif callee_type.name == 'real':
                        return REAL_TYPE
                    elif callee_type.name == 'char':
                        return CHAR_TYPE
                    elif callee_type.name == 'string':
                        return STRING_TYPE
                    elif callee_type.name == 'bytes':
                        # bytes type? Not defined; treat as string? We'll just return string.
                        return STRING_TYPE
                else:
                    # Unknown builtin, return fresh var
                    return ret_type
            # Normal function: must be FunctionType
            if not isinstance(callee_type, FunctionType):
                raise TypeCheckError(f"Expression '{expr.callee}' is not callable", expr)
            if len(callee_type.param_types) != len(arg_types):
                raise TypeCheckError(f"Function expects {len(callee_type.param_types)} arguments, got {len(arg_types)}", expr)
            for p_type, a_type in zip(callee_type.param_types, arg_types):
                self.unify(expr, a_type, p_type)
            # Also unify effects? ignore.
            return callee_type.return_type

        elif isinstance(expr, ArrayIndexExpr):
            array_type = self.infer_expr(expr.array)
            index_type = self.infer_expr(expr.index)
            elem_type = TypeVar(fresh_type_var())
            self.unify(expr, array_type, ArrayType(elem_type, None))  # size ignored
            self.unify(expr, index_type, INT_TYPE)
            return elem_type

        elif isinstance(expr, RecordAccessExpr):
            record_type = self.infer_expr(expr.record)
            field_type = TypeVar(fresh_type_var())
            row_var = fresh_row_var()
            expected = RecordType(fields={expr.field: field_type}, row_var=row_var)
            self.unify(expr, record_type, expected)
            return field_type

        elif isinstance(expr, ArrayConstructorExpr):
            if not expr.elements:
                # Empty array: return a polymorphic array type
                elem_type = TypeVar(fresh_type_var())
                return ArrayType(elem_type, None)
            else:
                elem_types = [self.infer_expr(e) for e in expr.elements]
                # All elements must have same type
                first = elem_types[0]
                for i, et in enumerate(elem_types[1:], start=1):
                    self.unify(expr, first, et)
                return ArrayType(first, None)

        elif isinstance(expr, RecordConstructorExpr):
            # Look up the record type by name
            scheme = self.env.lookup(expr.type_name)
            if scheme is None:
                raise TypeCheckError(f"Unknown record type '{expr.type_name}'", expr)
            record_type = scheme.instantiate()
            if not isinstance(record_type, RecordType):
                raise TypeCheckError(f"Type '{expr.type_name}' is not a record", expr)
            # For each field in expr.field_values, check type matches record_type.fields
            for field_name, value_expr in expr.field_values.items():
                if field_name not in record_type.fields:
                    raise TypeCheckError(f"Record '{expr.type_name}' has no field '{field_name}'", expr)
                field_type = record_type.fields[field_name]
                value_type = self.infer_expr(value_expr)
                self.unify(expr, value_type, field_type)
            # Return the record type itself (closed)
            return record_type

        elif isinstance(expr, ParenExpr):
            return self.infer_expr(expr.expr)

        elif isinstance(expr, TernaryExpr):
            cond_type = self.infer_expr(expr.condition)
            self.unify(expr, cond_type, BOOL_TYPE)
            then_type = self.infer_expr(expr.then_expr)
            else_type = self.infer_expr(expr.else_expr)
            result_type = TypeVar(fresh_type_var())
            self.unify(expr, then_type, else_type)
            self.unify(expr, then_type, result_type)
            return result_type

        # ProbExpr and SampleExpr are not implemented in MVP
        elif isinstance(expr, (ProbExpr, SampleExpr)):
            raise TypeCheckError("Probabilistic expressions not yet supported", expr)

        else:
            raise TypeCheckError(f"Unsupported expression type: {type(expr).__name__}", expr)

    def infer_stmt(self, stmt: Stmt):
        if isinstance(stmt, VarDeclStmt):
            self.process_var_decl(stmt)
        elif isinstance(stmt, ConstDeclStmt):
            self.process_const_decl(stmt)
        elif isinstance(stmt, AssignmentStmt):
            self.infer_assignment(stmt)
        elif isinstance(stmt, ProcCallStmt):
            self.infer_proc_call(stmt)
        elif isinstance(stmt, IfStmt):
            self.infer_if_stmt(stmt)
        elif isinstance(stmt, WhileStmt):
            self.infer_while_stmt(stmt)
        elif isinstance(stmt, ForStmt):
            self.infer_for_stmt(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.infer_return_stmt(stmt)
        elif isinstance(stmt, BlockStmt):
            for s in stmt.statements:
                self.infer_stmt(s)
        elif isinstance(stmt, ExprStmt):
            self.infer_expr(stmt.expr)
        elif isinstance(stmt, SkipStmt):
            pass
        elif isinstance(stmt, AssertStmt):
            cond_type = self.infer_expr(stmt.condition)
            self.unify(stmt, cond_type, BOOL_TYPE)
        elif isinstance(stmt, (ProbBlockStmt, CausalBlockStmt, VerifyBlockStmt)):
            # For now, treat as block (may contain special semantics later)
            if isinstance(stmt, VerifyBlockStmt):
                cond_type = self.infer_expr(stmt.condition)
                self.unify(stmt, cond_type, BOOL_TYPE)
            else:
                for s in stmt.statements:
                    self.infer_stmt(s)
        elif isinstance(stmt, ImportStmt):
            self.process_import(stmt)
        elif isinstance(stmt, ExportStmt):
            self.exports.update(stmt.names)
        elif isinstance(stmt, ModuleDeclStmt):
            # Module declaration; could set module name but not needed for typechecking
            pass
        else:
            raise TypeCheckError(f"Unsupported statement type: {type(stmt).__name__}", stmt)

    def infer_assignment(self, stmt: AssignmentStmt):
        target_type = self.infer_expr(stmt.target)  # This will get the type of lvalue? Actually for IdentifierExpr, it returns its declared type from env. For record/array access, it returns element type.
        value_type = self.infer_expr(stmt.value)
        self.unify(stmt, target_type, value_type)

    def infer_proc_call(self, stmt: ProcCallStmt):
        callee_type = self.infer_expr(stmt.callee)
        arg_types = [self.infer_expr(arg) for arg in stmt.args]
        ret_type = TypeVar(fresh_type_var())
        if isinstance(callee_type, BuiltinType):
            # Skip checking for dynamic builtins
            # For deterministic builtins like sqrt, callee_type will be FunctionType, not BuiltinType.
            # We'll just unify with a fake function type to satisfy? Actually we should handle other builtins (like sqrt) as FunctionType already added to env, so callee_type will be FunctionType.
            # So BuiltinType only for ones we marked dynamic. For these, we skip arity/type checks; return fresh var or void?
            if callee_type.name in ('println', 'print'):
                # These are used as statements; ignore
                return VOID_TYPE
            else:
                return ret_type
        if not isinstance(callee_type, FunctionType):
            raise TypeCheckError(f"Expression '{stmt.callee}' is not callable", stmt)
        if len(callee_type.param_types) != len(arg_types):
            raise TypeCheckError(f"Function expects {len(callee_type.param_types)} arguments, got {len(arg_types)}", stmt)
        for p_type, a_type in zip(callee_type.param_types, arg_types):
            self.unify(stmt, a_type, p_type)
        return callee_type.return_type

    def infer_if_stmt(self, stmt: IfStmt):
        cond_type = self.infer_expr(stmt.condition)
        self.unify(stmt, cond_type, BOOL_TYPE)
        self.infer_stmt(stmt.then_branch)
        if stmt.else_branch:
            self.infer_stmt(stmt.else_branch)

    def infer_while_stmt(self, stmt: WhileStmt):
        cond_type = self.infer_expr(stmt.condition)
        self.unify(stmt, cond_type, BOOL_TYPE)
        self.infer_stmt(stmt.body)

    def infer_for_stmt(self, stmt: ForStmt):
        # Loop variable is implicitly int
        # Check start/end/step are int
        start_type = self.infer_expr(stmt.start)
        end_type = self.infer_expr(stmt.end)
        self.unify(stmt, start_type, INT_TYPE)
        self.unify(stmt, end_type, INT_TYPE)
        if stmt.step:
            step_type = self.infer_expr(stmt.step)
            self.unify(stmt, step_type, INT_TYPE)
        # Body with iterator bound to int
        body_env = Env(parent=self.env)
        body_env.extend(stmt.iterator, TypeScheme([], INT_TYPE))
        old_env = self.env
        self.env = body_env
        try:
            self.infer_stmt(stmt.body)
        finally:
            self.env = old_env

    def infer_return_stmt(self, stmt: ReturnStmt):
        if self.current_return_type is None:
            raise TypeCheckError("Return statement outside function", stmt)
        if stmt.value:
            value_type = self.infer_expr(stmt.value)
            self.unify(stmt, value_type, self.current_return_type)
        else:
            self.unify(stmt, VOID_TYPE, self.current_return_type)  # ensure expected is void? Actually if function declares non-void, missing return is error. We'll allow void returns in any function? Standard: if function returns a value, return must have value. If procedure (void), return with value is error. Here, we check: if expected is not void, then value needed; if expected is void and value present, error. We'll do:
            if self.current_return_type != VOID_TYPE:
                raise TypeCheckError("Function requires a return value", stmt)



    def process_import(self, stmt: ImportStmt):
        module_name = stmt.module_name
        # Convert module name to file path components
        # Search for the module file in the search path
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
            raise TypeCheckError(f"Module '{module_name}' not found", stmt)
        # Check cache
        if file_path in self.module_cache:
            mod_env, mod_exports = self.module_cache[file_path]
        else:
            # Detect circular dependency
            if file_path in self.loading_stack:
                cycle = ' -> '.join(self.loading_stack + [file_path])
                raise TypeCheckError(f"Circular import: {cycle}", stmt)
            self.loading_stack.append(file_path)
            try:
                with open(file_path, 'r') as f:
                    source = f.read()
                from src.lexer import Lexer
                from src.parser import Parser
                lexer = Lexer(source)
                parser = Parser(lexer)
                program = parser.parse()
                # Use a new constraint generator for this module, with its own directory as base_path
                mod_base_path = os.path.dirname(file_path)
                mod_cg = ConstraintGenerator(base_path=mod_base_path)
                mod_env = mod_cg.infer_program(program)
                mod_exports = mod_cg.exports
                self.module_cache[file_path] = (mod_env, mod_exports)
            finally:
                self.loading_stack.pop()
        # Import names
        if stmt.names is not None:
            # Selective import
            for name in stmt.names:
                if name not in mod_exports:
                    raise TypeCheckError(f"Module '{module_name}' does not export '{name}'", stmt)
                scheme = mod_env.lookup(name)
                if scheme is None:
                    raise TypeCheckError(f"Imported name '{name}' not defined in module '{module_name}'", stmt)
                self.env.extend(name, scheme)
        else:
            # Wildcard import: import all exported names
            for name in mod_exports:
                scheme = mod_env.lookup(name)
                if scheme is None:
                    continue
                self.env.extend(name, scheme)
        # Handle module alias
        if stmt.alias:
            # Create a namespace record type with fields for each exported name
            fields = {}
            for name in mod_exports:
                scheme = mod_env.lookup(name)
                if scheme:
                    fields[name] = scheme.mono_type
            namespace_type = RecordType(fields)
            self.env.extend(stmt.alias, TypeScheme([], namespace_type))

# Singleton unify function used earlier
def unify(t1: Type, t2: Type) -> Substitution:
    from src.type_system import unify as type_unify
    return type_unify(t1, t2)
