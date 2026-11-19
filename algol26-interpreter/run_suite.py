#!/usr/bin/env python3
"""ALGOL 26 integration suite runner — the CI verification gate.

No pytest: every test is a real .algol26 program run through main.py.

Gates:
  1. --smt mode: EVERY test must pass (the verification truth).
  2. Normal mode: every test must pass EXCEPT the documented
     verification-only constructs (bare quantifiers, lemma facts with
     quantifiers, unbounded model checks) which error by design without
     --smt. The expected-failure set is matched EXACTLY: an expected
     failure that starts passing means a verification construct was
     weakened into a runtime no-op — also a gate failure.
  3. --verify exit-code contracts: refutations hard-fail (exit != 0);
     proven and unknown-defer cases exit 0.
  4. src/model_checker_test.py runtime probes exit 0.

Run:  python3 run_suite.py   (from anywhere; paths resolve to this dir)
Exit 0 iff every gate holds.
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Verification-only constructs: NO runtime meaning without --smt, so they
# error in normal mode by design (see skill: never "fix" these into no-ops).
EXPECTED_NORMAL_FAILURES = {
    "tests/lemma_reuse.algol26",
    "tests/smt_verify_forall_proven.algol26",
    "tests/smt_verify_forall_refuted.algol26",
    "tests/model_check_unbounded_guarded.algol26",
    "tests/model_check_unbounded_proven.algol26",
    "tests/model_check_unbounded_refuted.algol26",
    "tests/model_check_unbounded_unknown.algol26",
}

# (file, extra flags, expect exit 0)
VERIFY_CONTRACTS = [
    ("tests/smt_proven.algol26", ["--smt", "--verify"], True),
    ("tests/smt_refuted.algol26", ["--smt", "--verify"], False),
    ("tests/model_check_refuted.algol26", ["--verify"], False),
    ("tests/model_check_unbounded_proven.algol26", ["--smt", "--verify"], True),
    ("tests/model_check_unbounded_refuted.algol26", ["--smt", "--verify"], False),
    ("tests/model_check_unbounded_unknown.algol26", ["--smt", "--verify"], True),
]


def run(args, timeout=180):
    p = subprocess.run([sys.executable] + args, cwd=HERE,
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def discover():
    tests = sorted(
        os.path.relpath(os.path.join(r, f), HERE)
        for r, _, fs in os.walk(os.path.join(HERE, "tests"))
        for f in fs if f.endswith(".algol26"))
    tests += sorted(os.path.relpath(p, HERE)
                    for p in glob.glob(os.path.join(HERE, "test*.algol26")))
    return tests


def main():
    failures = []
    tests = discover()

    # Gate 1: --smt — all pass.
    smt_pass = 0
    for t in tests:
        rc, out = run(["main.py", t, "--smt"])
        if rc == 0:
            smt_pass += 1
        else:
            failures.append(f"[--smt] {t} exited {rc}\n{out[-400:]}")
    print(f"--smt mode: {smt_pass}/{len(tests)} pass", flush=True)

    # Gate 2: normal — exact expected-failure match.
    normal_pass = 0
    normal_expected_fail = set()
    for t in tests:
        rc, out = run(["main.py", t])
        if rc == 0:
            normal_pass += 1
            if t in EXPECTED_NORMAL_FAILURES:
                failures.append(
                    f"[normal] {t} PASSES but is verification-only — "
                    "construct weakened into a runtime no-op?")
        else:
            if t in EXPECTED_NORMAL_FAILURES:
                normal_expected_fail.add(t)
            else:
                failures.append(f"[normal] {t} exited {rc}\n{out[-400:]}")
    for t in sorted(EXPECTED_NORMAL_FAILURES - normal_expected_fail):
        if not os.path.exists(os.path.join(HERE, t)):
            failures.append(f"[normal] expected-failure file missing: {t}")
    print(f"normal mode: {normal_pass} pass + "
          f"{len(normal_expected_fail)} expected verification-only failures",
          flush=True)

    # Gate 3: --verify exit-code contracts.
    for t, flags, expect_ok in VERIFY_CONTRACTS:
        rc, out = run(["main.py", t] + flags)
        if (rc == 0) != expect_ok:
            failures.append(
                f"[verify] {t} {' '.join(flags)}: exit {rc}, expected "
                f"{'0' if expect_ok else 'nonzero'}\n{out[-400:]}")
    print(f"--verify contracts: {len(VERIFY_CONTRACTS)} checked", flush=True)

    # Gate 4: runtime model-checker probes.
    rc, out = run(["src/model_checker_test.py"])
    if rc != 0:
        failures.append(f"[runtime] model_checker_test.py exited {rc}\n{out[-400:]}")
    print("runtime model probes: " + ("pass" if rc == 0 else "FAIL"), flush=True)

    if failures:
        print(f"\nSUITE FAILED ({len(failures)} problem(s)):")
        for f in failures:
            print(" - " + f)
        return 1
    print(f"\nSUITE OK: {len(tests)} tests | --smt {smt_pass}/{len(tests)} | "
          f"normal {normal_pass}+{len(normal_expected_fail)} expected | "
          "verify contracts + runtime probes green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
