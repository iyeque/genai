"""
ALGOL 26 Abstract Syntax Tree (AST) Nodes

Represents the parsed structure of an ALGOL 26 program.
Uses Type objects from src.type_system for type annotations.
"""

from dataclasses import dataclass
from typing import List, Optional, Union, Any, Set, TypeVar, Dict

# Import type system; note: type_system imports nothing from ast, so safe.
from src.type_system import Type, PrimitiveType, ArrayType, RecordType, FunctionType, TypeName, Substitution


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
    token: Any  # Token from lexer; we keep for location and maybe literal type

    def __post_init__(self):
        # We don't set expr_type here; static type inference will determine type
        self.expr_type: Optional[Type] = None


@dataclass
class IdentifierExpr(Expr):
    name: str
    token: Any

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class BinaryOpExpr(Expr):
    left: Expr
    op: Any  # Token
    right: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class UnaryOpExpr(Expr):
    op: Any
    operand: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class CallExpr(Expr):
    callee: Expr
    args: List[Expr]

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class ArrayIndexExpr(Expr):
    array: Expr
    index: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class RecordAccessExpr(Expr):
    record: Expr
    field: str
    token: Any

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class ArrayConstructorExpr(Expr):
    elements: List[Expr]

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class RecordConstructorExpr(Expr):
    type_name: str  # record type identifier (name)
    field_values: Dict[str, Expr]  # field_name -> Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class ParenExpr(Expr):
    expr: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class TernaryExpr(Expr):
    condition: Expr
    then_expr: Expr
    else_expr: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class ProbExpr(Expr):
    identifier: str
    distribution: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class SampleExpr(Expr):
    distribution_expr: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class ProbBlockExpr(Expr):
    """Expression form of a probabilistic block: prob { ... }"""
    statements: List['Stmt']

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class GivenExpr(Expr):
    """Conditional distribution: dist given (condition)"""
    dist: Expr
    condition: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class QuantifierExpr(Expr):
    """Quantified formula: forall/exists <var>: <type>. <body>

    Used in verification clauses (Phase 5.1c). `kind` is 'forall' or 'exists';
    `var_name` is the bound variable; `var_type` is its type name (e.g. 'int');
    `body` is the (implicitly universally-scoped) matrix the quantifier binds.
    """
    kind: str            # 'forall' | 'exists'
    var_name: str
    var_type: str
    body: Expr

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


@dataclass
class KernelLaunchExpr(Expr):
    """launch(kernel, device_array) -> device_array (Phase 5.2).

    Applies a @kernel proc elementwise over a device array on the active
    backend. The CPU reference backend maps the kernel body across elements;
    a future GPU backend would schedule the same graph on device.
    """
    kernel: Expr          # identifier naming the kernel proc
    input: Expr           # device array to map over

    def __post_init__(self):
        self.expr_type: Optional[Type] = None


# Statements
@dataclass
class Stmt(ASTNode):
    pass


@dataclass
class VarDeclStmt(Stmt):
    name: str
    type_annot: Optional[Type]  # None means inferred
    init_expr: Optional[Expr]
    token: Any

    def __post_init__(self):
        self.declared_type: Optional[Type] = None  # will hold inferred/checked type


@dataclass
class ConstDeclStmt(Stmt):
    name: str
    type_annot: Type
    init_expr: Expr

    def __post_init__(self):
        self.declared_type: Optional[Type] = None


@dataclass
class TypeDeclStmt(Stmt):
    name: str
    type_annot: Type  # The type that this name aliases or defines

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
    invariants: List['SpecClause'] = None

    def __post_init__(self):
        if self.invariants is None:
            self.invariants = []


@dataclass
class ForStmt(Stmt):
    iterator: str
    start: Expr
    end: Expr
    step: Optional[Expr]
    body: Stmt
    direction: str
    invariants: List['SpecClause'] = None

    def __post_init__(self):
        if self.invariants is None:
            self.invariants = []


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]

    def __post_init__(self):
        pass


@dataclass
class BlockStmt(Stmt):
    statements: List['Stmt']

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
    statements: List['Stmt']

    def __post_init__(self):
        pass


@dataclass
class CausalBlockStmt(Stmt):
    statements: List['Stmt']

    def __post_init__(self):
        pass


@dataclass
class VerifyBlockStmt(Stmt):
    condition: Expr
    message: Optional[str]

    def __post_init__(self):
        pass


@dataclass
class AlwaysStmt(Stmt):
    """Temporal assertion: always { P } — P is an invariant that holds
    universally (Phase 5.1). Statically discharged with Z3 like a verify block;
    without a state-transition model the checkable meaning is validity of P.
    """
    condition: Expr
    message: Optional[str] = None

    def __post_init__(self):
        pass


