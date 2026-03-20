"""
ALGOL 26 Abstract Syntax Tree (AST) Nodes

Represents the parsed structure of an ALGOL 26 program.
"""

from dataclasses import dataclass
from typing import List, Optional, Union, Any


# Base node
class ASTNode:
    pass


# Expressions
@dataclass
class Expr(ASTNode):
    pass


@dataclass
class LiteralExpr(Expr):
    value: Any
    token: Token  # Keep token for type information and error reporting

    def __post_init__(self):
        # Determine type from token
        if self.token.type == TokenType.INTEGER:
            self.expr_type = 'int'
            self.value = int(self.value)
        elif self.token.type == TokenType.REAL:
            self.expr_type = 'real'
            self.value = float(self.value)
        elif self.token.type in (TokenType.TRUE, TokenType.FALSE):
            self.expr_type = 'bool'
            self.value = self.value == 'true'
        elif self.token.type == TokenType.CHAR:
            self.expr_type = 'char'
        elif self.token.type == TokenType.STRING:
            self.expr_type = 'string'
        elif self.token.type == TokenType.NULL:
            self.expr_type = 'null'
        else:
            self.expr_type = None


@dataclass
class IdentifierExpr(Expr):
    name: str
    token: Token

    def __post_init__(self):
        self.expr_type = None  # To be resolved by semantic analysis


@dataclass
class BinaryOpExpr(Expr):
    left: Expr
    op: Token  # Operator token
    right: Expr

    def __post_init__(self):
        self.expr_type = None


@dataclass
class UnaryOpExpr(Expr):
    op: Token
    operand: Expr

    def __post_init__(self):
        self.expr_type = None


@dataclass
class CallExpr(Expr):
    callee: Expr
    args: List[Expr]

    def __post_init__(self):
        self.expr_type = None


@dataclass
class ArrayIndexExpr(Expr):
    array: Expr
    index: Expr

    def __post_init__(self):
        self.expr_type = None


@dataclass
class RecordAccessExpr(Expr):
    record: Expr
    field: str  # identifier
    token: Token

    def __post_init__(self):
        self.expr_type = None


@dataclass
class ArrayConstructorExpr(Expr):
    elements: List[Expr]

    def __post_init__(self):
        self.expr_type = None


@dataclass
class RecordConstructorExpr(Expr):
    type_name: str  # record type identifier
    field_values: dict  # field_name -> Expr

    def __post_init__(self):
        self.expr_type = None


@dataclass
class ParenExpr(Expr):
    expr: Expr

    def __post_init__(self):
        self.expr_type = None


@dataclass
class TernaryExpr(Expr):
    condition: Expr
    then_expr: Expr
    else_expr: Expr

    def __post_init__(self):
        self.expr_type = None


@dataclass
class ProbExpr(Expr):
    """Probabilistic expression: prob identifier ~ distribution"""
    identifier: str
    distribution: Expr  # distribution expression

    def __post_init__(self):
        self.expr_type = None


@dataclass
class SampleExpr(Expr):
    """Sample from distribution: sample(expr)"""
    distribution_expr: Expr

    def __post_init__(self):
        self.expr_type = None


# Statements
@dataclass
class Stmt(ASTNode):
    pass


@dataclass
class VarDeclStmt(Stmt):
    name: str
    type_name: Optional[str]  # None means inferred
    init_expr: Optional[Expr]
    token: Token  # var token

    def __post_init__(self):
        self.declared_type = None  # To be resolved


@dataclass
class ConstDeclStmt(Stmt):
    name: str
    type_name: str
    init_expr: Expr

    def __post_init__(self):
        self.declared_type = None


@dataclass
class TypeDeclStmt(Stmt):
    name: str
    type_def: 'TypeDef'  # Forward reference

    def __post_init__(self):
        pass


@dataclass
class AssignmentStmt(Stmt):
    target: Union[IdentifierExpr, ArrayIndexExpr, RecordAccessExpr]
    value: Expr

    def __post_init__(self):
        pass


@dataclass
class ProcCallStmt(Stmt):
    callee: Expr
    args: List[Expr]

    def __post_init__(self):
        pass


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]

    def __post_init__(self):
        pass


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Stmt

    def __post_init__(self):
        pass


@dataclass
class ForStmt(Stmt):
    iterator: str
    start: Expr
    end: Expr
    step: Optional[Expr]
    body: Stmt
    direction: str  # 'to' or 'downto'

    def __post_init__(self):
        pass


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]  # None for procedures

    def __post_init__(self):
        pass


@dataclass
class BlockStmt(Stmt):
    statements: List[Stmt]

    def __post_init__(self):
        pass


@dataclass
class ExprStmt(Stmt):
    expr: Expr

    def __post_init__(self):
        pass


@dataclass
class SkipStmt(Stmt):
    pass


@dataclass
class AssertStmt(Stmt):
    condition: Expr

    def __post_init__(self):
        pass


@dataclass
class ProbBlockStmt(Stmt):
    """prob block: prob declarations and observations"""
    statements: List[Stmt]

    def __post_init__(self):
        pass


@dataclass
class CausalBlockStmt(Stmt):
    """causal block for causal inference"""
    statements: List[Stmt]

    def __post_init__(self):
        pass


@dataclass
class VerifyBlockStmt(Stmt):
    """verify block for formal verification"""
    condition: Expr
    message: Optional[str]

    def __post_init__(self):
        pass


# Procedure/Function declaration
@dataclass
class ProcDeclStmt(Stmt):
    name: str
    params: List['Param']  # List of Parameter objects
    return_type: Optional[str]  # None means void/procedure
    body: Union[BlockStmt, Expr]  # Expression form or block form

    def __post_init__(self):
        pass


@dataclass
class Param:
    name: str
    type_name: str
    is_ref: bool = False

    def __post_init__(self):
        pass


# Types
@dataclass
class TypeDef:
    """Type definition for records, arrays, etc."""
    pass


@dataclass
class RecordTypeDef(TypeDef):
    fields: List['FieldDef']


@dataclass
class FieldDef:
    name: str
    type_name: str


@dataclass
class ArrayTypeDef(TypeDef):
    size: Optional[Expr]  # None means dynamic (future)
    element_type: str


@dataclass
class ProcTypeDef(TypeDef):
    params: List[Param]
    return_type: Optional[str]


# Program
@dataclass
class Program(ASTNode):
    declarations: List[Stmt]  # Top-level declarations (type, var, const, proc)
    statements: List[Stmt]    # Top-level statements (usually a block)

    def __post_init__(self):
        pass


# Import Token for type annotations in AST nodes
from src.lexer import Token, TokenType

# To resolve forward reference for TypeDef in ProcDeclStmt
ProcDeclStmt.__annotations__['body'] = "Union['BlockStmt', 'Expr']"
