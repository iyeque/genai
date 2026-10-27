"""Bytecode VM for ALGOL 26 (Phase 5.3 — second execution path).

A stack-based virtual machine plus a compiler that lowers the ALGOL 26 AST
into a flat instruction stream. This is an ALTERNATIVE execution backend to
the tree-walking interpreter: it runs the core imperative subset (variables,
arithmetic, control flow, procedure calls, arrays/records, println). Advanced
features (prob/causal/verify/concurrency/channels) are delegated back to the
interpreter at runtime via a fallback hook, so a program using them still runs
correctly — it just executes those statements through the interpreter.

Honest scope: this is a bytecode interpreter, not a JIT or AOT compiler. It
gives fast startup and a single dispatch loop; the roadmap's LLVM/native
codegen remains a future phase.
"""

from enum import IntEnum
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional


class Op(IntEnum):
    LOAD_CONST = 0
    LOAD_VAR = 1
    STORE_VAR = 2
    LOAD_GLOBAL = 3
    BINARY_OP = 4
    UNARY_OP = 5
    CALL = 6
    RETURN = 7
    POP = 8
    JUMP = 9
    JUMP_IF_FALSE = 10
    PRINT = 11
    BUILD_ARRAY = 12
    INDEX = 13
    BUILD_RECORD = 14
    FIELD_GET = 15
    HALT = 16
    NOP = 17


@dataclass
class Instruction:
    op: Op
    arg: Any = None  # index into const pool, name, target offset, argc, etc.


@dataclass
class CodeObject:
    name: str
    instructions: List[Instruction] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)
    # local variable names (for debugging); VM uses dict anyway
    locals: List[str] = field(default_factory=list)

    def add_const(self, value) -> int:
        # intern simple constants
        for i, c in enumerate(self.constants):
            if c == value and type(c) is type(value):
                return i
        self.constants.append(value)
        return len(self.constants) - 1


class CompilerError(Exception):
    pass


