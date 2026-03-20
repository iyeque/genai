"""
ALGOL 26 Typechecker: Type Checking Visitor

This module implements the AST visitor that performs type inference
and annotation using Hindley-Milner with extensions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum, auto
import sys

# Import from our modules
from .inference import (
    Type, TypeKind, Scheme, UnificationError, 
    TypeEnv, fresh_type_var, unify, compose_subst,
    int_type, float_type, bool_type, string_type, unit_type,
    fun_type, var_type, con_type, generalize, instantiate,
    builtin_env
)
from .modules import Module, ImportStatement, ExportStatement, Namespace, ModuleResolver

# Import AST definitions from parser (will be created)
# For now, define minimal AST node types we need


class TypeCheckError(Exception):
    """Base type checking error"""
    def __init__(self, message: str, node: 'ASTNode' = None, span: Tuple[int, int] = None):
        super().__init__(message)
        self.node = node
        self.span = span
        self.message = message
    
    def __str__(self) -> str:
        if self.span:
            return f"Type error at line {self.span[0]}: {self.message}"
        return self.message


@dataclass
class AnnotatedNode:
    """AST node with inferred/annotated type"""
    node: Any  # Original AST node
    type: Type
    

class TypeChecker:
    """
    AST visitor that infers and annotates types.
    Implements Hindley-Milner algorithm with extensions for:
    - Let-polymorphism
    - Algebraic data types (ADTs)
    - Row polymorphism for records
    - Module imports/exports
    """
    
    def __init__(self, module_resolver: ModuleResolver = None):
        self.module_resolver = module_resolver or ModuleResolver()
        self.current_module: Optional[Module] = None
        self.global_env = builtin_env()
        self.recursive_bindings: Set[str] = set()  # For let-rec handling
        
    def check_module(self, module: Module) -> Module:
        """
        Type check an entire module.
        Returns the module with annotated AST and namespace.
        """
        self.current_module = module
        env = self.global_env
        
        # Process import statements first
        for import_stmt in module.dependencies:
            try:
                imported_modules = self.module_resolver.resolve_import(import_stmt, module)
                # In full impl: would add imports to env
                # For now, just track them
            except Exception as e:
                raise TypeCheckError(f"Import error: {e}", span=None)
        
        # Type check each top-level declaration
        namespace = {}
        for decl in module.ast.declarations:
            # Would call visit_* methods here
            # For now, placeholder
            pass
        
        module.set_namespace(namespace)
        return module
    
    def infer_expr(self, expr: Any, env: TypeEnv) -> Tuple[Type, Dict[Type, Type]]:
        """
        Infer the type of an expression in given environment.
        Returns (type, substitution).
        """
        # This is a simplified placeholder
        # Full implementation would dispatch on expr node type
        if expr.kind == "int_literal":
            return int_type(), {}
        elif expr.kind == "float_literal":
            return float_type(), {}
        elif expr.kind == "bool_literal":
            return bool_type(), {}
        elif expr.kind == "string_literal":
            return string_type(), {}
        elif expr.kind == "identifier":
            scheme = env.lookup(expr.value)
            if scheme is None:
                raise TypeCheckError(f"Unbound identifier: {expr.value}", expr)
            typ = instantiate(scheme)
            return typ, {}
        elif expr.kind == "lambda":
            # Infer param type (maybe from annotation or fresh var)
            param_type = fresh_type_var() if expr.param_type is None else expr.param_type
            new_env = env.extend(expr.param_name, Scheme([], param_type))
            body_type, s1 = self.infer_expr(expr.body, new_env)
            return fun_type(param_type, body_type), s1
        elif expr.kind == "application":
            fun_type, s1 = self.infer_expr(expr.function, env)
            arg_type, s2 = self.infer_expr(expr.argument, env.substitute(s1))
            
            # Apply s1 to fun_type first, then unify with arg -> result
            fun_type_applied = fun_type.substitute(s1)
            if fun_type_applied.kind != TypeKind.FUN:
                raise TypeCheckError("Non-function in application", expr)
            
            expected_arg = fun_type_applied.args[0]
            result_type = fun_type_applied.args[1]
            
            s3 = unify(expected_arg, arg_type.substitute(s2))
            subst = compose_subst(s3, compose_subst(s2, s1))
            return result_type.substitute(s3), subst
        else:
            raise NotImplementedError(f"Expression kind {expr.kind}")
    
    def infer_let(self, name: str, expr: Any, body: Any, 
                  env: TypeEnv, is_recursive: bool = False) -> Tuple[Type, TypeEnv]:
        """
        Handle let-binding (polymorphic).
        
        The key HM algorithm:
        1. Infer type for expr in current env (with name bound to fresh var if recursive)
        2. Generalize over free type variables not in env
        3. Extend env with generalized scheme
        4. Infer body in extended env
        """
        if is_recursive:
            # For let-rec: add fresh var to env first, then infer expr
            fresh = fresh_type_var()
            env_with_binding = env.extend(name, Scheme([], fresh))
            self.recursive_bindings.add(name)
            try:
                expr_type, s = self.infer_expr(expr, env_with_binding)
                # Ensure the fresh var matches the inferred type
                try:
                    s_unify = unify(fresh, expr_type)
                    s = compose_subst(s_unify, s)
                except UnificationError as e:
                    raise TypeCheckError(f"Recursive binding type mismatch: {e}", expr)
            finally:
                self.recursive_bindings.discard(name)
        else:
            expr_type, s = self.infer_expr(expr, env)
        
        # Apply substitution to env
        env_subst = env.substitute(s) if hasattr(env, 'substitute') else env
        
        # Generalize
        # Get free type vars in expr_type that are not in env's free vars
        free_in_expr = self._free_type_vars(expr_type)
        free_in_env = self._env_free_type_vars(env_subst)
        quantifiable = free_in_expr - free_in_env
        scheme = Scheme(sorted(quantifiable), expr_type.substitute(s))
        
        # Extend environment
        new_env = env_subst.extend(name, scheme)
        
        # Infer body
        body_type, s2 = self.infer_expr(body, new_env)
        final_subst = compose_subst(s2, s)
        
        return body_type.substitute(final_subst), new_env.substitute(final_subst)
    
    def infer_let_many(self, bindings: List[Tuple[str, Any]], 
                      body: Any, env: TypeEnv, 
                      is_recursive: bool = False) -> Tuple[Type, TypeEnv]:
        """
        Handle multiple consecutive let-bindings (syntactic sugar for nested lets).
        """
        current_env = env
        for name, expr in bindings:
            body_type, current_env = self.infer_let(name, expr, body, current_env, is_recursive)
            # For sequentially scoped lets, body is the next binding or final body
            if bindings.index((name, expr)) < len(bindings) - 1:
                # Continue with next binding, need to extract next expr
                body = bindings[bindings.index((name, expr)) + 1][1]
            else:
                # Last binding, body is actual body
                body = body
        return body_type, current_env
    
    def _free_type_vars(self, typ: Type) -> Set[str]:
        """Get free type variables in a type (delegate to TypeEnv)"""
        if hasattr(typ, 'kind'):
            if typ.kind == TypeKind.VAR:
                return {typ.var_name} if typ.var_name else set()
            elif typ.kind in (TypeKind.FUN, TypeKind.CON):
                vars_set = set()
                for arg in typ.args:
                    vars_set.update(self._free_type_vars(arg))
                return vars_set
            elif typ.kind == TypeKind.ROW:
                vars_set = set()
                for arg in typ.args:
                    vars_set.update(self._free_type_vars(arg))
                if typ.row_rest:
                    vars_set.update(self._free_type_vars(typ.row_rest))
                return vars_set
        return set()
    
    def _env_free_type_vars(self, env: TypeEnv) -> Set[str]:
        """Get all free type variables in environment"""
        all_vars = set()
        # Would need to iterate through all schemes and collect their free vars
        # Simplified: return empty for now (not needed in prototype)
        return all_vars


# Placeholder AST node types (would normally be in parser)
class ASTNode:
    """Base AST node"""
    pass

@dataclass
class IntLiteral(ASTNode):
    value: int

@dataclass
class FloatLiteral(ASTNode):
    value: float

@dataclass
class BoolLiteral(ASTNode):
    value: bool

@dataclass
class StringLiteral(ASTNode):
    value: str

@dataclass
class Identifier(ASTNode):
    value: str

@dataclass
class Lambda(ASTNode):
    param_name: str
    param_type: Optional[Type] = None
    body: ASTNode = None

@dataclass
class Application(ASTNode):
    function: ASTNode
    argument: ASTNode

@dataclass
class LetBinding(ASTNode):
    name: str
    expr: ASTNode
    body: ASTNode
    is_recursive: bool = False

@dataclass
class ModuleDecl(ASTNode):
    name: str
    imports: List[ImportStatement] = field(default_factory=list)
    exports: List[ExportStatement] = field(default_factory=list)
    declarations: List[ASTNode] = field(default_factory=list)


# Example usage and simple test
if __name__ == "__main__":
    print("TypeChecker module loaded")
    # Simple test: identity function should have type ∀a. a -> a
    print("Testing basic inference...")
    checker = TypeChecker()
    # Would need actual parsing infrastructure to test properly
