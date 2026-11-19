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

Public API
----------
explore_model(model: ModelDeclStmt, bound: int)
    -> (Dict[state_id, State], transitions_applied: int)
check_model(model: ModelDeclStmt, bound: int = 10, properties: List[Expr] = None)
    -> CheckResult

CheckResult fields:
    proven / refuted / unknown: List[str]  -- obligation labels
    counterexamples: Dict[label, {'state': values, 'trace': [(trans, values)...]}]
    states_explored / transitions_applied / max_bound: int
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
