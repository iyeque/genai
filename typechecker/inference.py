"""
ALGOL 26 Typechecker: Hindley-Milner Type Inference

This module implements Hindley-Milner type inference with:
- Unification algorithm with occurs-check
- Type environments and substitution
- Generalization and instantiation
- Let-polymorphism support
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import Enum
import copy


class TypeKind(Enum):
    """Kinds of types in the system"""
    UNIT = "unit"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    FUN = "fun"
    VAR = "var"
    CON = "con"  # Type constructor (e.g., array, list)
    ROW = "row"  # For row polymorphism


@dataclass(frozen=True)
class Type:
    """Representation of types in the type system"""
    kind: TypeKind
    args: List[Type] = field(default_factory=list)  # Type arguments (for generics)
    var_name: Optional[str] = None  # For type variables
    row_rest: Optional[Type] = None  # For row types (rest variable)
    
    def __repr__(self) -> str:
        if self.kind == TypeKind.VAR:
            return self.var_name or "?"
        elif self.kind == TypeKind.FUN:
            if len(self.args) == 2:
                return f"({self.args[0]} -> {self.args[1]})"
            return "(->)"
        elif self.kind == TypeKind.CON:
            if self.args:
                args_str = ", ".join(map(repr, self.args))
                return f"{self.var_name}[{args_str}]"
            return self.var_name or "?"
        elif self.kind == TypeKind.ROW:
            fields = []
            for i in range(0, len(self.args), 2):
                if i + 1 < len(self.args):
                    fields.append(f"{self.args[i]}: {self.args[i+1]}")
            rest = f" | {self.row_rest}" if self.row_rest else ""
            return "{" + ", ".join(fields) + rest + "}"
        else:
            return self.kind.value
    
    def occurs(self, var: Type) -> bool:
        """Check if a type variable occurs in this type (for occurs check)"""
        if self.kind == TypeKind.VAR:
            return self == var
        elif self.kind in (TypeKind.FUN, TypeKind.CON):
            return any(arg.occurs(var) for arg in self.args)
        elif self.kind == TypeKind.ROW:
            for arg in self.args:
                if arg.occurs(var):
                    return True
            if self.row_rest and self.row_rest.occurs(var):
                return True
        return False
    
    def substitute(self, subst: Dict[Type, Type]) -> Type:
        """Apply substitution to this type"""
        if self.kind == TypeKind.VAR:
            return subst.get(self, self)
        elif self.kind in (TypeKind.FUN, TypeKind.CON):
            return Type(self.kind, [arg.substitute(subst) for arg in self.args], 
                       var_name=self.var_name)
        elif self.kind == TypeKind.ROW:
            new_args = [arg.substitute(subst) for arg in self.args]
            new_rest = self.row_rest.substitute(subst) if self.row_rest else None
            return Type(self.kind, new_args, row_rest=new_rest)
        else:
            return self


# Basic type constructors
def unit_type() -> Type:
    return Type(TypeKind.UNIT)

def int_type() -> Type:
    return Type(TypeKind.INT)

def float_type() -> Type:
    return Type(TypeKind.FLOAT)

def bool_type() -> Type:
    return Type(TypeKind.BOOL)

def string_type() -> Type:
    return Type(TypeKind.STRING)

def fun_type(arg: Type, ret: Type) -> Type:
    return Type(TypeKind.FUN, [arg, ret])

def var_type(name: str) -> Type:
    return Type(TypeKind.VAR, var_name=name)

def con_type(name: str, args: List[Type] = None) -> Type:
    if args is None:
        args = []
    return Type(TypeKind.CON, args, var_name=name)


@dataclass
class Scheme:
    """Type scheme with quantified type variables"""
    type_vars: List[str]
    type: Type
    
    def instantiate(self) -> Type:
        """Create a fresh copy with new type variables"""
        if not self.type_vars:
            return copy.deepcopy(self.type)
        
        subst = {}
        for var in self.type_vars:
            fresh = fresh_type_var()
            subst[var_type(var)] = fresh
        return self.type.substitute(subst)
    
    def __repr__(self) -> str:
        if self.type_vars:
            vars_str = ", ".join(self.type_vars)
            return f"∀{vars_str}. {self.type}"
        return repr(self.type)


class UnificationError(Exception):
    """Raised when types cannot be unified"""
    pass


def fresh_type_var() -> Type:
    """Generate a fresh type variable with unique name"""
    fresh_type_var.counter += 1
    return var_type(f"t{fresh_type_var.counter}")

fresh_type_var.counter = 0


def unify(t1: Type, t2: Type) -> Dict[Type, Type]:
    """
    Unify two types, returning the most general unifier (MGU).
    Raises UnificationError if types are not unifiable.
    """
    subst = {}
    worklist = [(t1, t2)]
    
    while worklist:
        s, t = worklist.pop()
        s = s.substitute(subst)
        t = t.substitute(subst)
        
        if s == t:
            continue
        
        if s.kind == TypeKind.VAR:
            if t.occurs(s):
                raise UnificationError(f"Occurs check failed: {s} in {t}")
            subst[s] = t
        elif t.kind == TypeKind.VAR:
            if s.occurs(t):
                raise UnificationError(f"Occurs check failed: {t} in {s}")
            subst[t] = s
        elif s.kind == TypeKind.FUN and t.kind == TypeKind.FUN:
            if len(s.args) != 2 or len(t.args) != 2:
                raise UnificationError("Function arity mismatch")
            worklist.append((s.args[0], t.args[0]))  # argument types
            worklist.append((s.args[1], t.args[1]))  # return types
        elif s.kind == t.kind and s.kind in (TypeKind.CON,):
            if s.var_name != t.var_name:
                raise UnificationError(f"Type constructor mismatch: {s.var_name} vs {t.var_name}")
            if len(s.args) != len(t.args):
                raise UnificationError(f"Arity mismatch for {s.var_name}")
            for a1, a2 in zip(s.args, t.args):
                worklist.append((a1, a2))
        else:
            raise UnificationError(f"Cannot unify {s} with {t}")
    
    return subst


def compose_subst(s1: Dict[Type, Type], s2: Dict[Type, Type]) -> Dict[Type, Type]:
    """Compose two substitutions: s1 ∘ s2"""
    result = {}
    # Apply s1 to s2's values
    for var, typ in s2.items():
        result[var] = typ.substitute(s1)
    # Add s1's bindings
    for var, typ in s1.items():
        result[var] = typ
    return result


class TypeEnv:
    """Type environment mapping identifiers to schemes"""
    
    def __init__(self, parent: Optional[TypeEnv] = None):
        self.mapping: Dict[str, Scheme] = {}
        self.parent = parent
    
    def lookup(self, name: str) -> Optional[Scheme]:
        """Look up a name in the environment"""
        if name in self.mapping:
            return self.mapping[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
    
    def extend(self, name: str, scheme: Scheme) -> TypeEnv:
        """Create a new environment extended with a binding"""
        new_env = TypeEnv(self)
        new_env.mapping[name] = scheme
        return new_env
    
    def extend_many(self, names: List[str], types: List[Type]) -> TypeEnv:
        """Extend with multiple monomorphic bindings"""
        new_env = TypeEnv(self)
        for name, typ in zip(names, types):
            new_env.mapping[name] = Scheme([], typ)
        return new_env
    
    def generalize(self, typ: Type, bound_vars: Set[str]) -> Scheme:
        """
        Generalize a type over type variables not in bound_vars.
        This computes the principal type for let-binding.
        """
        free_vars = self.free_type_vars(typ)
        quantifiable = free_vars - bound_vars
        return Scheme(sorted(quantifiable), typ)
    
    def free_type_vars(self, typ: Type) -> Set[str]:
        """Get free type variables in a type"""
        if typ.kind == TypeKind.VAR:
            return {typ.var_name} if typ.var_name else set()
        elif typ.kind in (TypeKind.FUN, TypeKind.CON):
            vars_set = set()
            for arg in typ.args:
                vars_set.update(self.free_type_vars(arg))
            return vars_set
        elif typ.kind == TypeKind.ROW:
            vars_set = set()
            for arg in typ.args:
                vars_set.update(self.free_type_vars(arg))
            if typ.row_rest:
                vars_set.update(self.free_type_vars(typ.row_rest))
            return vars_set
        return set()


def generalize(env: TypeEnv, typ: Type, bound: Set[str]) -> Scheme:
    """Convenience wrapper for env.generalize"""
    return env.generalize(typ, bound)


def instantiate(scheme: Scheme) -> Type:
    """Instantiate a scheme with fresh type variables"""
    return scheme.instantiate()


# Built-in types and functions
BUILTIN_TYPES = {
    "int": Scheme([], int_type()),
    "float": Scheme([], float_type()),
    "bool": Scheme([], bool_type()),
    "string": Scheme([], string_type()),
}

BUILTIN_FUNCTIONS = {
    "+": Scheme([], fun_type(int_type(), int_type())),
    "-": Scheme([], fun_type(int_type(), int_type())),
    "*": Scheme([], fun_type(int_type(), int_type())),
    "/": Scheme([], fun_type(int_type(), int_type())),
    "print": Scheme([], fun_type(unit_type(), unit_type())),
}


def builtin_env() -> TypeEnv:
    """Create initial environment with built-in types and functions"""
    env = TypeEnv()
    for name, scheme in BUILTIN_TYPES.items():
        env.mapping[name] = scheme
    for name, scheme in BUILTIN_FUNCTIONS.items():
        env.mapping[name] = scheme
    return env
