"""
ALGOL 26 Typechecker Package

Provides Hindley-Milner type inference with Hindley-Milner inference,
module system, and type checking integration.
"""

from .inference import (
    Type, TypeKind, Scheme, UnificationError,
    fresh_type_var, unify, TypeEnv, generalize, instantiate,
    int_type, float_type, bool_type, string_type, unit_type,
    fun_type, var_type, con_type, builtin_env
)
from .modules import (
    Module, ModuleSignature, Export, ImportStatement, ExportStatement,
    ModuleResolver, Namespace, ModuleSource, build_signature_from_module
)
from .typecheck import (
    TypeChecker, TypeCheckError, AnnotatedNode
)

__all__ = [
    # Inference
    'Type', 'TypeKind', 'Scheme', 'UnificationError',
    'fresh_type_var', 'unify', 'TypeEnv', 'generalize', 'instantiate',
    'int_type', 'float_type', 'bool_type', 'string_type', 'unit_type',
    'fun_type', 'var_type', 'con_type', 'builtin_env',
    # Modules
    'Module', 'ModuleSignature', 'Export', 'ImportStatement', 'ExportStatement',
    'ModuleResolver', 'Namespace', 'ModuleSource', 'build_signature_from_module',
    # Typechecking
    'TypeChecker', 'TypeCheckError', 'AnnotatedNode'
]
