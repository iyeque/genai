"""
ALGOL 26 Type System - Core Type Representation

Defines the data structures for types in the Hindley-Milner type inference system
with extensions: ADTs, row polymorphism, and effect tracking.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set, Union
from enum import Enum, auto


class TypeKind(Enum):
    """Kinds of types for quick discrimination."""
    PRIMITIVE = auto()
    TYPE_VAR = auto()
    FUNCTION = auto()
    ARRAY = auto()
    RECORD = auto()
    ADT = auto()  # Algebraic Data Type (sum type)
    EFFECT = auto()


# Type variable counter for generating fresh type variables
_type_var_counter = 0


def fresh_type_var() -> str:
    """Generate a fresh type variable name (e.g., 'a', 'b', ...)."""
    global _type_var_counter
    _type_var_counter += 1
    return chr(ord('a') + (_type_var_counter - 1) % 26) + ('' if _type_var_counter <= 26 else str(_type_var_counter // 26))


def reset_type_var_counter():
    """Reset counter for clean testing."""
    global _type_var_counter
    _type_var_counter = 0


@dataclass(frozen=True)
class Type:
    """Base class for all types."""
    # kind: TypeKind  # Can use isinstance checks instead

    def occurs(self, var: 'TypeVar') -> bool:
        """Check if a type variable occurs in this type (for occurs check)."""
        return False

    def substitute(self, subst: 'Substitution') -> 'Type':
        """Apply a substitution (mapping from type variables to types)."""
        return self

    def free_vars(self) -> Set['TypeVar']:
        """Set of free type variables."""
        return set()

    def row_vars(self) -> Set['RowVar']:
        """Set of row variables (for row polymorphism)."""
        return set()


@dataclass(frozen=True)
class PrimitiveType(Type):
    """Primitive types: int, real, bool, char, string, void, etc."""
    name: str

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"PrimitiveType('{self.name}')"

    def __hash__(self):
        return hash((self.name, 'primitive'))


@dataclass(frozen=True)
class TypeVar(Type):
    """Type variable (e.g., 'a', 'b'). May be quantified (generic) or unification variable."""
    name: str
    is_rigid: bool = False  # True if this var is a quantified generic (rigid), False if unification variable (flexible)
    is_effect: bool = False  # True if this is an effect variable

    def occurs(self, var: 'TypeVar') -> bool:
        return self == var

    def substitute(self, subst: 'Substitution') -> 'Type':
        if self in subst.mapping:
            return subst.mapping[self].substitute(subst)
        return self

    def free_vars(self) -> Set['TypeVar']:
        return {self}

    def __str__(self):
        prefix = "'" if self.is_rigid else ""  # Haskell style: 'a for rigid
        # For effect vars, maybe use different notation
        return f"{prefix}{self.name}"

    def __repr__(self):
        return f"TypeVar('{self.name}', rigid={self.is_rigid}, effect={self.is_effect})"

    def __hash__(self):
        return hash((self.name, self.is_rigid, self.is_effect, 'var'))


@dataclass(frozen=True)
class FunctionType(Type):
    """Function type: (param types) -> return type with effect"""
    param_types: List[Type]
    return_type: Type
    effect: Optional[TypeVar] = field(default=None, compare=False)  # Effect variable (e.g., for IO)

    def __post_init__(self):
        # Ensure effect is a TypeVar or None
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
        # Note: Not including effect in hash for simplicity, though it's part of type equality ideally
        # But for now, we may treat effect as separate orthogonal property
        return hash(('function', tuple(self.param_types), self.return_type))


@dataclass(frozen=True)
class ArrayType(Type):
    """Array type: array[n] of T or array[] of T (dynamic)"""
    element_type: Type
    size: Optional[Expr] = None  # For now size is an expression; later could be Type (constant int)

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
    """Record type: { field1: T1, field2: T2, ... } with optional row variable for extensibility"""
    fields: Dict[str, Type]  # field name -> type
    row_var: Optional[TypeVar] = field(default=None, compare=False)  # Row variable for polymorphism (e.g., { name: string, .. })

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
        # RowVar is a special type variable for rows. Here we treat it as TypeVar with row flag.
        return {self.row_var} if self.row_var else set()

    def __str__(self):
        fields_str = ', '.join(f"{name}: {typ}" for name, typ in self.fields.items())
        row_str = f", ..{self.row_var}" if self.row_var else ""
        return f"{{{fields_str}{row_str}}}"

    def __repr__(self):
        return f"RecordType({self.fields}, row_var={self.row_var})"

    def __hash__(self):
        # Record hash: field names/ types + row var if present. Order matters for fields? In ALGOL 26, record fields are unordered but we represent as dict (unordered). Hash based on frozenset of items.
        return hash(('record', frozenset(self.fields.items()), self.row_var))


@dataclass(frozen=True)
class ADTConstructor(Type):
    """A constructor for an Algebraic Data Type. Has a name and argument types."""
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
    """Algebraic Data Type (sum type) representing a union of constructors."""
    name: str  # Type name, e.g., "Option", "Result"
    constructors: List[ADTConstructor]  # All constructors

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
    """Mapping from type variables to types. Mutable, for use during unification."""
    mapping: Dict[TypeVar, Type] = field(default_factory=dict)

    def add(self, var: TypeVar, typ: Type):
        """Add a substitution. Must check for occurs check before calling."""
        self.mapping[var] = typ

    def apply(self, typ: Type) -> Type:
        """Apply this substitution to a type (returns new type)."""
        return typ.substitute(self)

    def compose(self, other: 'Substitution') -> 'Substitution':
        """Compose this substitution with another: s1 ∘ s2 = s3 where s3(x) = s1(s2(x))."""
        new_map = {}
        # Apply s1 to all values in s2, then merge s1
        for var, typ in self.mapping.items():
            new_map[var] = typ
        for var, typ in other.mapping.items():
            new_map[var] = self.apply(typ)
        return Substitution(new_map)

    def __str__(self):
        items = ', '.join(f"{k} -> {v}" for k, v in self.mapping.items())
        return f"{{{items}}}"

    def __repr__(self):
        return f"Substitution({self.mapping})"

    def is_empty(self) -> bool:
        return not self.mapping


class UnificationError(Exception):
    """Error during type unification."""
    def __init__(self, message, type1=None, type2=None):
        self.type1 = type1
        self.type2 = type2
        super().__init__(message)


def unify(t1: Type, t2: Type) -> Substitution:
    """
    Unify two types, returning a substitution that makes them equal.
    May raise UnificationError.
    """
    # Apply current substitution to both? We assume types are already free of known substitutions at point of call
    # Actually we can just unify directly; substitution application is handled by caller if necessary

    # If types are already equal (structurally)
    if t1 == t2:
        return Substitution()

    # Case: t1 is TypeVar
    if isinstance(t1, TypeVar):
        return var_bind(t1, t2)

    # Case: t2 is TypeVar
    if isinstance(t2, TypeVar):
        return var_bind(t2, t1)

    # Case: both are FunctionType
    if isinstance(t1, FunctionType) and isinstance(t2, FunctionType):
        if len(t1.param_types) != len(t2.param_types):
            raise UnificationError(f"Function arity mismatch: {len(t1.param_types)} vs {len(t2.param_types)}", t1, t2)
        subst = Substitution()
        for p1, p2 in zip(t1.param_types, t2.param_types):
            s1 = unify(apply_subst(p1, subst), apply_subst(p2, subst))
            subst = compose_subst(s1, subst)
        # Unify return types
        s2 = unify(apply_subst(t1.return_type, subst), apply_subst(t2.return_type, subst))
        subst = compose_subst(s2, subst)
        # Unify effects if present
        if t1.effect or t2.effect:
            e1 = t1.effect if t1.effect else TypeVar(fresh_type_var(), is_effect=True)
            e2 = t2.effect if t2.effect else TypeVar(fresh_type_var(), is_effect=True)
            s3 = unify(apply_subst(e1, subst), apply_subst(e2, subst))
            subst = compose_subst(s3, subst)
        return subst

    # Case: both are ArrayType
    if isinstance(t1, ArrayType) and isinstance(t2, ArrayType):
        subst = unify(t1.element_type, t2.element_type)
        # For now ignore size differences; MVP allows size to differ? Usually arrays of different sizes are same type if element type matches. In ALGOL 26, size may be part of type? We'll treat sizes as not affecting type equality unless they are constant expressions that evaluate to same number? Better to ignore size for unification as they are both arrays regardless of size.
        return subst

    # Case: both are RecordType
    if isinstance(t1, RecordType) and isinstance(t2, RecordType):
        # Row polymorphism: if both have row vars, we must unify them
        subst = Substitution()
        # Check that field sets match (names), and unify field types
        fields1 = set(t1.fields.keys())
        fields2 = set(t2.fields.keys())
        if fields1 != fields2:
            raise UnificationError(f"Record fields mismatch: {fields1} vs {fields2}", t1, t2)
        for name in fields1:
            s_field = unify(apply_subst(t1.fields[name], subst), apply_subst(t2.fields[name], subst))
            subst = compose_subst(s_field, subst)
        # Handle row variables
        if t1.row_var and t2.row_var:
            s_row = unify(apply_subst(t1.row_var, subst), apply_subst(t2.row_var, subst))
            subst = compose_subst(s_row, subst)
        elif t1.row_var or t2.row_var:
            # One has row var, the other is closed; we can extend the closed to have row var that matches extra fields. But simpler: require both to have same row status for now.
            # Actually we could treat row var as unifiable with a record that extends. But we'll leave as MVP: both rows must match.
            raise UnificationError(f"Row variable mismatch: {t1.row_var} vs {t2.row_var}", t1, t2)
        return subst

    # Case: both are ADTType (same ADT)
    if isinstance(t1, ADTType) and isinstance(t2, ADTType):
        if t1.name != t2.name:
            raise UnificationError(f"ADT name mismatch: {t1.name} vs {t2.name}", t1, t2)
        if len(t1.constructors) != len(t2.constructors):
            raise UnificationError(f"ADT constructor count mismatch for {t1.name}", t1, t2)
        # Constructors should be in same order? They may differ. Usually ADT constructors are unique; but two ADTType values representing the same type should have same constructors. So they should be identical if same name.
        # For simplicity, require exact match of constructors (name order)
        for c1, c2 in zip(t1.constructors, t2.constructors):
            if c1.name != c2.name:
                raise UnificationError(f"ADT constructor name mismatch: {c1.name} vs {c2.name}", t1, t2)
            if len(c1.arg_types) != len(c2.arg_types):
                raise UnificationError(f"ADT constructor arg count mismatch for {c1.name}", t1, t2)
            subst = Substitution()
            for a1, a2 in zip(c1.arg_types, c2.arg_types):
                s = unify(apply_subst(a1, subst), apply_subst(a2, subst))
                subst = compose_subst(s, subst)
        return Substitution()

    # Case: both are ADTConstructor (should happen when matching a value against a pattern)
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

    # Case: Primitive types
    if isinstance(t1, PrimitiveType) and isinstance(t2, PrimitiveType):
        if t1.name == t2.name:
            return Substitution()
        raise UnificationError(f"Primitive type mismatch: {t1.name} vs {t2.name}", t1, t2)

    raise UnificationError(f"Cannot unify {t1} with {t2}", t1, t2)


def var_bind(var: TypeVar, typ: Type) -> Substitution:
    """Bind a type variable to a type, with occurs check."""
    if var == typ:
        return Substitution()
    if var.occurs(typ):
        raise UnificationError(f"Occurs check failed: {var} occurs in {typ}")

    # Note: If var is rigid (quantified generic), we cannot bind it to an arbitrary type. But in HM, rigid variables come from generalization; during inference they shouldn't be unified. We'll check is_rigid.
    if var.is_rigid:
        raise UnificationError(f"Cannot bind rigid type variable {var} to {typ}")

    subst = Substitution()
    subst.add(var, typ)
    return subst


def apply_subst(typ: Type, subst: Substitution) -> Type:
    """Apply substitution to a type (convenience)."""
    return subst.apply(typ)


def compose_subst(s1: Substitution, s2: Substitution) -> Substitution:
    """Compose s1 after s2: s1 ∘ s2."""
    # Equivalent to apply s1 to all values in s2, then merge s1
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
NULL_TYPE = PrimitiveType('null')  # null literal type; may be a subtype of all? but we treat as distinct


def is_primitive_type(name: str) -> bool:
    return name in ('int', 'real', 'bool', 'char', 'string', 'void', 'null')


PRIMITIVE_TYPES = {
    'int': INT_TYPE,
    'real': REAL_TYPE,
    'bool': BOOL_TYPE,
    'char': CHAR_TYPE,
    'string': STRING_TYPE,
    'void': VOID_TYPE,
    'null': NULL_TYPE,
}


# Row var for records
class RowVar(TypeVar):
    """Special type variable for record row polymorphism."""
    def __init__(self, name: str):
        super().__init__(name, is_rigid=False, is_effect=False)
        # We could tag it differently

    def __str__(self):
        return f"..{self.name}"

    def __repr__(self):
        return f"RowVar('{self.name}')"


def fresh_row_var() -> RowVar:
    """Create a fresh row variable."""
    return RowVar(fresh_type_var())


# Effect types
PURE_EFFECT = TypeVar("pure", is_rigid=False, is_effect=True)  # Not a real effect, placeholder
IO_EFFECT = TypeVar("io", is_rigid=False, is_effect=True)
