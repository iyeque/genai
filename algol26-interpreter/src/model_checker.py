"""
ALGOL 26 Model Checker (Phase 5.1 model checking).

Bounded explicit-state model checking for state-transition models:

    model Name {
        state  x: INTEGER := 0;          -- initial state
        state  y: INTEGER := 10;
        trans  inc_x: x := x + 1;        -- transition body (any statement)
        trans  dec_y: y := y - 1;
        invariant x + y <= 10;           -- checked over the reachable space
    }
    check Name {
        bound: 10;                       -- transition-application budget
        property: x >= 0;                -- additional obligations
    }

Exploration is breadth-first from the single initial state (all state vars
combined), applying each transition body with the real interpreter and
deduplicating states by their variable values, until the transition budget
(`bound`) is exhausted. Invariants and check-properties are then evaluated
over every reachable state; a refutation carries the violating state plus
the transition trace that reaches it.

This is dynamic (runtime) analysis — it evaluates concrete states with the
interpreter and does NOT require z3.

Unbounded model checking (Phase 5.1 generalised)
------------------------------------------------
`check Name { unbounded; ... }` (--smt only) proves obligations for ALL
reachable states by 1-induction via Z3:

    base:  Init(s) ==> I(s)             for each obligation I
    step:  I(s) /\\ T(s, s') ==> I(s')   for each transition T, obligation I

(all obligations are assumed in the step pre-state — sound for their
conjunction). Transition bodies are symbolically executed over the subset
{assignment, block, if/else, skip}; anything else defers honestly. A refuted
BASE is a genuine initial-state violation. A refuted/unknown STEP means the
obligations are not 1-inductive — the bounded explorer then runs as fallback
(real counterexample, or UNKNOWN for the unbounded claim).

Public API
----------
explore_model(model: ModelDeclStmt, bound: int)
    -> (Dict[state_id, State], transitions_applied: int)
check_model(model: ModelDeclStmt, bound: int = 10, properties: List[Expr] = None)
    -> CheckResult
prove_model_unbounded(model: ModelDeclStmt, properties: List[Expr] = None,
                      fallback_bound: int = 10)
    -> UnboundedCheckResult

CheckResult fields:
    proven / refuted / unknown: List[str]  -- obligation labels
    counterexamples: Dict[label, {'state': values, 'trace': [(trans, values)...]}]
    states_explored / transitions_applied / max_bound: int

UnboundedCheckResult fields:
    proven / refuted / unknown: List[str]  -- obligation labels
    counterexamples: Dict[label, {'state': values, 'trace': [...]}]
    note: str                              -- why induction fell short
    fallback: Optional[CheckResult]        -- bounded result when it did
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import deque

from src.algol_ast import (
    ModelDeclStmt, Expr,
    LiteralExpr, IdentifierExpr, BinaryOpExpr, UnaryOpExpr,
)
from src.interpreter import Interpreter, Environment


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    proven: List[str] = field(default_factory=list)
    refuted: List[str] = field(default_factory=list)
    unknown: List[str] = field(default_factory=list)
    counterexamples: Dict[str, Any] = field(default_factory=dict)
    states_explored: int = 0
    transitions_applied: int = 0
    max_bound: int = 0


# ---------------------------------------------------------------------------
# State representation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class State:
    """A reachable state: current values of the model's state vars, plus the
    parent link and transition name that produced it (for counterexample
    traces)."""

    id: str
    values: Dict[str, Any] = field(default_factory=dict)
    parent: Optional['State'] = None
    transition: Optional[str] = None

    def value_key(self) -> Tuple:
        return tuple(sorted(self.values.items()))


def _trace_to(state: State) -> List[Tuple[Optional[str], Dict[str, Any]]]:
    """Transition trace from the initial state to `state` (inclusive)."""
    path = []
    cur: Optional[State] = state
    while cur is not None:
        path.append((cur.transition, dict(cur.values)))
        cur = cur.parent
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# Expression rendering (human-readable obligation labels)
# ---------------------------------------------------------------------------

def expr_to_source(expr: Expr) -> str:
    if isinstance(expr, LiteralExpr):
        return str(expr.value)
    if isinstance(expr, IdentifierExpr):
        return expr.name
    if isinstance(expr, BinaryOpExpr):
        return f"({expr_to_source(expr.left)} {expr.op.value} {expr_to_source(expr.right)})"
    if isinstance(expr, UnaryOpExpr):
        return f"({expr.op.value}{expr_to_source(expr.operand)})"
    return str(expr)


# ---------------------------------------------------------------------------
# State-space exploration (BFS)
# ---------------------------------------------------------------------------

def explore_model(model: ModelDeclStmt, bound: int) -> Tuple[Dict[str, State], int]:
    """
    Explore the state space of `model` with a budget of `bound` transition
    applications, breadth-first from the initial state. States are
    deduplicated by their variable values.

    Returns (dict mapping state-id -> State, transitions applied).
    """
    # Build ONE initial state holding ALL state vars.
    interp = Interpreter()
    env = Environment()
    interp.current_env = env
    for var in model.state_vars:
        if var.init_expr is not None:
            val = interp.eval(var.init_expr)
        else:
            val = 0  # default initial value
        env.define(var.name, val)
    initial = State(id=f"{model.name}_s0", values=dict(env.vars))

    discovered: Dict[Tuple, State] = {initial.value_key(): initial}
    frontier = deque([initial])
    transitions_applied = 0
    counter = 0

    while frontier and transitions_applied < bound:
        state = frontier.popleft()
        for trans in model.transitions:
            if transitions_applied >= bound:
                break
            # Fresh environment + interpreter per transition application.
            env = Environment()
            for name, val in state.values.items():
                env.define(name, val)
            interp = Interpreter()
            interp.current_env = env

            try:
                interp.eval(trans.body)
            except Exception:
                # A transition that raises (e.g. failed assertion) is not a
                # valid step from this state.
                continue
            transitions_applied += 1

            new_values = dict(env.vars)
            key = tuple(sorted(new_values.items()))
            if key in discovered:
                continue
            counter += 1
            new_state = State(
                id=f"{model.name}_s{counter}",
                values=new_values,
                parent=state,
                transition=trans.name,
            )
            discovered[key] = new_state
            frontier.append(new_state)

    return {s.id: s for s in discovered.values()}, transitions_applied


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def check_model(model: ModelDeclStmt, bound: int = 10,
                properties: Optional[List[Expr]] = None) -> CheckResult:
    """
    Bounded model checking of `model`: explore up to `bound` transition
    applications, then evaluate every invariant (and any extra `properties`
    from a `check` statement) over all reachable states.
    """
    result = CheckResult(max_bound=bound)

    states, transitions_applied = explore_model(model, bound)
    result.states_explored = len(states)
    result.transitions_applied = transitions_applied

    def eval_over_states(expr: Expr) -> Tuple[bool, Optional[State]]:
        """(holds in every state, first violating state or None)."""
        for s in states.values():
            env = Environment()
            for name, val in s.values.items():
                env.define(name, val)
            interp = Interpreter()
            interp.current_env = env
            try:
                holds = interp.eval(expr)
            except Exception:
                return False, s
            if not holds:
                return False, s
        return True, None

    obligations: List[Tuple[str, Expr]] = [
        (expr_to_source(inv.condition), inv.condition) for inv in model.invariants
    ]
    if properties:
        obligations.extend((expr_to_source(p), p) for p in properties)

    for label, expr in obligations:
        ok, cex = eval_over_states(expr)
        if ok:
            result.proven.append(label)
        else:
            result.refuted.append(label)
            if cex is not None:
                result.counterexamples[label] = {
                    'state': dict(cex.values),
                    'trace': _trace_to(cex),
                }

    return result


# ---------------------------------------------------------------------------
# Unbounded model checking (1-induction via Z3)
# ---------------------------------------------------------------------------

@dataclass
class UnboundedCheckResult:
    """Outcome of an unbounded (induction) check.

    proven: obligations shown to hold in ALL reachable states (base + step).
    refuted: genuine initial-state violations (base refuted), with the
             initial state as counterexample.
    unknown: obligations left open by induction itself.
    note:    why induction fell short (step refuted/unknown, untranslatable).
    fallback: bounded CheckResult when induction fell short — its refutations
              are real counterexamples; its 'proven' labels only hold within
              the bound, so the unbounded claim stays UNKNOWN for them.
    """
    proven: List[str] = field(default_factory=list)
    refuted: List[str] = field(default_factory=list)
    unknown: List[str] = field(default_factory=list)
    counterexamples: Dict[str, Any] = field(default_factory=dict)
    note: str = ""
    fallback: Optional[CheckResult] = None


def _state_sort(var):
    """z3 sort for a model state variable from its type annotation."""
    import z3
    from src.type_system import PrimitiveType
    t = var.type_annot
    if isinstance(t, PrimitiveType):
        if t.name in ("real", "float"):
            return z3.RealSort()
        if t.name == "bool":
            return z3.BoolSort()
    return z3.IntSort()


def _z3_to_py(v):
    """Render a z3 counterexample value as a plain Python value."""
    import z3
    if v is None:
        return None
    if z3.is_int_value(v):
        return v.as_long()
    if z3.is_rational_value(v):
        return float(v.as_fraction())
    if z3.is_true(v):
        return True
    if z3.is_false(v):
        return False
    return str(v)


def _symbolic_exec(stmt, tr, sym, pre):
    """Symbolically execute a transition body over the model's state vars.

    `sym` maps var name -> current z3 term (initially the pre-state constants
    themselves); `pre` maps var name -> its pre-state constant. Returns a NEW
    map for the post-state. Supports assignments to state vars, blocks
    (sequential), if/else (per-var ITE merge) and skip; anything else raises
    SmtUnsupported so the caller defers to the bounded explorer honestly.
    """
    import z3
    from src.algol_ast import (
        AssignmentStmt, BlockStmt, IfStmt, SkipStmt, IdentifierExpr,
    )
    from src.smt import SmtUnsupported

    def subst(term):
        pairs = [(pre[n], sym[n]) for n in sym if pre[n] is not sym[n]]
        return z3.substitute(term, *pairs) if pairs else term

    if isinstance(stmt, AssignmentStmt):
        if not isinstance(stmt.target, IdentifierExpr) or stmt.target.name not in sym:
            raise SmtUnsupported("assignment target is not a model state variable")
        out = dict(sym)
        out[stmt.target.name] = subst(tr.translate(stmt.value))
        return out
    if isinstance(stmt, BlockStmt):
        cur = dict(sym)
        for s in stmt.statements:
            cur = _symbolic_exec(s, tr, cur, pre)
        return cur
    if isinstance(stmt, IfStmt):
        cond = subst(tr.translate(stmt.condition))
        then_sym = _symbolic_exec(stmt.then_branch, tr, dict(sym), pre)
        else_sym = (_symbolic_exec(stmt.else_branch, tr, dict(sym), pre)
                    if stmt.else_branch is not None else dict(sym))
        return {n: z3.If(cond, then_sym[n], else_sym[n]) for n in sym}
    if isinstance(stmt, SkipStmt):
        return dict(sym)
    raise SmtUnsupported(f"{type(stmt).__name__} not symbolically executable")


def prove_model_unbounded(model: ModelDeclStmt,
                          properties: Optional[List[Expr]] = None,
                          fallback_bound: int = 10) -> UnboundedCheckResult:
    """Unbounded model checking by 1-induction over Z3 (requires z3).

    Discharges, for the obligation conjunction (model invariants + check
    properties):
      base:  Init(s) ==> I(s)            for each obligation I
      step:  I(s) /\\ T(s, s') ==> I(s')  for each transition T, obligation I
    where T is the symbolically-executed transition body relating pre-state
    constants to post-state constants. All obligations are assumed in the
    step pre-state (sound for the conjunction).

    A refuted BASE is a genuine violation (the initial state). A refuted or
    unknown STEP, or a transition body outside the symbolic subset, means
    induction falls short: the bounded explorer runs as `fallback` and `note`
    records the gap. Nothing is silently passed.
    """
    import z3
    from src.smt import SmtTranslator, SmtUnsupported, prove

    labels = [expr_to_source(inv.condition) for inv in model.invariants]
    exprs: List[Expr] = [inv.condition for inv in model.invariants]
    if properties:
        labels.extend(expr_to_source(p) for p in properties)
        exprs.extend(properties)

    result = UnboundedCheckResult()
    if not exprs:
        return result  # no obligations

    def _fallback(note):
        result.note = note
        result.fallback = check_model(model, bound=fallback_bound,
                                      properties=properties)
        return result

    names = [v.name for v in model.state_vars]
    tr_pre = SmtTranslator()
    tr_post = SmtTranslator()
    pre = {v.name: tr_pre.declare(v.name, _state_sort(v)) for v in model.state_vars}
    # Post-state: primed z3 constants bound UNDER THE STATE-VAR NAME in the
    # post translator. (declare() registers under the name passed, so
    # declaring "count'" would leave "count" unknown -> the translator's
    # fallback re-declares z3.Const("count"), which z3 interns to the SAME
    # term as the pre constant — collapsing post onto pre and making every
    # step proof vacuously valid.)
    post = {}
    for v in model.state_vars:
        c = z3.Const(v.name + "'", _state_sort(v))
        tr_post.vars[v.name] = c
        post[v.name] = c

    # Init constraints and obligations (pre- and post-state translations).
    try:
        init_constraints = []
        for v in model.state_vars:
            if v.init_expr is not None:
                init_term = tr_pre.translate(v.init_expr)
            else:
                sort = pre[v.name].sort()
                init_term = (z3.BoolVal(False) if sort == z3.BoolSort()
                             else z3.RealVal(0) if sort == z3.RealSort()
                             else z3.IntVal(0))
            init_constraints.append(pre[v.name] == init_term)
        obls_pre = [tr_pre.translate(e) for e in exprs]
        obls_post = [tr_post.translate(e) for e in exprs]
    except SmtUnsupported as e:
        return _fallback(f"obligation/init not translatable: {e}")

    # Transition relations: post_v == f_v(pre), one conjunction per trans.
    relations = []
    try:
        for trans in model.transitions:
            sym = _symbolic_exec(trans.body, tr_pre, dict(pre), pre)
            relations.append((trans.name, [post[n] == sym[n] for n in names]))
    except SmtUnsupported as e:
        return _fallback(f"transition not symbolically executable: {e}")

    # Base case: Init ==> each obligation. A refutation here is genuine.
    base_unknown = None
    for label, goal in zip(labels, obls_pre):
        pr = prove(init_constraints, goal, var_names=pre)
        if pr.status == "refuted":
            result.refuted.append(label)
            vals = {n: _z3_to_py(pr.counterexample.get(n)) for n in names}
            result.counterexamples[label] = {'state': vals, 'trace': [(None, vals)]}
        elif pr.status == "unknown":
            base_unknown = label
    if result.refuted:
        result.unknown = [l for l in labels if l not in result.refuted]
        result.note = "initial-state violation; induction aborted"
        return result
    if base_unknown is not None:
        return _fallback(f"base case unknown for {base_unknown}")

    # Induction step: obligations(pre) /\ T(pre, post) ==> obligation(post).
    step_gap = None
    for tname, rel in relations:
        assumes = obls_pre + rel
        for label, goal_post in zip(labels, obls_post):
            pr = prove(assumes, goal_post, var_names={**pre, **post})
            if pr.status != "proven":
                step_gap = f"step '{tname}' {pr.status} for {label}; not 1-inductive"
                break
        if step_gap:
            break

    if step_gap is None:
        result.proven = list(labels)
        return result
    return _fallback(step_gap)