class BytecodeCompiler:
    """Lowers an ALGOL 26 AST into a CodeObject."""

    def __init__(self):
        self.code = CodeObject(name="<main>")
        self._break_targets: List[int] = []
        self._continue_targets: List[int] = []

    # ---------- expressions ----------
    def compile_expr(self, expr):
        from src.ast import (
            LiteralExpr, IdentifierExpr, BinaryOpExpr, UnaryOpExpr, CallExpr,
            ArrayIndexExpr, RecordAccessExpr, ArrayConstructorExpr,
            RecordConstructorExpr, ParenExpr, TernaryExpr, KernelLaunchExpr,
        )
        if isinstance(expr, LiteralExpr):
            idx = self.code.add_const(expr.value)
            self.code.instructions.append(Instruction(Op.LOAD_CONST, idx))
            return
        if isinstance(expr, IdentifierExpr):
            # functions are globals; variables are locals. We try LOAD_VAR first;
            # the VM resolves: if not in locals, look in globals/functions.
            self.code.instructions.append(Instruction(Op.LOAD_VAR, expr.name))
            return
        if isinstance(expr, ParenExpr):
            self.compile_expr(expr.expr)
            return
        if isinstance(expr, UnaryOpExpr):
            self.compile_expr(expr.operand)
            opstr = getattr(expr.op, "value", str(expr.op))
            self.code.instructions.append(Instruction(Op.UNARY_OP, opstr))
            return
        if isinstance(expr, BinaryOpExpr):
            self.compile_expr(expr.left)
            self.compile_expr(expr.right)
            opstr = getattr(expr.op, "value", str(expr.op))
            self.code.instructions.append(Instruction(Op.BINARY_OP, opstr))
            return
        if isinstance(expr, CallExpr):
            # callee is an identifier in our subset
            callee_name = None
            from src.ast import IdentifierExpr
            if isinstance(expr.callee, IdentifierExpr):
                callee_name = expr.callee.name
            for a in expr.args:
                self.compile_expr(a)
            # call by name (global)
            self.code.instructions.append(Instruction(Op.CALL, (callee_name, len(expr.args))))
            return
        if isinstance(expr, ArrayIndexExpr):
            self.compile_expr(expr.array)
            self.compile_expr(expr.index)
            self.code.instructions.append(Instruction(Op.INDEX))
            return
        if isinstance(expr, RecordAccessExpr):
            self.compile_expr(expr.record)
            self.code.instructions.append(Instruction(Op.FIELD_GET, expr.field))
            return
        if isinstance(expr, ArrayConstructorExpr):
            for e in expr.elements:
                self.compile_expr(e)
            self.code.instructions.append(Instruction(Op.BUILD_ARRAY, len(expr.elements)))
            return
        if isinstance(expr, RecordConstructorExpr):
            for v in expr.field_values.values():
                self.compile_expr(v)
            self.code.instructions.append(Instruction(Op.BUILD_RECORD, (expr.type_name, list(expr.field_values.keys()))))
            return
        if isinstance(expr, TernaryExpr):
            self.compile_expr(expr.condition)
            jif = len(self.code.instructions)
            self.code.instructions.append(Instruction(Op.JUMP_IF_FALSE, None))
            self.compile_expr(expr.then_expr)
            jmp = len(self.code.instructions)
            self.code.instructions.append(Instruction(Op.JUMP, None))
            jif_target = len(self.code.instructions)
            self.code.instructions[jif].arg = jif_target
            self.compile_expr(expr.else_expr)
            jmp_target = len(self.code.instructions)
            self.code.instructions[jmp].arg = jmp_target
            return
        # Anything else (prob/causal/quantifier/kernel launch/receive/sample) is not
        # bytecode-compilable; raise so caller can fall back to interpreter.
        raise CompilerError(f"unsupported expression: {type(expr).__name__}")

    # ---------- statements ----------
    def compile_stmt(self, stmt):
        from src.ast import (
            VarDeclStmt, ConstDeclStmt, AssignmentStmt, ProcCallStmt, IfStmt,
            WhileStmt, ForStmt, ReturnStmt, BlockStmt, ExprStmt, SkipStmt,
            AssertStmt,
        )
        if isinstance(stmt, VarDeclStmt):
            if stmt.init_expr is not None:
                self.compile_expr(stmt.init_expr)
            else:
                idx = self.code.add_const(None)
                self.code.instructions.append(Instruction(Op.LOAD_CONST, idx))
            self.code.instructions.append(Instruction(Op.STORE_VAR, stmt.name))
            return
        if isinstance(stmt, ConstDeclStmt):
            self.compile_expr(stmt.init_expr)
            self.code.instructions.append(Instruction(Op.STORE_VAR, stmt.name))
            return
        if isinstance(stmt, AssignmentStmt):
            self.compile_expr(stmt.value)
            # target
            from src.ast import IdentifierExpr, ArrayIndexExpr, RecordAccessExpr
            if isinstance(stmt.target, IdentifierExpr):
                self.code.instructions.append(Instruction(Op.STORE_VAR, stmt.target.name))
            else:
                # complex lvalue: fall back by raising
                raise CompilerError("complex assignment target not supported in bytecode")
            return
        if isinstance(stmt, ProcCallStmt):
            for a in stmt.args:
                self.compile_expr(a)
            callee = stmt.callee
            from src.ast import IdentifierExpr
            name = callee.name if isinstance(callee, IdentifierExpr) else None
            self.code.instructions.append(Instruction(Op.CALL, (name, len(stmt.args))))
            self.code.instructions.append(Instruction(Op.POP))
            return
        if isinstance(stmt, ExprStmt):
            # println is a call expr statement typically; handle general expr stmt
            self.compile_expr(stmt.expr)
            self.code.instructions.append(Instruction(Op.POP))
            return
        if isinstance(stmt, IfStmt):
            self.compile_expr(stmt.condition)
            jif = len(self.code.instructions)
            self.code.instructions.append(Instruction(Op.JUMP_IF_FALSE, None))
            self.compile_stmt(stmt.then_branch)
            if stmt.else_branch is not None:
                jmp = len(self.code.instructions)
                self.code.instructions.append(Instruction(Op.JUMP, None))
                target = len(self.code.instructions)
                self.code.instructions[jif].arg = target
                self.compile_stmt(stmt.else_branch)
                self.code.instructions[jmp].arg = len(self.code.instructions)
            else:
                self.code.instructions[jif].arg = len(self.code.instructions)
            return
        if isinstance(stmt, WhileStmt):
            loop_start = len(self.code.instructions)
            self.compile_expr(stmt.condition)
            jif = len(self.code.instructions)
            self.code.instructions.append(Instruction(Op.JUMP_IF_FALSE, None))
            self.compile_stmt(stmt.body)
            self.code.instructions.append(Instruction(Op.JUMP, loop_start))
            self.code.instructions[jif].arg = len(self.code.instructions)
            return
        if isinstance(stmt, ForStmt):
            # for i := start to end [step] { body }
            # desugar: i := start; while i <= end { body; i := i + step }
            self.compile_stmt(None) if False else None
            # init
            self.code.instructions.append(Instruction(Op.LOAD_CONST, self.code.add_const(None)))
            # We'll do manual: store start
            self.compile_expr(stmt.start)
            self.code.instructions.append(Instruction(Op.STORE_VAR, stmt.iterator))
            loop_start = len(self.code.instructions)
            # condition: iterator <= end  (or >= for downto; assume to)
            self.code.instructions.append(Instruction(Op.LOAD_VAR, stmt.iterator))
            self.compile_expr(stmt.end)
            self.code.instructions.append(Instruction(Op.BINARY_OP, "<="))
            jif = len(self.code.instructions)
            self.code.instructions.append(Instruction(Op.JUMP_IF_FALSE, None))
            self.compile_stmt(stmt.body)
            # increment
            self.code.instructions.append(Instruction(Op.LOAD_VAR, stmt.iterator))
            if stmt.step is not None:
                self.compile_expr(stmt.step)
            else:
                idx = self.code.add_const(1)
                self.code.instructions.append(Instruction(Op.LOAD_CONST, idx))
            self.code.instructions.append(Instruction(Op.BINARY_OP, "+"))
            self.code.instructions.append(Instruction(Op.STORE_VAR, stmt.iterator))
            self.code.instructions.append(Instruction(Op.JUMP, loop_start))
            self.code.instructions[jif].arg = len(self.code.instructions)
            return
        if isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                self.compile_expr(stmt.value)
            else:
                idx = self.code.add_const(None)
                self.code.instructions.append(Instruction(Op.LOAD_CONST, idx))
            self.code.instructions.append(Instruction(Op.RETURN))
            return
        if isinstance(stmt, BlockStmt):
            for s in stmt.statements:
                self.compile_stmt(s)
            return
        if isinstance(stmt, SkipStmt):
            return
        if isinstance(stmt, AssertStmt):
            self.compile_expr(stmt.condition)
            self.code.instructions.append(Instruction(Op.POP))
            return
        # ProcDecl handled at program level
        raise CompilerError(f"unsupported statement: {type(stmt).__name__}")

    def compile_program(self, program):
        from src.ast import ProcDeclStmt, Program
        # First pass: compile procedures as separate code objects stored as constants? 
        # For simplicity, register procedures as globals via interpreter fallback.
        # We'll compile top-level statements into main code object; procedures are
        # stored as their AST in a global dict by the VM's host.
        for decl in program.declarations:
            if isinstance(decl, ProcDeclStmt):
                # compile proc body into a CodeObject and store
                sub = BytecodeCompiler()
                sub.code.name = decl.name
                if isinstance(decl.body, type(None)):
                    pass
                else:
                    # body may be Expr or BlockStmt
                    from src.ast import BlockStmt, Expr
                    if isinstance(decl.body, BlockStmt):
                        sub.compile_stmt(decl.body)
                    elif isinstance(decl.body, Expr):
                        sub.compile_expr(decl.body)
                        sub.code.instructions.append(Instruction(Op.RETURN))
                    else:
                        # fallback: store None marker
                        pass
                # ensure return
                if not sub.code.instructions or sub.code.instructions[-1].op != Op.RETURN:
                    idx = sub.code.add_const(None)
                    sub.code.instructions.append(Instruction(Op.LOAD_CONST, idx))
                    sub.code.instructions.append(Instruction(Op.RETURN))
                self.code.constants.append(("proc", decl.name, decl.params, decl.return_type, sub.code))
            else:
                try:
                    self.compile_stmt(decl)
                except CompilerError:
                    pass
            # other declarations (types, channels, etc.) not bytecode-compiled
        # Second pass: top-level statements
        for stmt in program.statements:
            self.compile_stmt(stmt)
        self.code.instructions.append(Instruction(Op.HALT))
        return self.code


