"""
ALGOL 26 Type System

Core type representation for Hindley-Milner inference and static checking.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set, Union
from enum import Enum, auto


class TypeKind(Enum):
    PRIMITIVE = auto()
    TYPE_VAR = auto()
    FUNCTION = auto()
    ARRAY = auto()
    RECORD = auto()
    ADT = auto()
    EFFECT = auto()
    NAME = auto()  # For forward references (TypeName)


_type_var_counter = 0


def fresh_type_var() -> str:
    global _type_var_counter
    _type_var_counter += 1
    return chr(ord('a') + (_type_var_counter - 1) % 26) + ('' if _type_var_counter <= 26 else str(_type_var_counter // 26))


def reset_type_var_counter():
    global _type_var_counter
    _type_var_counter = 0


@dataclass(frozen=True)
class Type:
    """Base class for all types."""
    def occurs(self, var: 'TypeVar') -> bool:
        return False

    def substitute(self, subst: 'Substitution') -> 'Type':
        return self

    def free_vars(self) -> Set['TypeVar']:
        return set()

    def row_vars(self) -> Set['RowVar']:
        return set()


@dataclass(frozen=True)
class PrimitiveType(Type):
    name: str

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"PrimitiveType('{self.name}')"

    def __hash__(self):
        return hash((self.name, 'primitive'))


@dataclass(frozen=True)
class TypeVar(Type):
    name: str
    is_rigid: bool = False
    is_effect: bool = False

    def occurs(self, var: 'TypeVar') -> bool:
        return self == var

    def substitute(self, subst: 'Substitution') -> 'Type':
        if self in subst.mapping:
            return subst.mapping[self].substitute(subst)
        return self

    def free_vars(self) -> Set['TypeVar']:
        return {self}

    def __str__(self):
        prefix = "'" if self.is_rigid else ""
        return f"{prefix}{self.name}"

    def __repr__(self):
        return f"TypeVar('{self.name}', rigid={self.is_rigid}, effect={self.is_effect})"

    def __hash__(self):
        return hash((self.name, self.is_rigid, self.is_effect, 'var'))


@dataclass(frozen=True)
class TypeName(Type):
    """A forward reference to a named type. Will be resolved to actual Type during type checking."""
    name: str

    def substitute(self, subst: 'Substitution') -> 'Type':
        # TypeName should be resolved before substitution; if not, keep as is.
        return self

    def free_vars(self) -> Set['TypeVar']:
        return set()

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"TypeName('{self.name}')"

    def __hash__(self):
        return hash((self.name, 'name'))



@dataclass(frozen=True)
class BuiltinType(Type):
    """Marker type for built-in functions that have dynamic types (e.g., println)."""
    name: str

    def substitute(self, subst: 'Substitution') -> 'Type':
        return self

    def free_vars(self) -> Set['TypeVar']:
        return set()

    def __str__(self):
        return f"builtin({self.name})"

    def __repr__(self):
        return f"BuiltinType('{self.name}')"

    def __hash__(self):
        return hash((self.name, 'builtin'))

@dataclass(frozen=True)
class DistType(Type):
    """Distribution over a given element type."""
    element_type: Type

    def substitute(self, subst: 'Substitution') -> 'Type':
        return DistType(self.element_type.substitute(subst))

    def free_vars(self) -> Set['TypeVar']:
        return self.element_type.free_vars()

    def __str__(self):
        return f"Dist[{self.element_type}]"

    def __repr__(self):
        return f"DistType({self.element_type})"

    def __hash__(self):
        return hash(('dist', self.element_type))

@dataclass(frozen=True)
class FunctionType(Type):
    param_types: List[Type]
    return_type: Type
    effect: Optional[TypeVar] = field(default=None, compare=False)

    def __post_init__(self):
        if self.effect is not None and not isinstance(self.effect, TypeVar):
            raise TypeError("Effect must be a TypeVar or None")

    def substitute(self, subst: 'Substitution') -> 'Type':
        new_params = [p.substitute(subst) for p in self.param_types]
        new_ret = self.return_type.substitute(subst)
        new_effect = self.effect.substitute(subst) if self.effect else None
        return FunctionType(new_params, new_ret, new_effect)

    def free_vars(self) -> Set['TypeVar']:
        vars_set = set()
        for p in self.param_types:
            vars_set.update(p.free_vars())
        vars_set.update(self.return_type.free_vars())
        if self.effect:
            vars_set.update(self.effect.free_vars())
        return vars_set

    def __str__(self):
        params = ', '.join(str(p) for p in self.param_types)
        eff = f" ~ {self.effect}" if self.effect else ""
        return f"({params}) -> {self.return_type}{eff}"

    def __repr__(self):
        return f"FunctionType({self.param_types}, {self.return_type}, effect={self.effect})"

    def __hash__(self):
        return hash(('function', tuple(self.param_types), self.return_type))


@dataclass(frozen=True)
class ArrayType(Type):
    element_type: Type
    size: Optional[Any] = None  # Typically an integer or an expression node (for constant folding later)

    def substitute(self, subst: 'Substitution') -> 'Type':
        return ArrayType(self.element_type.substitute(subst), self.size)

    def free_vars(self) -> Set['TypeVar']:
        return self.element_type.free_vars()

    def __str__(self):
        size_str = f"[{self.size}]" if self.size else "[]"
        return f"array{size_str} of {self.element_type}"

    def __repr__(self):
        return f"ArrayType({self.element_type}, size={self.size})"

    def __hash__(self):
        return hash(('array', self.element_type, self.size))


@dataclass(frozen=True)
class RecordType(Type):
    fields: Dict[str, Type]  # field name -> type
    row_var: Optional[TypeVar] = field(default=None, compare=False)

    def substitute(self, subst: 'Substitution') -> 'Type':
        new_fields = {name: ft.substitute(subst) for name, ft in self.fields.items()}
        new_row = self.row_var.substitute(subst) if self.row_var else None
        return RecordType(new_fields, new_row)

    def free_vars(self) -> Set['TypeVar']:
        vars_set = set()
        for ft in self.fields.values():
            vars_set.update(ft.free_vars())
        if self.row_var:
            vars_set.update(self.row_var.free_vars())
        return vars_set

    def row_vars(self) -> Set['RowVar']:
        return {self.row_var} if self.row_var else set()

    def __str__(self):
        fields_str = ', '.join(f"{name}: {typ}" for name, typ in self.fields.items())
        row_str = f", ..{self.row_var}" if self.row_var else ""
        return f"{{{fields_str}{row_str}}}"

    def __repr__(self):
        return f"RecordType({self.fields}, row_var={self.row_var})"

    def __hash__(self):
        return hash(('record', frozenset(self.fields.items()), self.row_var))


@dataclass(frozen=True)
class ADTConstructor(Type):
    name: str
    arg_types: List[Type]

    def substitute(self, subst: 'Substitution') -> 'Type':
        new_args = [arg.substitute(subst) for arg in self.arg_types]
        return ADTConstructor(self.name, new_args)

    def free_vars(self) -> Set['TypeVar']:
        vars_set = set()
        for arg in self.arg_types:
            vars_set.update(arg.free_vars())
        return vars_set

    def __str__(self):
        args = ', '.join(str(a) for a in self.arg_types) if self.arg_types else ''
        return f"{self.name}({args})"

    def __repr__(self):
        return f"ADTConstructor('{self.name}', {self.arg_types})"

    def __hash__(self):
        return hash(('adt_ctor', self.name, tuple(self.arg_types)))


@dataclass(frozen=True)
class ADTType(Type):
    name: str
    constructors: List[ADTConstructor]

    def substitute(self, subst: 'Substitution') -> 'Type':
        new_ctors = [ctor.substitute(subst) for ctor in self.constructors]
        return ADTType(self.name, new_ctors)

    def free_vars(self) -> Set['TypeVar']:
        vars_set = set()
        for ctor in self.constructors:
            vars_set.update(ctor.free_vars())
        return vars_set

    def __str__(self):
        ctors = ' | '.join(str(c) for c in self.constructors)
        return f"{self.name} = {ctors}"

    def __repr__(self):
        return f"ADTType('{self.name}', {self.constructors})"

    def __hash__(self):
        return hash(('adt', self.name, tuple(self.constructors)))


@dataclass
class Substitution:
    mapping: Dict[TypeVar, Type] = field(default_factory=dict)

    def add(self, var: TypeVar, typ: Type):
        self.mapping[var] = typ

    def apply(self, typ: Type) -> Type:
        return typ.substitute(self)

    def compose(self, other: 'Substitution') -> 'Substitution':
        new_map = {}
        for var, typ in other.mapping.items():
            new_map[var] = self.apply(typ)
        for var, typ in self.mapping.items():
            new_map[var] = typ
        return Substitution(new_map)

    def __str__(self):
        items = ', '.join(f"{k} -> {v}" for k, v in self.mapping.items())
        return f"{{{items}}}"

    def __repr__(self):
        return f"Substitution({self.mapping})"

    def is_empty(self) -> bool:
        return not self.mapping


class UnificationError(Exception):
    def __init__(self, message, type1=None, type2=None):
        self.type1 = type1
        self.type2 = type2
        super().__init__(message)


def unify(t1: Type, t2: Type) -> Substitution:
    if t1 == t2:
        return Substitution()

    if isinstance(t1, TypeVar):
        return var_bind(t1, t2)

    if isinstance(t2, TypeVar):
        return var_bind(t2, t1)

    if isinstance(t1, FunctionType) and isinstance(t2, FunctionType):
        if len(t1.param_types) != len(t2.param_types):
            raise UnificationError(f"Function arity mismatch: {len(t1.param_types)} vs {len(t2.param_types)}", t1, t2)
        subst = Substitution()
        for p1, p2 in zip(t1.param_types, t2.param_types):
            s1 = unify(apply_subst(p1, subst), apply_subst(p2, subst))
            subst = compose_subst(s1, subst)
        s2 = unify(apply_subst(t1.return_type, subst), apply_subst(t2.return_type, subst))
        subst = compose_subst(s2, subst)
        if t1.effect or t2.effect:
            e1 = t1.effect if t1.effect else TypeVar(fresh_type_var(), is_effect=True)
            e2 = t2.effect if t2.effect else TypeVar(fresh_type_var(), is_effect=True)
            s3 = unify(apply_subst(e1, subst), apply_subst(e2, subst))
            subst = compose_subst(s3, subst)
        return subst

    if isinstance(t1, ArrayType) and isinstance(t2, ArrayType):
        return unify(t1.element_type, t2.element_type)

    if isinstance(t1, RecordType) and isinstance(t2, RecordType):
        fields1 = set(t1.fields.keys())
        fields2 = set(t2.fields.keys())
        if fields1 != fields2:
            raise UnificationError(f"Record fields mismatch: {fields1} vs {fields2}", t1, t2)
        subst = Substitution()
        for name in fields1:
            s_field = unify(apply_subst(t1.fields[name], subst), apply_subst(t2.fields[name], subst))
            subst = compose_subst(s_field, subst)
        if t1.row_var and t2.row_var:
            s_row = unify(apply_subst(t1.row_var, subst), apply_subst(t2.row_var, subst))
            subst = compose_subst(s_row, subst)
        elif t1.row_var or t2.row_var:
            raise UnificationError(f"Row variable mismatch: {t1.row_var} vs {t2.row_var}", t1, t2)
        return subst

    if isinstance(t1, ADTType) and isinstance(t2, ADTType):
        if t1.name != t2.name:
            raise UnificationError(f"ADT name mismatch: {t1.name} vs {t2.name}", t1, t2)
        if len(t1.constructors) != len(t2.constructors):
            raise UnificationError(f"ADT constructor count mismatch for {t1.name}", t1, t2)
        subst = Substitution()
        for c1, c2 in zip(t1.constructors, t2.constructors):
            if c1.name != c2.name:
                raise UnificationError(f"ADT constructor name mismatch: {c1.name} vs {c2.name}", t1, t2)
            if len(c1.arg_types) != len(c2.arg_types):
                raise UnificationError(f"ADT constructor arg count mismatch for {c1.name}", t1, t2)
            for a1, a2 in zip(c1.arg_types, c2.arg_types):
                s = unify(apply_subst(a1, subst), apply_subst(a2, subst))
                subst = compose_subst(s, subst)
        return subst

    if isinstance(t1, ADTConstructor) and isinstance(t2, ADTConstructor):
        if t1.name != t2.name:
            raise UnificationError(f"ADT constructor mismatch: {t1.name} vs {t2.name}", t1, t2)
        if len(t1.arg_types) != len(t2.arg_types):
            raise UnificationError(f"ADT constructor arg count mismatch for {t1.name}", t1, t2)
        subst = Substitution()
        for a1, a2 in zip(t1.arg_types, t2.arg_types):
            s = unify(apply_subst(a1, subst), apply_subst(a2, subst))
            subst = compose_subst(s, subst)
        return subst

    if isinstance(t1, DistType) and isinstance(t2, DistType):
        return unify(t1.element_type, t2.element_type)

    if isinstance(t1, PrimitiveType) and isinstance(t2, PrimitiveType):
        if t1.name == t2.name:
            return Substitution()
        raise UnificationError(f"Primitive type mismatch: {t1.name} vs {t2.name}", t1, t2)

    raise UnificationError(f"Cannot unify {t1} with {t2}", t1, t2)


def var_bind(var: TypeVar, typ: Type) -> Substitution:
    if var == typ:
        return Substitution()
    if var.occurs(typ):
        raise UnificationError(f"Occurs check failed: {var} occurs in {typ}")
    if var.is_rigid:
        raise UnificationError(f"Cannot bind rigid type variable {var} to {typ}")
    subst = Substitution()
    subst.add(var, typ)
    return subst


def apply_subst(typ: Type, subst: Substitution) -> Type:
    return subst.apply(typ)


def compose_subst(s1: Substitution, s2: Substitution) -> Substitution:
    new_map = {}
    for var, typ in s2.mapping.items():
        new_map[var] = s1.apply(typ)
    for var, typ in s1.mapping.items():
        new_map[var] = typ
    return Substitution(new_map)


# Predefined primitive types
INT_TYPE = PrimitiveType('int')
REAL_TYPE = PrimitiveType('real')
BOOL_TYPE = PrimitiveType('bool')
CHAR_TYPE = PrimitiveType('char')
STRING_TYPE = PrimitiveType('string')
VOID_TYPE = PrimitiveType('void')
NULL_TYPE = PrimitiveType('null')

PRIMITIVE_TYPES = {
    'int': INT_TYPE,
    'real': REAL_TYPE,
    'bool': BOOL_TYPE,
    'char': CHAR_TYPE,
    'string': STRING_TYPE,
    'void': VOID_TYPE,
    'null': NULL_TYPE,
}


def is_primitive_type(name: str) -> bool:
    return name in PRIMITIVE_TYPES


# Row var for records
class RowVar(TypeVar):
    def __init__(self, name: str):
        super().__init__(name, is_rigid=False, is_effect=False)

    def __str__(self):
        return f"..{self.name}"

    def __repr__(self):
        return f"RowVar('{self.name}')"


def fresh_row_var() -> RowVar:
    return RowVar(fresh_type_var())


# Effect types (lightweight)
# We can define a polymorphic effect system but MVP: just track effect variable per function. Effects are separate from value types.