@dataclass
class LemmaDeclStmt(Stmt):
    """A named lemma: lemma <name>: <fact> ; (Phase 5.1 proof automation).

    States a fact (typically a quantified formula) that is proven once and can
    be reused as an assumption via `assume <name>;` in later obligations —
    proof reuse across a module. The interpreter registers the lemma and, under
    --smt, proves it and records its translated Z3 term for assumption lookup.
    """
    name: str
    condition: Expr

    def __post_init__(self):
        pass


@dataclass
class AssumeStmt(Stmt):
    """assume <name> ; — cite a registered lemma as an assumption (Phase 5.1).

    Under --smt, adds the named lemma's translated fact to the assumption set
    for subsequent obligations in the same scope (proof reuse). At runtime it is
    a no-op. An unknown lemma name is an error under --smt.
    """
    name: str

    def __post_init__(self):
        pass


@dataclass
class ProbBindStmt(Stmt):
    """Inside a prob block: binds an identifier to a distribution."""
    identifier: str
    distribution: Expr

    def __post_init__(self):
        pass


@dataclass
class ImportStmt(Stmt):
    module_name: str
    alias: Optional[str] = None
    names: Optional[List[str]] = None
    token: Any = None

    def __post_init__(self):
        pass


@dataclass
class ExportStmt(Stmt):
    names: List[str]
    token: Any = None

    def __post_init__(self):
        pass



@dataclass
class ModuleDeclStmt(Stmt):
    name: str
    token: Any = None

    def __post_init__(self):
        pass

# Procedure/Function declaration
@dataclass
class ProcDeclStmt(Stmt):
    name: str
    params: List['Param']
    return_type: Optional[Type]  # None means void
    body: Union['BlockStmt', Expr]
    preconditions: List['SpecClause'] = None   # requires ...
    postconditions: List['SpecClause'] = None  # ensures ... (may use `result`)
    attributes: List['Attribute'] = None       # @kernel(...), @vectorize(...) (Phase 5.2)

    def __post_init__(self):
        if self.preconditions is None:
            self.preconditions = []
        if self.postconditions is None:
            self.postconditions = []
        if self.attributes is None:
            self.attributes = []


@dataclass
class Attribute:
    """A proc attribute: @name(args). E.g. @kernel(gpu), @vectorize(width: 8).

    Phase 5.2 hardware-acceleration surface. `name` is the attribute identifier
    (without '@'); `args` is a list of raw string arguments (e.g. ['gpu'] or
    ['width: 8'] parsed lazily by the backend).
    """
    name: str
    args: List[str]

    def __post_init__(self):
        if self.args is None:
            self.args = []


@dataclass
class SpecClause:
    """A requires/ensures/invariant specification clause with an optional message."""
    condition: Expr
    message: Optional[str] = None


@dataclass
class Param:
    name: str
    type_annot: Type
    is_ref: bool = False

    def __post_init__(self):
        pass


# No separate TypeDef nodes; type annotations are directly Type objects.

# Program
@dataclass
class Program(ASTNode):
    declarations: List['Stmt']
    statements: List['Stmt']

    def __post_init__(self):
        pass


# Import token types for parser reference
from src.lexer import Token, TokenType

# Forward reference resolution for ProcDeclStmt body type (already fine)
ProcDeclStmt.__annotations__['body'] = "Union['BlockStmt', 'Expr']"

# ==================== Phase 4: Concurrency and Meta-Cognition ====================

@dataclass
class ChanDeclStmt(Stmt):
    """Channel declaration: `chan c: type [capacity];`"""
    name: str
    chan_type: Type
    capacity: Optional[int] = None

@dataclass
class SendStmt(Stmt):
    """Send statement: `c <- value;`"""
    channel: Expr
    value: Expr

@dataclass
class ReceiveExpr(Expr):
    """Receive expression: `<- c`"""
    channel: Expr

@dataclass
class Case:
    """A case in select: case c => stmt (receive) or case c <- value => stmt (send)"""
    channel: Expr
    is_send: bool
    stmt: Stmt
    value: Optional[Expr] = None

@dataclass
class SelectStmt(Stmt):
    """Select statement: select { case ...; default => ...; }"""
    cases: List[Case]
    default_stmt: Optional[Stmt] = None

@dataclass
class AsyncProcDeclStmt(Stmt):
    """Asynchronous procedure: async proc foo(): int { ... }"""
    name: str
    params: List[Param]
    body: Union['BlockStmt', 'Expr']
    return_type: Optional[Type] = None

@dataclass(frozen=True)
class TaskType(Type):
    """Type of an async task: task<T>"""
    result_type: Type

    def substitute(self, subst: Substitution) -> Type:
        return TaskType(self.result_type.substitute(subst))

    def free_vars(self) -> Set[TypeVar]:
        return self.result_type.free_vars()

    def __str__(self):
        return f"task<{self.result_type}>"

    def __repr__(self):
        return f"TaskType({self.result_type})"

    def __hash__(self):
        return hash(('task', self.result_type))
