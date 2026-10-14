"""
ALGOL 26 -> Z3 SMT translation and proof-obligation discharge (Phase 5.1b).

Translates the subset of ALGOL 26 expressions that appear in specification
clauses (requires / ensures / invariant / verify) into Z3 formulas, then
discharges proof obligations of the form  assumptions ⟹ goal  by asking Z3
for a counterexample.

Only the decidable, side-effect-free fragment is supported: integer/real/bool
literals, identifiers (bound to Z3 constants), arithmetic (+ - * / % ^),
comparison (== != < <= > >=), and logical (and or not) operators, plus
parentheses. Anything else (calls, arrays, records, probabilistic constructs)
raises SmtUnsupported so the caller can fall back to runtime checking.
"""

import z3

from src.ast import (
    Expr,
    LiteralExpr, IdentifierExpr, BinaryOpExpr, UnaryOpExpr, ParenExpr,
    QuantifierExpr,
)
from src.lexer import TokenType


class SmtUnsupported(Exception):
    """Raised when an expression cannot be translated to SMT."""


# Sentinel for "no saved binding" when shadowing quantifier variables.
_MISSING = object()


# Map ALGOL 26 binary operator token types to Z3 builders.
_BIN_OPS = {
    TokenType.PLUS: lambda a, b: a + b,
    TokenType.MINUS: lambda a, b: a - b,
    TokenType.STAR: lambda a, b: a * b,
    TokenType.SLASH: lambda a, b: a / b,
    TokenType.PERCENT: lambda a, b: a % b,
    TokenType.CARET: lambda a, b: a ** b,   # z3 supports ** for ints
    TokenType.EQ: lambda a, b: a == b,
    TokenType.NEQ: lambda a, b: a != b,
    TokenType.LT: lambda a, b: a < b,
    TokenType.LTE: lambda a, b: a <= b,
    TokenType.GT: lambda a, b: a > b,
    TokenType.GTE: lambda a, b: a >= b,
    TokenType.AND: lambda a, b: z3.And(a, b),
    TokenType.OR: lambda a, b: z3.Or(a, b),
    TokenType.IMPLIES: lambda a, b: z3.Implies(a, b),
}

_UNARY_OPS = {
    TokenType.MINUS: lambda a: -a,
    TokenType.NOT: lambda a: z3.Not(a),
}


class SmtTranslator:
    """Translate ALGOL 26 spec expressions into Z3 terms."""

    def __init__(self):
        # identifier name -> z3 term (constant or previously-built expr)
        self.vars = {}
        # All bound variables introduced by quantifiers, for counterexample
        # rendering: name -> z3 term. Unlike `vars`, these are NOT unbound
        # after translation, so a refuted `forall` can show the witness.
        self.bound_vars = {}

    def declare(self, name, sort):
        """Declare a symbolic variable of the given z3 sort."""
        term = z3.Const(name, sort)
        self.vars[name] = term
        return term

    def translate(self, expr):
        """Recursively translate an ALGOL 26 Expr into a z3 term."""
        if isinstance(expr, ParenExpr):
            return self.translate(expr.expr)

        if isinstance(expr, QuantifierExpr):
            return self._translate_quantifier(expr)

        if isinstance(expr, LiteralExpr):
            return self._literal(expr)

        if isinstance(expr, IdentifierExpr):
            if expr.name in self.vars:
                return self.vars[expr.name]
            # Unknown identifier: treat as an unconstrained integer constant.
            # This keeps translation total for spec clauses that reference
            # globals we do not model; proofs involving them are then only as
            # strong as the (vacuous) constraint allows.
            return self.declare(expr.name, z3.IntSort())

        if isinstance(expr, BinaryOpExpr):
            op = expr.op.type
            if op not in _BIN_OPS:
                raise SmtUnsupported(f"binary operator {op.name} not SMT-translatable")
            left = self.translate(expr.left)
            right = self.translate(expr.right)
            return _BIN_OPS[op](left, right)

        if isinstance(expr, UnaryOpExpr):
            op = expr.op.type
            if op not in _UNARY_OPS:
                raise SmtUnsupported(f"unary operator {op.name} not SMT-translatable")
            return _UNARY_OPS[op](self.translate(expr.operand))

        raise SmtUnsupported(f"{type(expr).__name__} not SMT-translatable")

    def _translate_quantifier(self, expr):
        """Translate a forall/exists QuantifierExpr into a z3 quantifier.

        The bound variable is declared fresh (shadowing any outer binding of the
        same name) with the sort implied by its type annotation; only int/real
        are supported, everything else raises SmtUnsupported.
        """
        vt = (expr.var_type or "").lower()
        if vt in ("real", "float"):
            sort = z3.RealSort()
        elif vt in ("int", "integer"):
            sort = z3.IntSort()
        else:
            raise SmtUnsupported(f"quantifier variable type {expr.var_type!r} not SMT-translatable")

        # Declare the bound variable (a genuine z3 constant; z3.ForAll binds it).
        bound = z3.Const(expr.var_name, sort)
        # Remember it so a refuted obligation can render this witness.
        self.bound_vars[expr.var_name] = bound
        # Temporarily bind the name so the body translates the bound variable.
        saved = self.vars.get(expr.var_name, _MISSING)
        self.vars[expr.var_name] = bound
        try:
            matrix = self.translate(expr.body)
        finally:
            if saved is _MISSING:
                self.vars.pop(expr.var_name, None)
            else:
                self.vars[expr.var_name] = saved

        if expr.kind == 'forall':
            return z3.ForAll(bound, matrix)
        elif expr.kind == 'exists':
            return z3.Exists(bound, matrix)
        raise SmtUnsupported(f"unknown quantifier kind {expr.kind!r}")

    @staticmethod
    def _literal(expr):
        """Build a z3 literal from a LiteralExpr, using its token type to
        coerce the raw string value the way the interpreter does."""
        tok = expr.token
        if tok.type == TokenType.INTEGER:
            return z3.IntVal(int(tok.value))
        if tok.type == TokenType.REAL:
            return z3.RealVal(float(tok.value))
        if tok.type == TokenType.TRUE:
            return z3.BoolVal(True)
        if tok.type == TokenType.FALSE:
            return z3.BoolVal(False)
        # Fall back to the Python value if it is already typed.
        value = expr.value
        if isinstance(value, bool):
            return z3.BoolVal(value)
        if isinstance(value, int):
            return z3.IntVal(value)
        if isinstance(value, float):
            return z3.RealVal(value)
        raise SmtUnsupported(f"literal {value!r} not SMT-translatable")


