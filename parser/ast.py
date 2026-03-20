"""
ALGOL 26 AST Module

Data structures representing the Abstract Syntax Tree.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Any


# Base AST node
class ASTNode:
    """Base class for all AST nodes"""
    pass


# Expression base
class Expr(ASTNode):
    """Base expression node"""
    pass


# Literals
@dataclass
class IntLiteral(Expr):
    """Integer literal"""
    value: int


@dataclass
class FloatLiteral(Expr):
    """Float literal"""
    value: float


@dataclass
class BoolLiteral(Expr):
    """Boolean literal"""
    value: bool


@dataclass
class StringLiteral(Expr):
    """String literal"""
    value: str


# Identifiers
@dataclass
class Identifier(Expr):
    """Variable reference"""
    name: str


# Lambda (anonymous function)
@dataclass
class Lambda(Expr):
    """Lambda expression"""
    param: Param
    body: Expr


# Function application
@dataclass
class Application(Expr):
    """Function application"""
    function: Expr
    argument: Expr


# If expression
@dataclass
class IfExpr(Expr):
    """If-then-else expression"""
    condition: Expr
    then_expr: Expr
    else_expr: Optional[Expr] = None


# Let expression (nested)
@dataclass
class LetExpr(Expr):
    """Let expression (nested)"""
    binding: LetBinding
    body: Expr


# Type base
class Type(ASTNode):
    """Base type node"""
    pass


@dataclass
class NamedType(Type):
    """Named type (possibly with type arguments)"""
    name: str
    args: List[Type] = None  # Type arguments (for generics)


@dataclass
class FunctionType(Type):
    """Function type (arg -> ret)"""
    arg_type: Type
    return_type: Type


@dataclass
class TupleType(Type):
    """Tuple type (for multiple arguments/returns)"""
    element_types: List[Type]


# Declarations
class Decl(ASTNode):
    """Base declaration"""
    pass


@dataclass
class ModuleDecl(Decl):
    """Module declaration"""
    name: str
    imports: List[ImportStmt]
    exports: List[ExportStmt]
    declarations: List[Decl]


@dataclass
class ImportStmt(Decl):
    """Import statement"""
    module_name: str  # Qualified name like "math" or "utils::vector"
    alias: Optional[str] = None
    items: Optional[List[ImportItem]] = None  # None = wildcard import
    
    def is_wildcard(self) -> bool:
        return self.items is None


@dataclass
class ImportItem(Decl):
    """Single imported item with optional rename or module spec"""
    name: str  # For items: name in module; for module spec: module name
    alias: Optional[str] = None  # Renamed name (None = keep original)
    items: Optional[List[ImportItem]] = None  # For selective imports within module spec (unused)


@dataclass
class ExportStmt(Decl):
    """Export statement"""
    items: List[ExportItem]
    
    def is_export_all(self) -> bool:
        return len(self.items) == 0


@dataclass
class ExportItem(Decl):
    """Exported item with optional rename"""
    name: str  # Name in this module to export
    alias: Optional[str] = None  # Exported under different name


@dataclass
class FuncDecl(Decl):
    """Function declaration"""
    name: str
    params: List[Param]
    body: Expr
    return_type: Optional[Type] = None  # Optional return type annotation


@dataclass
class Param(Decl):
    """Function parameter"""
    name: str
    type_annotation: Optional[Type] = None


@dataclass
class LetDecl(Decl):
    """Let binding (may be recursive if 'and' used)"""
    bindings: List[LetBinding]
    body: Expr
    
    def is_recursive(self) -> bool:
        return len(self.bindings) > 1


@dataclass
class LetBinding(Decl):
    """Single let binding"""
    name: str
    expr: Expr
    type_annotation: Optional[Type] = None  # Optional type annotation


@dataclass
class TypeDecl(Decl):
    """Type declaration (for algebraic data types)"""
    name: str
    type_expr: Type  # Type definition (e.g., ADT, type alias)
