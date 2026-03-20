"""
ALGOL 26 Parser

Recursive descent parser for ALGOL 26 grammar.
Extended with import/export statements.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Any, Tuple
from enum import Enum, auto

from .lexer import Token, TokenType, tokenize
from .ast import (
    ModuleDecl, ImportStmt, ImportItem, 
    ExportStmt, ExportItem, FuncDecl, Param,
    LetDecl, LetBinding, TypeDecl, Type, NamedType,
    IntLiteral, FloatLiteral, BoolLiteral, StringLiteral,
    Identifier, Lambda
)


class ParseError(Exception):
    """Parser error"""
    def __init__(self, message: str, token: Token):
        super().__init__(f"{message} at line {token.line}, column {token.column}")
        self.token = token
        self.message = message


class Parser:
    """
    Recursive descent parser.
    Grammar (simplified):
    
    program ::= module_decl
    module_decl ::= "module" IDENTIFIER "{" decl* "}"
    decl ::= import_stmt | export_stmt | func_decl | type_decl | let_decl
    import_stmt ::= "import" module_spec ("," module_spec)*
    module_spec ::= IDENTIFIER ("." IDENTIFIER)* 
                    ("as" IDENTIFIER)? 
                    ("{" IDENTIFIER ("," IDENTIFIER)* "}")?
    export_stmt ::= "export" IDENTIFIER ("," IDENTIFIER)*
    func_decl ::= "func" IDENTIFIER "(" params? ")" "=" expr
    params ::= param ("," param)*
    param ::= IDENTIFIER (":" type)?
    let_decl ::= "let" IDENTIFIER "=" expr ("and" IDENTIFIER "=" expr)* "in" expr
    type ::= IDENTIFIER | type "->" type | "(" type ")"
    expr ::= literal | identifier | lambda | app | if_expr | match_expr
    lambda ::= "(" IDENTIFIER ":" type? ")" "=>" expr | IDENTIFIER "=>" expr
    app ::= expr expr
    if_expr ::= "if" expr "then" expr ("else" expr)?
    match_expr ::= "match" expr "{" case+ "}"
    case ::= pattern "=>" expr
    pattern ::= IDENTIFIER | "_" | literal
    literal ::= INT | FLOAT | STRING | BOOL
    """
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token = tokens[0] if tokens else None
    
    def parse(self) -> ModuleDecl:
        """Parse the token stream into an AST"""
        return self._parse_module()
    
    def _advance(self):
        """Consume current token and move to next"""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = Token(TokenType.EOF, '', 0, 0)
    
    def _expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type, raise error if not matched"""
        if self.current_token.token_type == token_type:
            token = self.current_token
            self._advance()
            return token
        raise ParseError(f"Expected {token_type.name}, got {self.current_token.token_type.name}", 
                        self.current_token)
    
    def _match(self, token_type: TokenType) -> bool:
        """Check if current token matches type without consuming"""
        return self.current_token.token_type == token_type
    
    # --- Top-level parsing ---
    
    def _parse_module(self) -> ModuleDecl:
        """Parse module declaration"""
        self._expect(TokenType.MODULE)
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.LBRACE)
        
        imports = []
        exports = []
        declarations = []
        
        while not self._match(TokenType.RBRACE) and not self._match(TokenType.EOF):
            if self._match(TokenType.IMPORT):
                imports.append(self._parse_import())
            elif self._match(TokenType.EXPORT):
                exports.append(self._parse_export())
            elif self._match(TokenType.FUNC):
                declarations.append(self._parse_func_decl())
            elif self._match(TokenType.LET):
                declarations.append(self._parse_let_decl())
            elif self._match(TokenType.TYPE):
                declarations.append(self._parse_type_decl())
            else:
                raise ParseError(f"Unexpected token in module: {self.current_token.token_type.name}",
                               self.current_token)
        
        self._expect(TokenType.RBRACE)
        
        return ModuleDecl(
            name=name_token.value,
            imports=imports,
            exports=exports,
            declarations=declarations
        )
    
    def _parse_import(self) -> ImportStmt:
        """Parse import statement"""
        self._expect(TokenType.IMPORT)
        
        items = []
        while True:
            module_spec = self._parse_module_spec()
            items.append(module_spec)
            
            if self._match(TokenType.COMMA):
                self._advance()
            else:
                break
        
        # For now, we return a single ImportStmt with the first specification
        # A real implementation would handle multiple imports better
        first = items[0] if items else None
        if first:
            return ImportStmt(
                module_name=first.module_name,
                alias=first.alias,
                items=first.items
            )
        return ImportStmt(module_name="", items=[])
    
    def _parse_module_spec(self) -> ImportItem:
        """
        Parse a module specification and return as ImportItem.
        The ImportItem holds the module_name and alias for the module import.
        """
        # Read the qualified module name
        parts = [self._expect(TokenType.IDENTIFIER).value]
        while self._match(TokenType.DOT):
            self._advance()
            parts.append(self._expect(TokenType.IDENTIFIER).value)
        
        module_name = "::".join(parts)
        
        # Optional alias
        alias = None
        if self._match(TokenType.AS):
            self._advance()
            alias = self._expect(TokenType.IDENTIFIER).value
        
        # Optional selective import
        items = None
        if self._match(TokenType.LBRACE):
            self._advance()
            items = []
            while True:
                item_name = self._expect(TokenType.IDENTIFIER).value
                item_alias = None
                if self._match(TokenType.AS):
                    self._advance()
                    item_alias = self._expect(TokenType.IDENTIFIER).value
                items.append(ImportItem(item_name, item_alias))
                
                if self._match(TokenType.COMMA):
                    self._advance()
                else:
                    break
            self._expect(TokenType.RBRACE)
        
        # Return an ImportItem that holds the module spec
        # We repurpose ImportItem for module spec (it has same fields)
        return ImportItem(
            name=module_name,
            alias=alias,
            items=items  # Store selective items here
        )
    
    def _parse_export(self) -> ExportStmt:
        """Parse export statement"""
        self._expect(TokenType.EXPORT)
        
        items = []
        while True:
            item_name = self._expect(TokenType.IDENTIFIER).value
            item_alias = None
            if self._match(TokenType.AS):
                self._advance()
                item_alias = self._expect(TokenType.IDENTIFIER).value
            items.append(ExportItem(item_name, item_alias))
            
            if self._match(TokenType.COMMA):
                self._advance()
            else:
                break
        
        return ExportStmt(items=items)
    
    def _parse_func_decl(self) -> FuncDecl:
        """Parse function declaration: func name(params) => expr"""
        self._expect(TokenType.FUNC)
        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.LPAREN)
        
        params = []
        if not self._match(TokenType.RPAREN):
            while True:
                param_name = self._expect(TokenType.IDENTIFIER).value
                param_type = None
                if self._match(TokenType.COLON):
                    self._advance()
                    param_type = self._parse_type()
                params.append(Param(param_name, param_type))
                
                if self._match(TokenType.COMMA):
                    self._advance()
                else:
                    break
        
        self._expect(TokenType.RPAREN)
        
        # Optional return type annotation
        return_type = None
        if self._match(TokenType.ARROW):
            self._advance()
            return_type = self._parse_type()
        
        self._expect(TokenType.ASSIGN)  # =
        body = self._parse_expr()
        
        return FuncDecl(
            name=name,
            params=params,
            body=body,
            return_type=return_type
        )
    
    def _parse_let_decl(self) -> LetDecl:
        """Parse let declaration: let name = expr and name = expr in body"""
        self._expect(TokenType.LET)
        
        bindings = []
        while True:
            name = self._expect(TokenType.IDENTIFIER).value
            self._expect(TokenType.ASSIGN)
            expr = self._parse_expr()
            bindings.append(LetBinding(name, expr))
            
            if self._match(TokenType.AND):
                self._advance()
            else:
                break
        
        self._expect(TokenType.IN)
        body = self._parse_expr()
        
        return LetDecl(
            bindings=bindings,
            body=body
        )
    
    def _parse_type_decl(self) -> TypeDecl:
        """Parse type declaration: type Name = TypeExpr"""
        self._expect(TokenType.TYPE)
        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.ASSIGN)
        type_expr = self._parse_type()
        
        return TypeDecl(
            name=name,
            type_expr=type_expr
        )
    
    def _parse_type(self) -> Type:
        """Parse type expression"""
        if self._match(TokenType.IDENTIFIER):
            name = self.current_token.value
            self._advance()
            
            # Check for generic arguments
            args = []
            if self._match(TokenType.LBRACKET):
                self._advance()
                args.append(self._parse_type())
                while self._match(TokenType.COMMA):
                    self._advance()
                    args.append(self._parse_type())
                self._expect(TokenType.RBRACKET)
            
            return NamedType(name=name, args=args if args else [])
        elif self._match(TokenType.LPAREN):
            self._advance()
            typ = self._parse_type()
            self._expect(TokenType.RPAREN)
            return typ
        else:
            raise ParseError(f"Unexpected token in type: {self.current_token.token_type.name}",
                           self.current_token)
    
    def _parse_expr(self) -> Expr:
        """Parse expression (simplified for prototype)"""
        # For now, handle a few basic cases
        # Full parser would have proper precedence climbing
        
        if self._match(TokenType.INT):
            token = self.current_token
            self._advance()
            return IntLiteral(int(token.value))
        elif self._match(TokenType.FLOAT):
            token = self.current_token
            self._advance()
            return FloatLiteral(float(token.value))
        elif self._match(TokenType.STRING):
            token = self.current_token
            self._advance()
            return StringLiteral(token.value)
        elif self._match(TokenType.TRUE):
            self._advance()
            return BoolLiteral(True)
        elif self._match(TokenType.FALSE):
            self._advance()
            return BoolLiteral(False)
        elif self._match(TokenType.IDENTIFIER):
            token = self.current_token
            self._advance()
            return Identifier(token.value)
        elif self._match(TokenType.LPAREN):
            return self._parse_paren_expr()
        elif self._match(TokenType.FUNC):
            return self._parse_lambda()
        else:
            raise ParseError(f"Unexpected token in expression: {self.current_token.token_type.name}",
                           self.current_token)
    
    def _parse_paren_expr(self) -> Expr:
        """Parse parenthesized expression"""
        self._expect(TokenType.LPAREN)
        expr = self._parse_expr()
        self._expect(TokenType.RPAREN)
        return expr
    
    def _parse_lambda(self) -> Lambda:
        """Parse lambda expression"""
        self._expect(TokenType.FUNC)
        # Simplified: func(x: int) => expr or x => expr
        if self._match(TokenType.LPAREN):
            self._advance()
            param_name = self._expect(TokenType.IDENTIFIER).value
            param_type = None
            if self._match(TokenType.COLON):
                self._advance()
                param_type = self._parse_type()
            self._expect(TokenType.RPAREN)
        else:
            # Shorthand: x => expr
            param_name = self._expect(TokenType.IDENTIFIER).value
            param_type = None
        
        self._expect(TokenType.ARROW)
        body = self._parse_expr()
        
        return Lambda(
            param=Param(param_name, param_type),
            body=body
        )


def parse(source: str) -> Any:
    """Parse source code into AST"""
    from .lexer import tokenize
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse()