def prove(assumptions, goal, var_names=None, timeout_ms=10000):
    """Try to prove  AND(assumptions) ⟹ goal.

    var_names maps identifier -> z3 term, used to render a readable
    counterexample when the obligation is refuted.
    Returns a ProofResult describing the outcome.
    """
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)

    a_terms = list(assumptions)
    if a_terms:
        solver.add(z3.And(*a_terms) if len(a_terms) > 1 else a_terms[0])
    # Counterexample to the implication: assumptions hold but goal does not.
    solver.add(z3.Not(goal))

    res = solver.check()
    if res == z3.unsat:
        return ProofResult(True, "proven", None, None)
    if res == z3.sat:
        model = solver.model()
        cex = {}
        if var_names:
            for name, term in var_names.items():
                try:
                    cex[name] = model.eval(term, model_completion=True)
                except Exception:
                    pass
        return ProofResult(False, "refuted", model, cex)
    return ProofResult(False, "unknown", None, None)


class ProofResult:
    def __init__(self, proven, status, model, counterexample=None):
        self.proven = proven
        self.status = status      # "proven" | "refuted" | "unknown"
        self.model = model        # z3 model when refuted
        self.counterexample = counterexample or {}  # name -> z3 value

    def __repr__(self):
        return f"ProofResult(proven={self.proven}, status={self.status!r})"


def _sort_for(param):
    """Pick a z3 sort for a proc parameter from its ALGOL 26 type annotation."""
    from src.type_system import PrimitiveType
    t = param.type_annot
    if isinstance(t, PrimitiveType):
        name = getattr(t, "name", None)
        if name in ("real", "float"):
            return z3.RealSort()
        return z3.IntSort()
    return z3.IntSort()


def verify_proc_contracts(decl):
    """Statically verify a proc's post conditions against its preconditions.

    For an expression-bodied proc (body is a single Expr), the return value is
    modelled as  result := translate(body), giving a sound proof obligation
      (AND of requires) ⟹ (each ensures with result substituted).
    For block bodies (assignments/loops), full effect modelling is out of
    scope for 5.1b, so postconditions are left to runtime checking.

    Returns a list of (clause_kind, ProofResult-or-None, note) tuples.
    """
    from src.ast import Expr

    results = []
    tr = SmtTranslator()
    for p in decl.params:
        tr.declare(p.name, _sort_for(p))

    # Preconditions become assumptions.
    assumes = []
    ok = True
    for c in decl.preconditions:
        try:
            assumes.append(tr.translate(c.condition))
        except SmtUnsupported as e:
            results.append(("requires", None, f"not translatable: {e}"))
            ok = False
    if decl.preconditions and ok:
        results.append(("requires", None, "assumed"))

    # Model the return value from an expression body, if we have one.
    body_is_expr = isinstance(decl.body, Expr)
    result_term = None
    if body_is_expr:
        try:
            result_term = tr.translate(decl.body)
            tr.vars["result"] = result_term
        except SmtUnsupported as e:
            results.append(("ensures", None, f"body not translatable: {e}"))
            return results

    # Postconditions become goals to discharge.
    for c in decl.postconditions:
        if not body_is_expr:
            results.append(("ensures", None, "block body: deferred to runtime check"))
            continue
        try:
            goal = tr.translate(c.condition)
        except SmtUnsupported as e:
            results.append(("ensures", None, f"not translatable: {e}"))
            continue
        pr = prove(assumes, goal, var_names=tr.vars)
        results.append(("ensures", pr, c.message))
    return results
