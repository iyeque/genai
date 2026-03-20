"""
ALGOL 26 Typechecker: Module System

This module implements:
- Module resolution with search path
- Import/export handling
- Namespace management
- Cyclic dependency detection
- Interface files (.algol26i) for separate compilation
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import json


class ModuleError(Exception):
    """Base exception for module system errors"""
    pass


class CyclicDependencyError(ModuleError):
    """Raised when cyclic dependency is detected"""
    pass


class ModuleNotFoundError(ModuleError):
    """Raised when a module cannot be found"""
    pass


@dataclass
class Export:
    """Represents an exported entity from a module"""
    name: str  # Original name in module
    alias: Optional[str] = None  # Alias if renamed on export
    
    def public_name(self) -> str:
        """Get the name visible to importers"""
        return self.alias or self.name


@dataclass
class ModuleSignature:
    """
    Module signature/interface (for separate compilation).
    Stored in .algol26i files (JSON format).
    """
    name: str  # Module name (e.g., "math", "utils::vector")
    exports: List[Export] = field(default_factory=list)
    types: Dict[str, str] = field(default_factory=dict)  # Virtual "type" info (simplified)
    # In full implementation: would store type schemes, abstract types, etc.
    
    def to_dict(self) -> dict:
        """Serialize to dict for JSON"""
        return {
            "name": self.name,
            "exports": [
                {"name": e.name, "alias": e.alias} for e in self.exports
            ],
            "types": self.types
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> ModuleSignature:
        """Deserialize from dict"""
        exports = [Export(e["name"], e.get("alias")) for e in data.get("exports", [])]
        return cls(name=data["name"], exports=exports, types=data.get("types", {}))


class Module:
    """
    Represents a loaded module.
    Contains source AST, signature, and dependency information.
    """
    
    def __init__(self, name: str, source_path: Path, ast: Any = None):
        self.name = name
        self.source_path = source_path
        self.ast = ast  # Will be set after parsing
        self.signature: Optional[ModuleSignature] = None
        self.dependencies: List[ImportStatement] = []
        self.exported_names: Set[str] = set()
        self._namespace: Dict[str, Any] = {}  # Populated after type checking
        
    def add_export(self, name: str, alias: Optional[str] = None):
        """Add an exported name"""
        self.exported_names.add(name)
        # In full impl: would also add to signature
    
    def namespace(self) -> Dict[str, Any]:
        """Get module's namespace (type-checked symbols)"""
        return self._namespace
    
    def set_namespace(self, ns: Dict[str, Any]):
        """Set module's namespace after type checking"""
        self._namespace = ns


@dataclass
class ImportStatement:
    """
    Represents an import statement within a module.
    Parsed from: import module.{x, y} as alias, etc.
    """
    module_name: str
    items: Optional[List[Tuple[str, Optional[str]]]] = None  # [(original_name, alias), ...]
    # None means import all (wildcard)
    alias: Optional[str] = None  # Rename imported module
    
    def is_wildcard(self) -> bool:
        """Check if this is a wildcard import"""
        return self.items is None
    
    def imported_name(self, original: str) -> str:
        """Get the name under which an original will be imported"""
        # Check if item has alias
        if self.items:
            for orig, aliases in self.items:
                if orig == original:
                    return aliases or original
        # Wildcard or specific item without alias
        return original


@dataclass
class ExportStatement:
    """
    Represents an export statement within a module.
    Controls what is visible to other modules.
    """
    items: List[Tuple[str, Optional[str]]]  # [(name, alias), ...]
    # Empty list means export all public (default)
    
    def is_export_all(self) -> bool:
        """Check if this exports all public names"""
        return len(self.items) == 0


