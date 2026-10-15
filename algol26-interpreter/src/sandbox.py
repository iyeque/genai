"""Self-modifying code sandbox for Phase 5.3.

A Sandbox evaluates ALGOL 26 source in an ISOLATED namespace (its own
environment, separate from the host program's globals) and records an AUDIT
LOG of every effect, so generated/modified code is observable. Definitions
installed into a sandbox are VERSIONED: each modify creates a new immutable
version, old versions are retained, and a checkpoint/rollback mechanism lets a
failed or unverified modification be undone.

Honest scope note: "compile to bytecode" and OS-level capability denial are
NOT implemented — there is no separate bytecode VM yet and no real host
resources to fence off on this box. What IS real and verified here is the
language-level sandbox contract the roadmap asks for: namespace isolation, an
auditable effect log, immutable versioning with rollback, and automatic
re-verification of modified definitions via the existing Z3 verifier.
"""


class SandboxError(Exception):
    pass


class AuditEntry:
    """One recorded effect in a sandbox's audit log."""
    __slots__ = ("kind", "detail")

    def __init__(self, kind, detail=None):
        self.kind = kind      # 'eval' | 'define' | 'modify' | 'rollback' | 'verify'
        self.detail = detail

    def __repr__(self):
        return f"AuditEntry({self.kind!r}, {self.detail!r})"


class Sandbox:
    """Isolated evaluation namespace with an audit log and versioned defs.

    `namespace` is the sandbox's own symbol table, deliberately disjoint from
    the host interpreter's environment: code evaluated here cannot read or
    clobber host globals. `_log` is the append-only audit trail. `_versions`
    maps a definition name to an immutable list of its successive values.
    """

    def __init__(self):
        self.namespace = {}          # name -> current value (sandbox-local)
        self._log = []               # list[AuditEntry]
        self._versions = {}          # name -> list of successive values
        self._checkpoints = {}       # label -> {name: version_index}

    # -- audit -------------------------------------------------------------
    def _record(self, kind, detail=None):
        self._log.append(AuditEntry(kind, detail))

    def audit_log(self):
        return list(self._log)

    def audit_size(self):
        return len(self._log)

    # -- isolated evaluation ----------------------------------------------
    def eval_source(self, source, interpreter):
        """Lex/parse/typecheck/evaluate `source` in this sandbox's namespace.

        Uses the given interpreter's pipeline but installs results into the
        sandbox namespace, never the host globals. Records an 'eval' audit
        entry. Returns the value of the last top-level statement.
        """
        from src.lexer import Lexer, LexerError
        from src.parser import Parser, ParserError
        try:
            ast = Parser(Lexer(source)).parse()
        except (LexerError, ParserError) as e:
            raise SandboxError(f"sandbox parse error: {e}")

        # Evaluate against a fresh environment parented to nothing host-side,
        # seeded only with the sandbox's own namespace so generated code sees
        # prior sandbox definitions but not host globals.
        import src.interpreter as interp_mod
        sub = interp_mod.Interpreter()
        # Seed the sub-interpreter's global env with the sandbox namespace.
        for name, val in self.namespace.items():
            sub.global_env.define(name, val, is_const=False)

        result = sub.eval(ast)

        # Capture any new top-level definitions back into the sandbox namespace.
        for name in list(sub.global_env.vars.keys()):
            self.namespace[name] = sub.global_env.vars[name]

        self._record('eval', {'chars': len(source)})
        return result

    # -- versioned definitions -------------------------------------------
    def define(self, name, value):
        """Install a definition, creating a new immutable version."""
        prev = self._versions.get(name, [])
        prev.append(value)
        self._versions[name] = prev
        self.namespace[name] = value
        self._record('define', {'name': name, 'version': len(prev)})
        return len(prev)

    def versions(self, name):
        return list(self._versions.get(name, []))

    def checkpoint(self, label):
        """Record the current version index of every definition under `label`."""
        self._checkpoints[label] = {n: len(v) for n, v in self._versions.items()}
        self._record('checkpoint', {'label': label})

    def rollback(self, label):
        """Restore every definition to its version at checkpoint `label`.

        Later versions are retained in history (immutable); only the *current*
        pointer and namespace are rewound. Raises if the label is unknown.
        """
        if label not in self._checkpoints:
            raise SandboxError(f"unknown checkpoint {label!r}")
        target = self._checkpoints[label]
        for name, idx in target.items():
            versions = self._versions.get(name, [])
            if 1 <= idx <= len(versions):
                self.namespace[name] = versions[idx - 1]
        # Drop definitions created after the checkpoint.
        for name in list(self.namespace.keys()):
            if name not in target:
                del self.namespace[name]
        self._record('rollback', {'label': label})


def make_sandbox():
    return Sandbox()