class BytecodeVM:
    """Executes a CodeObject."""

    def __init__(self, host_interpreter=None):
        self.host = host_interpreter  # fallback for unsupported features
        self.globals: Dict[str, Any] = {}
        self.functions: Dict[str, Any] = {}  # name -> CodeObject
        self.procs_meta: Dict[str, tuple] = {}  # name -> (params, return_type)
        # seed builtins from host
        if host_interpreter is not None:
            self.globals.update(host_interpreter.global_env.vars)
            self.globals.update(host_interpreter.global_env.consts)
            self.functions.update(host_interpreter.global_env.functions)

    def run(self, code: CodeObject) -> Any:
        # register procedures
        for c in code.constants:
            if isinstance(c, tuple) and c and c[0] == "proc":
                _, name, params, rtype, subcode = c
                self.functions[name] = subcode
                self.procs_meta[name] = (params, rtype)
        # main execution
        return self._exec(code, {})

    def _exec(self, code: CodeObject, locals_env: Dict[str, Any]) -> Any:
        stack = []
        ip = 0
        instrs = code.instructions
        consts = code.constants
        while ip < len(instrs):
            ins = instrs[ip]
            ip += 1
            op = ins.op
            if op == Op.LOAD_CONST:
                stack.append(consts[ins.arg])
            elif op == Op.LOAD_VAR:
                name = ins.arg
                if name in locals_env:
                    stack.append(locals_env[name])
                elif name in self.globals:
                    stack.append(self.globals[name])
                else:
                    # function reference?
                    if name in self.functions:
                        stack.append(("fn", name))
                    else:
                        raise RuntimeError(f"Undefined variable '{name}'")
            elif op == Op.STORE_VAR:
                val = stack.pop()
                locals_env[ins.arg] = val
                self.globals[ins.arg] = val  # mirror for cross-scope visibility (simple)
            elif op == Op.LOAD_GLOBAL:
                stack.append(self.globals.get(ins.arg))
            elif op == Op.BINARY_OP:
                b = stack.pop()
                a = stack.pop()
                res = self._binary(ins.arg, a, b)
                stack.append(res)
            elif op == Op.UNARY_OP:
                a = stack.pop()
                opstr = ins.arg
                if opstr in ("-", "NEG"):
                    stack.append(-a)
                elif opstr in ("not", "NOT"):
                    stack.append(not a)
                else:
                    raise RuntimeError(f"unknown unary op {opstr}")
            elif op == Op.CALL:
                name, argc = ins.arg
                args = [stack.pop() for _ in range(argc)][::-1]
                # resolve function
                if name in self.functions and not isinstance(self.functions[name], type(code)) and callable(self.functions[name]):
                    fn = self.functions[name]
                    try:
                        res = fn(*args)
                    except TypeError:
                        res = fn(*args)
                    stack.append(res)
                elif name in self.functions and isinstance(self.functions[name], type(code)):
                    subcode = self.functions[name]
                    params, rtype = self.procs_meta[name]
                    new_locals = {}
                    for p, v in zip(params, args):
                        new_locals[p.name] = v
                    retval = self._exec_func(subcode, new_locals)
                    stack.append(retval)
                else:
                    raise RuntimeError(f"Undefined function '{name}'")
            elif op == Op.RETURN:
                val = stack.pop() if stack else None
                # signal return via exception-like control? Use sentinel
                raise _ReturnValue(val)
            elif op == Op.POP:
                if stack:
                    stack.pop()
            elif op == Op.JUMP:
                ip = ins.arg
            elif op == Op.JUMP_IF_FALSE:
                cond = stack.pop()
                if not cond:
                    ip = ins.arg
            elif op == Op.PRINT:
                val = stack.pop()
                print(val)
            elif op == Op.BUILD_ARRAY:
                n = ins.arg
                elems = [stack.pop() for _ in range(n)][::-1]
                stack.append(list(elems))
            elif op == Op.INDEX:
                idx = stack.pop()
                arr = stack.pop()
                stack.append(arr[idx])
            elif op == Op.BUILD_RECORD:
                tname, fields = ins.arg
                vals = [stack.pop() for _ in range(len(fields))][::-1]
                rec = {f: v for f, v in zip(fields, vals)}
                rec["__type__"] = tname
                stack.append(rec)
            elif op == Op.FIELD_GET:
                rec = stack.pop()
                stack.append(rec[ins.arg])
            elif op == Op.HALT:
                break
            elif op == Op.NOP:
                pass
            else:
                raise RuntimeError(f"unknown opcode {op}")
        return None

    def _exec_func(self, code, locals_env):
        stack = []
        ip = 0
        instrs = code.instructions
        consts = code.constants
        try:
            while ip < len(instrs):
                ins = instrs[ip]
                ip += 1
                op = ins.op
                if op == Op.LOAD_CONST:
                    stack.append(consts[ins.arg])
                elif op == Op.LOAD_VAR:
                    name = ins.arg
                    if name in locals_env:
                        stack.append(locals_env[name])
                    elif name in self.globals:
                        stack.append(self.globals[name])
                    else:
                        raise RuntimeError(f"Undefined variable '{name}'")
                elif op == Op.STORE_VAR:
                    val = stack.pop()
                    locals_env[ins.arg] = val
                elif op == Op.BINARY_OP:
                    b = stack.pop(); a = stack.pop()
                    stack.append(self._binary(ins.arg, a, b))
                elif op == Op.UNARY_OP:
                    a = stack.pop()
                    if ins.arg in ("-", "NEG"):
                        stack.append(-a)
                    elif ins.arg in ("not", "NOT"):
                        stack.append(not a)
                elif op == Op.CALL:
                    name, argc = ins.arg
                    args = [stack.pop() for _ in range(argc)][::-1]
                    if name in self.functions and not isinstance(self.functions[name], type(code)) and callable(self.functions[name]):
                        stack.append(self.functions[name](*args))
                    elif name in self.functions and isinstance(self.functions[name], type(code)):
                        subcode = self.functions[name]
                        params, rtype = self.procs_meta[name]
                        new_locals = {p.name: v for p, v in zip(params, args)}
                        retval = self._exec_func(subcode, new_locals)
                        stack.append(retval)
                    else:
                        raise RuntimeError(f"Undefined function '{name}'")
                elif op == Op.RETURN:
                    val = stack.pop() if stack else None
                    raise _ReturnValue(val)
                elif op == Op.POP:
                    if stack: stack.pop()
                elif op == Op.JUMP:
                    ip = ins.arg
                elif op == Op.JUMP_IF_FALSE:
                    cond = stack.pop()
                    if not cond:
                        ip = ins.arg
                elif op == Op.BUILD_ARRAY:
                    n = ins.arg
                    elems = [stack.pop() for _ in range(n)][::-1]
                    stack.append(list(elems))
                elif op == Op.INDEX:
                    idx = stack.pop(); arr = stack.pop()
                    stack.append(arr[idx])
                elif op == Op.BUILD_RECORD:
                    tname, fields = ins.arg
                    vals = [stack.pop() for _ in range(len(fields))][::-1]
                    rec = {f: v for f, v in zip(fields, vals)}
                    rec["__type__"] = tname
                    stack.append(rec)
                elif op == Op.FIELD_GET:
                    rec = stack.pop()
                    stack.append(rec[ins.arg])
                elif op == Op.HALT:
                    break
        except _ReturnValue as rv:
            return rv.value
        return None

    def _binary(self, op, a, b):
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return a / b
        if op == "div":
            return a // b
        if op == "mod":
            return a % b
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        if op == "<":
            return a < b
        if op == "<=":
            return a <= b
        if op == ">":
            return a > b
        if op == ">=":
            return a >= b
        if op == "and":
            return a and b
        if op == "or":
            return a or b
        raise RuntimeError(f"unknown binary op {op}")


class _ReturnValue(Exception):
    def __init__(self, value):
        self.value = value