class ModuleResolver:
    """
    Resolves module imports, handles search paths, and detects cycles.
    """
    
    def __init__(self, search_paths: List[Path] = None):
        self.search_paths = search_paths or [Path("."), Path("./stdlib")]
        self.loaded_modules: Dict[str, Module] = {}  # name -> Module
        self.loading_stack: List[str] = []  # For cycle detection
        self.interface_cache: Dict[Path, ModuleSignature] = {}
        
    def resolve_import(self, import_stmt: ImportStatement, 
                      importing_module: Module) -> List[Module]:
        """
        Resolve an import statement to loaded Module objects.
        Returns list of imported modules.
        """
        module_name = import_stmt.module_name
        module = self._load_module(module_name)
        
        # Handle alias for the module itself
        if import_stmt.alias:
            # For now, alias creates a new name in importing module's namespace
            # In full impl: would add alias to importing_module's namespace
            pass
        
        imported_modules = [module]
        return imported_modules
    
    def _load_module(self, name: str) -> Module:
        """
        Load a module by name, resolving its path and checking cycles.
        """
        # Check if already loaded
        if name in self.loaded_modules:
            return self.loaded_modules[name]
        
        # Cycle detection
        if name in self.loading_stack:
            cycle = " -> ".join(self.loading_stack + [name])
            raise CyclicDependencyError(f"Cyclic dependency detected: {cycle}")
        
        self.loading_stack.append(name)
        
        try:
            # Find module file
            path = self._find_module_file(name)
            
            # Check for interface file (.algol26i) first
            interface_path = path.with_suffix(".algol26i")
            if interface_path.exists():
                signature = self._load_interface(interface_path)
                # In full impl: would load precompiled module or compile from source
                module = Module(name, path)
                module.signature = signature
            else:
                # Need to parse source (this would be done by parser)
                # For now, create placeholder
                module = Module(name, path)
                # self._parse_and_typecheck(module) would go here
            
            self.loaded_modules[name] = module
            return module
            
        finally:
            self.loading_stack.pop()
    
    def _find_module_file(self, name: str) -> Path:
        """
        Find the source file for a module name.
        Searches in search_paths with various extensions.
        """
        # Convert module name to path (e.g., "utils::vector" -> "utils/vector.algol26")
        rel_path = name.replace("::", "/") + ".algol26"
        
        for search_path in self.search_paths:
            candidate = search_path / rel_path
            if candidate.exists():
                return candidate
            
            # Also check capitalized versions, etc. if needed
            candidate_upper = search_path / rel_path.upper()
            if candidate_upper.exists():
                return candidate_upper
        
        raise ModuleNotFoundError(f"Module '{name}' not found in search paths: {self.search_paths}")
    
    def _load_interface(self, path: Path) -> ModuleSignature:
        """Load a module interface (.algol26i) from JSON"""
        if path in self.interface_cache:
            return self.interface_cache[path]
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        signature = ModuleSignature.from_dict(data)
        self.interface_cache[path] = signature
        return signature
    
    def clear_cache(self):
        """Clear loaded modules (for testing)"""
        self.loaded_modules.clear()
        self.interface_cache.clear()
        self.loading_stack.clear()
    
    def create_interface(self, module: Module, output_path: Path):
        """
        Create an interface file for a module after successful type checking.
        This is used for separate compilation.
        """
        if not module.signature:
            raise ModuleError("Module has no signature")
        
        sig_dict = module.signature.to_dict()
        with open(output_path, 'w') as f:
            json.dump(sig_dict, f, indent=2)


class Namespace:
    """
    Manages the combined namespace of multiple imported modules.
    Handles name resolution with shadowing and aliasing.
    """
    
    def __init__(self):
        self.bindings: Dict[str, ModuleSource] = {}
        self.module_aliases: Dict[str, str] = {}  # alias -> actual module name
        
    def add_module(self, name: str, module: Module, 
                   import_stmt: ImportStatement = None):
        """
        Add a module's exports to the namespace.
        Respects selective imports and renaming.
        """
        if import_stmt is None:
            # Import whole module with its name
            for exported_name in module.exported_names:
                # For now, direct binding (no aliasing logic yet)
                if exported_name not in self.bindings:
                    self.bindings[exported_name] = ModuleSource(name, exported_name)
            if import_stmt and import_stmt.alias:
                self.module_aliases[import_stmt.alias] = name
        else:
            # Selective import
            if import_stmt.is_wildcard():
                # Import all exports
                for exported_name in module.exported_names:
                    self.bindings[exported_name] = ModuleSource(name, exported_name)
            else:
                # Import specific items
                for orig_name, alias in import_stmt.items:
                    if orig_name in module.exported_names:
                        binding_name = alias or orig_name
                        # Remove any existing binding of that name
                        self.bindings.pop(binding_name, None)
                        self.bindings[binding_name] = ModuleSource(name, orig_name)
    
    def resolve(self, name: str) -> Optional[ModuleSource]:
        """Resolve a name to its source module"""
        return self.bindings.get(name)
    
    def has_name(self, name: str) -> bool:
        """Check if a name is in the namespace"""
        return name in self.bindings


@dataclass
class ModuleSource:
    """
    Tracks where a name came from.
    Used for error messages and qualified references.
    """
    module_name: str
    original_name: str
    
    def qualified_name(self) -> str:
        """Get fully qualified name"""
        return f"{self.module_name}::{self.original_name}"


def build_signature_from_module(module: Module) -> ModuleSignature:
    """
    Construct a module signature from a type-checked module.
    Captures all public exports and their type information.
    """
    sig = ModuleSignature(module.name)
    
    for name, scheme in module.namespace().items():
        # Track export with alias handling (simplified)
        sig.exports.append(Export(name))
        # Could also store type info: sig.types[name] = repr(scheme.type)
    
    module.signature = sig
    return sig
