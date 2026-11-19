"""Assertion-based runtime probes for the model checker APIs (CI gate 4).

Plain asserts, no pytest. Exits nonzero on any failed probe.
Run: python3 src/model_checker_probes.py  (from algol26-interpreter/)
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.algol_ast import ModelDeclStmt
from src.lexer import Lexer
from src.parser import Parser
from src.model_checker import check_model, explore_model, prove_model_unbounded


def parse_model(source: str) -> ModelDeclStmt:
    prog = Parser(Lexer(source)).parse()
    for decl in prog.declarations:
        if isinstance(decl, ModelDeclStmt):
            return decl
    raise AssertionError("no model declaration parsed")


UPCOUNTER = """
model UpCounter {
    state count: INTEGER := 0;
    trans inc: count := count + 1;
    invariant count >= 0;
}
"""
COUNTER = """
model Counter {
    state count: INTEGER := 0;
    trans inc: count := count + 1;
    trans dec: count := count - 1;
    invariant count >= 0;
}
"""
DOWNCOUNTER = """
model DownCounter {
    state count: INTEGER := 0;
    trans dec: count := count - 1;
    invariant count >= 0;
}
"""


def probe_bounded_proven():
    m = parse_model(UPCOUNTER)
    r = check_model(m, bound=6)
    assert r.proven == ["(count >= 0)"], r.proven
    assert r.refuted == [] and r.unknown == []
    assert r.states_explored == 7, r.states_explored      # 0..6
    assert r.transitions_applied == 6, r.transitions_applied


def probe_bounded_refuted_trace():
    m = parse_model(COUNTER)
    r = check_model(m, bound=5)
    assert r.refuted == ["(count >= 0)"], r.refuted
    cex = r.counterexamples["(count >= 0)"]
    assert cex["state"]["count"] == -1, cex
    trace = cex["trace"]
    assert trace[0][0] is None and trace[-1][0] == "dec", trace
    # BFS dedupes by value: states {0,1,-1,2}, budget stops mid-frontier.
    assert r.states_explored == 4, r.states_explored
    assert r.transitions_applied == 5, r.transitions_applied


def probe_properties():
    m = parse_model(UPCOUNTER)
    prop_model = parse_model("""
model P {
    state count: INTEGER := 0;
    trans inc: count := count + 1;
    invariant count <= 6;
}
""")
    prop = prop_model.invariants[0].condition
    r = check_model(m, bound=6, properties=[prop])
    assert "(count <= 6)" in r.proven, r.proven
    r2 = check_model(m, bound=8, properties=[prop])
    assert "(count <= 6)" in r2.refuted, r2.refuted


def probe_unbounded_proven():
    m = parse_model(UPCOUNTER)
    ur = prove_model_unbounded(m)
    assert ur.proven == ["(count >= 0)"], ur.proven
    assert ur.fallback is None and not ur.refuted


def probe_unbounded_fallback_refuted():
    m = parse_model(DOWNCOUNTER)
    ur = prove_model_unbounded(m, fallback_bound=5)
    assert ur.proven == [] and ur.fallback is not None
    assert "(count >= 0)" in ur.fallback.refuted
    assert "not 1-inductive" in ur.note, ur.note


def main():
    probes = [v for k, v in sorted(globals().items()) if k.startswith("probe_")]
    for p in probes:
        p()
        print(f"PROBE OK: {p.__name__}")
    print(f"{len(probes)} probes passed")


if __name__ == "__main__":
    main()
