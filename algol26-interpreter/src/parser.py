"""
ALGOL 26 Parser

Recursive descent parser with Pratt parsing for expressions.
Based on GRAMMAR_BNF.md.
"""

from src.lexer import Lexer, Token, TokenType
from src.ast import (
    ASTNode, Program, Expr, Stmt,
    LiteralExpr, IdentifierExpr, BinaryOpExpr, UnaryOpExpr, CallExpr,
    ArrayIndexExpr, RecordAccessExpr, ArrayConstructorExpr, RecordConstructorExpr,
    ParenExpr, TernaryExpr, ProbExpr, SampleExpr,
    VarDeclStmt, ConstDeclStmt, TypeDeclStmt, AssignmentStmt, ProcCallStmt,
    IfStmt, WhileStmt, ForStmt, ReturnStmt, BlockStmt, ExprStmt, SkipStmt, AssertStmt,
    ProbBlockStmt, CausalBlockStmt, VerifyBlockStmt, ProbBindStmt,
    ProbBlockExpr, GivenExpr,
    ImportStmt, ExportStmt, ModuleDeclStmt,
    ProcDeclStmt, Param,
)
from src.type_system import Type, PrimitiveType, ArrayType, RecordType, FunctionType, TypeName, VOID_TYPE
from typing import List, Optional, Dict, Any


class ParserError(Exception):
    def __init__(self, message, token):
        super().__init__(f"{message} at line {token.line}, column {token.column}")
        self.token = token


class Parser:
    # Operator precedence for Pratt parsing (higher number = higher precedence)
    PRECEDENCE = {
        TokenType.OR: 1,
        TokenType.AND: 2,
        TokenType.GIVEN: 1,  # conditioning operator, very low precedence
        TokenType.EQ: 3, TokenType.NEQ: 3, TokenType.LT: 3, TokenType.LTE: 3, TokenType.GT: 3, TokenType.GTE: 3,
        TokenType.PLUS: 4, TokenType.MINUS: 4,
        TokenType.STAR: 5, TokenType.SLASH: 5, TokenType.PERCENT: 5,
        TokenType.CARET: 6,  # exponentiation, right-associative
        TokenType.DOT: 7,  # member access
        TokenType.LPAREN: 8,  # function call
        TokenType.LBRACKET: 8,  # array indexing
    }

    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.tokens = lexer.tokenize()
        self.pos = 0
        self.current_token = self.tokens[0] if self.tokens else None

    def error(self, message: str) -> ParserError:
        return ParserError(message, self.current_token)

    def advance(self):
        """Consume current token and move to next."""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = Token(TokenType.EOF, '', 0, 0)

    def expect(self, token_type: TokenType) -> Token:
        """Consume token of expected type or raise error."""
        if self.current_token.type == token_type:
            token = self.current_token
            self.advance()
            return token
        raise self.error(f"Expected token {token_type.name}, got {self.current_token.type.name}")

    def match(self, token_type: TokenType) -> bool:
        """Check if current token matches without consuming."""
        return self.current_token.type == token_type

    def peek(self) -> Optional[Token]:
        """Look ahead to next token without consuming."""
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return None

    def parse(self) -> Program:
        """Parse program: (declaration | statement)*"""
        declarations = []
        statements = []

        while not self.match(TokenType.EOF):
            # Determine if declaration or statement
            if self.current_token.type in (TokenType.VAR, TokenType.CONST, TokenType.TYPE, TokenType.PROC):
                decl = self.parse_declaration()
                declarations.append(decl)
            else:
                stmt = self.parse_statement()
                statements.append(stmt)

        return Program(declarations=declarations, statements=statements)

    def parse_declaration(self) -> Stmt:
        """Parse a top-level declaration."""
        t = self.current_token.type
        if t == TokenType.VAR:
            return self.parse_var_decl()
        elif t == TokenType.CONST:
            return self.parse_const_decl()
        elif t == TokenType.TYPE:
            return self.parse_type_decl()
        elif t == TokenType.PROC:
            return self.parse_proc_decl()
        else:
            raise self.error(f"Unexpected token {t.name} in declaration")

    def parse_var_decl(self) -> VarDeclStmt:
        """var identifier : type? = expr ;"""
        token = self.expect(TokenType.VAR)
        name = self.expect(TokenType.IDENT).value

        type_annot = None
        if self.match(TokenType.COLON):
            self.advance()
            type_annot = self.parse_type_annotation()

        init_expr = None
        if self.match(TokenType.ASSIGN):
            self.advance()
            init_expr = self.parse_expression()

        self.expect(TokenType.SEMI)
        return VarDeclStmt(name=name, type_annot=type_annot, init_expr=init_expr, token=token)

    def parse_const_decl(self) -> ConstDeclStmt:
        """const identifier : type = expr ;"""
        token = self.expect(TokenType.CONST)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)
        type_annot = self.parse_type_annotation()
        self.expect(TokenType.ASSIGN)
        init_expr = self.parse_expression()
        self.expect(TokenType.SEMI)
        return ConstDeclStmt(name=name, type_annot=type_annot, init_expr=init_expr, token=token)

    def parse_type_decl(self) -> TypeDeclStmt:
        """type identifier = type ;"""
        token = self.expect(TokenType.TYPE)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.ASSIGN)
        type_annot = self.parse_type_annotation()
        self.expect(TokenType.SEMI)
        return TypeDeclStmt(name=name, type_annot=type_annot)

    def parse_type_annotation(self) -> Type:
        """Parse a type annotation (used in var/const/type/proc)."""
        t = self.current_token.type
        if t in (TokenType.INT, TokenType.REAL_TYPE, TokenType.BOOL, TokenType.CHAR_TYPE, TokenType.STRING_TYPE, TokenType.BYTE_TYPE, TokenType.VOID):
            name = self.current_token.value
            self.advance()
            return PrimitiveType(name)
        elif t == TokenType.ARRAY:
            self.advance()
            self.expect(TokenType.LBRACKET)
            size_expr = self.parse_expression()
            self.expect(TokenType.RBRACKET)
            self.expect(TokenType.OF)
            element_type = self.parse_type_annotation()
            return ArrayType(element_type, size_expr)
        elif t == TokenType.RECORD:
            self.advance()
            self.expect(TokenType.LBRACE)
            fields = self.parse_record_fields()
            self.expect(TokenType.RBRACE)
            return RecordType(fields)
        elif t == TokenType.PROC:
            self.advance()
            self.expect(TokenType.LPAREN)
            params = self.parse_param_list() if not self.match(TokenType.RPAREN) else []
            self.expect(TokenType.RPAREN)
            return_type = None
            if self.match(TokenType.FAT_ARROW):
                self.advance()
                return_type = self.parse_type_annotation()
            ret_type = return_type if return_type is not None else VOID_TYPE
            return FunctionType([p.type_annot for p in params], ret_type)
        elif t == TokenType.IDENT:
            name = self.current_token.value
            self.advance()
            return TypeName(name)
        else:
            raise self.error(f"Unexpected token in type annotation: {t.name}")

    def parse_record_fields(self) -> Dict[str, Type]:
        fields = {}
        if self.match(TokenType.RBRACE):
            return fields  # empty record
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)
        field_type = self.parse_type_annotation()
        fields[name] = field_type
        while self.match(TokenType.COMMA):
            self.advance()
            name = self.expect(TokenType.IDENT).value
            self.expect(TokenType.COLON)
            field_type = self.parse_type_annotation()
            fields[name] = field_type
        return fields

    def parse_param_list(self) -> List[Param]:
        params = []
        if not self.match(TokenType.RPAREN):
            params.append(self.parse_param())
            while self.match(TokenType.COMMA):
                self.advance()
                params.append(self.parse_param())
        return params

    def parse_param(self) -> Param:
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)
        type_annot = self.parse_type_annotation()
        is_ref = False
        # Could support 'ref' keyword before name? BNF doesn't show.
        return Param(name=name, type_annot=type_annot, is_ref=is_ref)

    def parse_proc_decl(self) -> ProcDeclStmt:
        token = self.expect(TokenType.PROC)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list() if not self.match(TokenType.RPAREN) else []
        self.expect(TokenType.RPAREN)

        return_type = None
        if self.match(TokenType.FAT_ARROW):
            self.advance()
            return_type = self.parse_type_annotation()

        if self.match(TokenType.EQ):
            self.advance()
            body = self.parse_expression()
            self.expect(TokenType.SEMI)
        else:
            body = self.parse_block()

        return ProcDeclStmt(name=name, params=params, return_type=return_type, body=body)

    def parse_statement(self) -> Stmt:
        t = self.current_token.type

        if t == TokenType.VAR:
            return self.parse_var_decl()
        elif t == TokenType.CONST:
            return self.parse_const_decl()
        elif t == TokenType.BEGIN:
            return self.parse_block()
        elif t == TokenType.IF:
            return self.parse_if_stmt()
        elif t == TokenType.WHILE:
            return self.parse_while_stmt()
        elif t == TokenType.FOR:
            return self.parse_for_stmt()
        elif t == TokenType.RETURN or t == TokenType.RESULT:
            return self.parse_return_stmt()
        elif t == TokenType.SKIP:
            self.advance()
            self.expect(TokenType.SEMI)
            return SkipStmt()
        elif t == TokenType.ASSERT:
            return self.parse_assert_stmt()
        elif t == TokenType.CAUSAL:
            return self.parse_causal_block()
        elif t == TokenType.VERIFY:
            return self.parse_verify_block()
        elif t == TokenType.MODULE:
            return self.parse_module_decl()
        elif t == TokenType.IMPORT:
            return self.parse_import_stmt()
        elif t == TokenType.EXPORT:
            return self.parse_export_stmt()
        elif t in (TokenType.IDENT, TokenType.PRINTLN):
            # Probabilistic binding: identifier ':' expression
            if t == TokenType.IDENT and self.peek() and self.peek().type == TokenType.COLON:
                return self.parse_prob_bind()
            return self.parse_expression_statement()
        elif t == TokenType.PROC:
            raise self.error("Unexpected proc keyword in statement context (proc declarations are top-level only)")
        else:
            raise self.error(f"Unexpected token {t.name} in statement")

    def parse_module_decl(self) -> ModuleDeclStmt:
        token = self.expect(TokenType.MODULE)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.SEMI)
        return ModuleDeclStmt(name=name, token=token)

    def parse_import_stmt(self) -> ImportStmt:
        token = self.expect(TokenType.IMPORT)
        # Parse module path: one or more IDENT separated by '.'
        parts = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.DOT):
            # Check if there is an IDENT after the dot (to avoid consuming dot for selective import)
            next_tok = self.peek()
            if next_tok is not None and next_tok.type == TokenType.IDENT:
                self.advance()  # consume DOT
                parts.append(self.expect(TokenType.IDENT).value)
            else:
                break
        module_name = '.'.join(parts)

        alias = None
        names = None

        # Selective import with dot: import M.{a,b} or direct brace after module
        if self.match(TokenType.DOT):
            self.advance()
            self.expect(TokenType.LBRACE)
            names = []
            if not self.match(TokenType.RBRACE):
                names.append(self.expect(TokenType.IDENT).value)
                while self.match(TokenType.COMMA):
                    self.advance()
                    names.append(self.expect(TokenType.IDENT).value)
            self.expect(TokenType.RBRACE)
        elif self.match(TokenType.LBRACE):
            # Direct selective without dot (allowed)
            self.advance()
            names = []
            if not self.match(TokenType.RBRACE):
                names.append(self.expect(TokenType.IDENT).value)
                while self.match(TokenType.COMMA):
                    self.advance()
                    names.append(self.expect(TokenType.IDENT).value)
            self.expect(TokenType.RBRACE)
        elif self.match(TokenType.AS):
            self.advance()
            alias = self.expect(TokenType.IDENT).value

        self.expect(TokenType.SEMI)
        return ImportStmt(module_name=module_name, alias=alias, names=names, token=token)

    def parse_export_stmt(self) -> ExportStmt:
        token = self.expect(TokenType.EXPORT)
        names = []
        if not self.match(TokenType.SEMI):
            names.append(self.expect(TokenType.IDENT).value)
            while self.match(TokenType.COMMA):
                self.advance()
                names.append(self.expect(TokenType.IDENT).value)
        self.expect(TokenType.SEMI)
        return ExportStmt(names=names, token=token)

    def parse_block(self) -> BlockStmt:
        self.expect(TokenType.BEGIN)
        statements = []
        while not self.match(TokenType.END) and not self.match(TokenType.EOF):
            statements.append(self.parse_statement())
        self.expect(TokenType.END)
        return BlockStmt(statements=statements)

    def parse_if_stmt(self) -> IfStmt:
        self.expect(TokenType.IF)
        condition = self.parse_expression()
        self.expect(TokenType.THEN)
        then_branch = self.parse_statement()
        else_branch = None
        if self.match(TokenType.ELSE):
            self.advance()
            else_branch = self.parse_statement()
        self.expect(TokenType.FI)
        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch)

    def parse_while_stmt(self) -> WhileStmt:
        self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        self.expect(TokenType.DO)
        body = self.parse_statement()
        self.expect(TokenType.OD)
        return WhileStmt(condition=condition, body=body)

    def parse_for_stmt(self) -> ForStmt:
        self.expect(TokenType.FOR)
        iterator = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)
        start = self.parse_expression()
        self.expect(TokenType.TO)
        end = self.parse_expression()
        step = None
        if self.match(TokenType.STEP):
            self.advance()
            step = self.parse_expression()
        self.expect(TokenType.DO)
        body = self.parse_statement()
        return ForStmt(iterator=iterator, start=start, end=end, step=step, body=body, direction='to')

    def parse_return_stmt(self) -> ReturnStmt:
        if self.match(TokenType.RETURN):
            self.advance()
            value = self.parse_expression()
            self.expect(TokenType.SEMI)
            return ReturnStmt(value=value)
        elif self.match(TokenType.RESULT):
            self.advance()
            self.expect(TokenType.ASSIGN)
            value = self.parse_expression()
            self.expect(TokenType.SEMI)
            return ReturnStmt(value=value)
        else:
            raise self.error("Expected return or result")

    def parse_assert_stmt(self) -> AssertStmt:
        self.expect(TokenType.ASSERT)
        condition = self.parse_expression()
        self.expect(TokenType.SEMI)
        return AssertStmt(condition=condition)

    def parse_prob_bind(self) -> ProbBindStmt:
        # Syntax: identifier ':' expression ';'
        name = self.current_token.value
        self.advance()  # consume IDENT
        self.expect(TokenType.COLON)
        dist_expr = self.parse_expression()
        self.expect(TokenType.SEMI)
        return ProbBindStmt(identifier=name, distribution=dist_expr)

    def parse_prob_block(self) -> ProbBlockStmt:
        self.expect(TokenType.PROB)
        statements = self._parse_brace_block()
        return ProbBlockStmt(statements=statements)

    def parse_causal_block(self) -> CausalBlockStmt:
        self.expect(TokenType.CAUSAL)
        statements = self._parse_brace_block()
        return CausalBlockStmt(statements=statements)

    def parse_verify_block(self) -> VerifyBlockStmt:
        self.expect(TokenType.VERIFY)
        condition = self.parse_expression()
        message = None
        if self.match(TokenType.STRING):
            message = self.current_token.value
            self.advance()
        self.expect(TokenType.SEMI)
        return VerifyBlockStmt(condition=condition, message=message)

    def parse_expression_statement(self) -> Stmt:
        expr = self.parse_expression()
        self.expect(TokenType.SEMI)
        return ExprStmt(expr=expr)

    # Pratt parser for expressions
    def parse_expression(self, min_prec: int = 0) -> Expr:
        expr = self.parse_primary()

        while True:
            token = self.current_token
            if token.type not in self.PRECEDENCE or self.PRECEDENCE[token.type] < min_prec:
                break

            prec = self.PRECEDENCE[token.type]
            if token.type == TokenType.CARET:
                next_min = prec
            else:
                next_min = prec + 1

            self.advance()
            if token.type in (TokenType.LPAREN, TokenType.LBRACKET):
                if token.type == TokenType.LPAREN:
                    args = self.parse_argument_list() if not self.match(TokenType.RPAREN) else []
                    self.expect(TokenType.RPAREN)
                    expr = CallExpr(callee=expr, args=args)
                elif token.type == TokenType.LBRACKET:
                    index = self.parse_expression()
                    self.expect(TokenType.RBRACKET)
                    expr = ArrayIndexExpr(array=expr, index=index)
                continue
            else:
                right = self.parse_expression(next_min)
                expr = BinaryOpExpr(left=expr, op=token, right=right)

        return expr

    def parse_primary(self) -> Expr:
        t = self.current_token.type

        # Literals
        if t in (TokenType.INTEGER, TokenType.REAL, TokenType.CHAR, TokenType.STRING):
            token = self.current_token
            self.advance()
            return LiteralExpr(value=token.value, token=token)
        if t == TokenType.TRUE or t == TokenType.FALSE:
            token = self.current_token
            self.advance()
            return LiteralExpr(value=token.value, token=token)
        if t == TokenType.NULL:
            token = self.current_token
            self.advance()
            return LiteralExpr(value=None, token=token)

        # Probabilistic block expression
        if t == TokenType.PROB:
            self.advance()
            statements = self._parse_brace_block()
            return ProbBlockExpr(statements=statements)

        # Identifier or record constructor
        if t in (TokenType.IDENT, TokenType.PRINTLN):
            next_tok = self.peek()
            if next_tok and next_tok.type == TokenType.LBRACE:
                # Record constructor: TypeName { field: expr, ... }
                type_name = self.current_token.value
                self.advance()  # consume IDENT
                return self.parse_record_constructor(type_name)
            else:
                token = self.current_token
                self.advance()
                expr = IdentifierExpr(name=token.value, token=token)
                while True:
                    if self.match(TokenType.LPAREN):
                        self.advance()
                        args = self.parse_argument_list() if not self.match(TokenType.RPAREN) else []
                        self.expect(TokenType.RPAREN)
                        expr = CallExpr(callee=expr, args=args)
                    elif self.match(TokenType.LBRACKET):
                        self.advance()
                        index = self.parse_expression()
                        self.expect(TokenType.RBRACKET)
                        expr = ArrayIndexExpr(array=expr, index=index)
                    elif self.match(TokenType.DOT):
                        self.advance()
                        if not self.match(TokenType.IDENT):
                            raise self.error("Expected identifier after '.'")
                        field = self.current_token.value
                        self.advance()
                        expr = RecordAccessExpr(record=expr, field=field, token=self.current_token)
                    else:
                        break
                return expr

        # Parenthesized expression
        if t == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return ParenExpr(expr=expr)

        # Unary operators
        if t in (TokenType.MINUS, TokenType.NOT, TokenType.AMP, TokenType.STAR):
            token = self.current_token
            self.advance()
            operand = self.parse_primary()
            return UnaryOpExpr(op=token, operand=operand)

        # Array constructor: [ expr, ... ]
        if t == TokenType.LBRACKET:
            self.advance()
            elements = []
            if not self.match(TokenType.RBRACKET):
                elements.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    self.advance()
                    elements.append(self.parse_expression())
            self.expect(TokenType.RBRACKET)
            return ArrayConstructorExpr(elements=elements)

        raise self.error(f"Unexpected token {t.name} in primary expression")

    def parse_record_constructor(self, type_name: str) -> RecordConstructorExpr:
        """Parse record constructor: TypeName { field: expr, ... } (assumes LBRACE not yet consumed)"""
        self.expect(TokenType.LBRACE)
        field_values = {}
        if not self.match(TokenType.RBRACE):
            field_name = self.expect(TokenType.IDENT).value
            self.expect(TokenType.COLON)
            value_expr = self.parse_expression()
            field_values[field_name] = value_expr
            while self.match(TokenType.COMMA):
                self.advance()
                field_name = self.expect(TokenType.IDENT).value
                self.expect(TokenType.COLON)
                value_expr = self.parse_expression()
                field_values[field_name] = value_expr
        self.expect(TokenType.RBRACE)
        return RecordConstructorExpr(type_name=type_name, field_values=field_values)

    def parse_argument_list(self) -> List[Expr]:
        args = []
        if not self.match(TokenType.RPAREN):
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                self.advance()
                args.append(self.parse_expression())
        return args

    def _parse_brace_block(self) -> List[Stmt]:
        """Parse a block enclosed in { } (used by prob and causal blocks)."""
        self.expect(TokenType.LBRACE)
        statements = []
        while not self.match(TokenType.RBRACE) and not self.match(TokenType.EOF):
            statements.append(self.parse_statement())
        self.expect(TokenType.RBRACE)
        return statements
