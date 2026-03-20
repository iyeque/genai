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
    ProcDeclStmt, Param, ProbBlockStmt, CausalBlockStmt, VerifyBlockStmt,
    RecordTypeDef, FieldDef, ArrayTypeDef, ProcTypeDef,
)
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

    def parse(self) -> Program:
        """Parse program: (declaration)* statement*"""
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
        """var identifier : typeName [ = expr ] ;"""
        token = self.expect(TokenType.VAR)
        name = self.expect(TokenType.IDENT).value

        # Optional type annotation
        type_name = None
        if self.match(TokenType.COLON):
            self.advance()
            type_name = self.parse_type_name()

        # Optional initializer
        init_expr = None
        if self.match(TokenType.ASSIGN):
            self.advance()
            init_expr = self.parse_expression()

        self.expect(TokenType.SEMI)
        return VarDeclStmt(name=name, type_name=type_name, init_expr=init_expr, token=token)

    def parse_const_decl(self) -> ConstDeclStmt:
        """const identifier : typeName = expr ;"""
        token = self.expect(TokenType.CONST)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)
        type_name = self.parse_type_name()
        self.expect(TokenType.ASSIGN)
        init_expr = self.parse_expression()
        self.expect(TokenType.SEMI)
        return ConstDeclStmt(name=name, type_name=type_name, init_expr=init_expr)

    def parse_type_decl(self) -> TypeDeclStmt:
        """type identifier = typeDef ;"""
        token = self.expect(TokenType.TYPE)
        name = self.expect(TokenType.IDENT).value
        # In BNF, it's 'type identifier = typeName' but for records/arrays we need typeDef
        # We'll treat it as type identifier = typeDef where typeDef can be primitive or composite
        self.expect(TokenType.ASSIGN)
        type_def = self.parse_type_def()
        self.expect(TokenType.SEMI)
        return TypeDeclStmt(name=name, type_def=type_def)

    def parse_type_def(self) -> TypeDef:
        """Parse a type definition (primitive, array, record, proc)"""
        t = self.current_token.type
        if t == TokenType.INT:
            self.advance()
            return None  # Primitive types no explicit def needed, we'll handle inline
        elif t == TokenType.REAL_TYPE:
            self.advance()
            return None
        elif t == TokenType.BOOL:
            self.advance()
            return None
        elif t == TokenType.CHAR_TYPE:
            self.advance()
            return None
        elif t == TokenType.STRING_TYPE:
            self.advance()
            return None
        elif t == TokenType.ARRAY:
            return self.parse_array_type_def()
        elif t == TokenType.RECORD:
            return self.parse_record_type_def()
        elif t == TokenType.PROC:
            return self.parse_proc_type_def()
        elif t == TokenType.IDENT:
            # User-defined type alias
            name = self.current_token.value
            self.advance()
            return None  # We'll handle as alias by name
        else:
            raise self.error(f"Unexpected token in type definition: {t.name}")

    def parse_array_type_def(self) -> ArrayTypeDef:
        """array [ expr ] of typeName"""
        token = self.expect(TokenType.ARRAY)
        self.expect(TokenType.LBRACKET)
        size_expr = self.parse_expression()  # In MVP should be constant integer
        self.expect(TokenType.RBRACKET)
        self.expect(TokenType.OF)
        element_type = self.parse_type_name()
        return ArrayTypeDef(size=size_expr, element_type=element_type)

    def parse_record_type_def(self) -> RecordTypeDef:
        """record { fieldList }"""
        token = self.expect(TokenType.RECORD)
        self.expect(TokenType.LBRACE)
        fields = []
        if not self.match(TokenType.RBRACE):
            fields.append(self.parse_field_def())
            while self.match(TokenType.COMMA):
                self.advance()
                fields.append(self.parse_field_def())
        self.expect(TokenType.RBRACE)
        return RecordTypeDef(fields=fields)

    def parse_field_def(self) -> FieldDef:
        """identifier : typeName"""
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)
        type_name = self.parse_type_name()
        return FieldDef(name=name, type_name=type_name)

    def parse_proc_type_def(self) -> ProcTypeDef:
        """proc ( paramList ) => typeName"""
        token = self.expect(TokenType.PROC)
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list() if not self.match(TokenType.RPAREN) else []
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.FAT_ARROW)  # => for proc return type
        return_type = self.parse_type_name()
        return ProcTypeDef(params=params, return_type=return_type)

    def parse_proc_decl(self) -> ProcDeclStmt:
        """proc identifier ( [paramList] ) [=> typeName] = expr ; OR block"""
        token = self.expect(TokenType.PROC)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list() if not self.match(TokenType.RPAREN) else []
        self.expect(TokenType.RPAREN)

        # Optional return type with =>
        return_type = None
        if self.match(TokenType.FAT_ARROW):
            self.advance()
            return_type = self.parse_type_name()

        # Body: either expression form or block
        if self.match(TokenType.EQ):
            self.advance()
            body = self.parse_expression()
            self.expect(TokenType.SEMI)
        else:
            body = self.parse_block()

        return ProcDeclStmt(name=name, params=params, return_type=return_type, body=body)

    def parse_param_list(self) -> List[Param]:
        """param { , param }"""
        params = []
        if not self.match(TokenType.RPAREN):
            params.append(self.parse_param())
            while self.match(TokenType.COMMA):
                self.advance()
                params.append(self.parse_param())
        return params

    def parse_param(self) -> Param:
        """identifier : typeName"""
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)
        type_name = self.parse_type_name()
        # Check for 'ref' keyword before name? In BNF it's just identifier:typeName, but ownership may have 'ref' prefix.
        # In lexical spec, 'ref' is a keyword. In param, it could be: ref identifier:typeName. BNF doesn't show that.
        # For simplicity, MVP: no ref keyword in param list; all passed by value (or by reference for arrays/records naturally)
        return Param(name=name, type_name=type_name)

    def parse_type_name(self) -> str:
        """Parse a type name (primitive or composite)"""
        t = self.current_token.type
        if t in (TokenType.INT, TokenType.REAL_TYPE, TokenType.BOOL, TokenType.CHAR_TYPE,
                 TokenType.STRING_TYPE, TokenType.BYTE_TYPE, TokenType.VOID):
            name = self.current_token.value
            self.advance()
            return name
        elif t == TokenType.ARRAY:
            # array [ expr ] of typeName
            self.advance()
            self.expect(TokenType.LBRACKET)
            size_expr = self.parse_expression()
            self.expect(TokenType.RBRACKET)
            self.expect(TokenType.OF)
            element_type = self.parse_type_name()
            return f"array[{size_expr}][{element_type}]"
        elif t == TokenType.RECORD:
            self.advance()
            self.expect(TokenType.LBRACE)
            fields = []
            if not self.match(TokenType.RBRACE):
                fields.append(self.parse_field_def())
                while self.match(TokenType.COMMA):
                    self.advance()
                    fields.append(self.parse_field_def())
            self.expect(TokenType.RBRACE)
            # Return a special composite type string; later we'll resolve to a record def
            return f"record({','.join(f'{f.name}:{f.type_name}' for f in fields)})"
        elif t == TokenType.PROC:
            # proc ( paramList ) => typeName
            return self.parse_proc_type_def_as_string()
        elif t == TokenType.IDENT:
            # User-defined type alias
            name = self.current_token.value
            self.advance()
            # Could also refer to a record type defined earlier
            return name
        else:
            raise self.error(f"Unexpected token in type name: {t.name}")

    def parse_proc_type_def_as_string(self) -> str:
        """Parse proc type and return a string representation."""
        self.expect(TokenType.PROC)
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list() if not self.match(TokenType.RPAREN) else []
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.FAT_ARROW)  # =>
        return_type = self.parse_type_name()
        param_strs = ','.join(f"{p.name}:{p.type_name}" for p in params)
        return f"proc({param_strs})=>{return_type}"

    def parse_statement(self) -> Stmt:
        """Parse a statement."""
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
        elif t == TokenType.PROB:
            return self.parse_prob_block()
        elif t == TokenType.CAUSAL:
            return self.parse_causal_block()
        elif t == TokenType.VERIFY:
            return self.parse_verify_block()
        elif t in (TokenType.IDENT, TokenType.PRINTLN):
            # Could be assignment, proc call, or expression statement
            return self.parse_expression_statement()
        elif t == TokenType.PROC:
            # Inline proc lambda? BNF supports proc lambda. But at statement level, proc is a declaration, handled in top-level parse
            # So here we shouldn't see PROC unless it's expression lambda inside an expression
            # For simplicity, we treat it as parse_expression eventually
            raise self.error(f"Unexpected proc keyword in statement context")
        else:
            raise self.error(f"Unexpected token {t.name} in statement")

    def parse_block(self) -> BlockStmt:
        """begin statement* end"""
        self.expect(TokenType.BEGIN)
        statements = []
        while not self.match(TokenType.END) and not self.match(TokenType.EOF):
            statements.append(self.parse_statement())
        self.expect(TokenType.END)
        return BlockStmt(statements=statements)

    def parse_if_stmt(self) -> IfStmt:
        """if expr then statement [ else statement ] fi"""
        self.expect(TokenType.IF)
        condition = self.parse_expression()
        self.expect(TokenType.THEN)
        then_branch = self.parse_statement()
        else_branch = None
        if self.match(TokenType.ELSE):
            self.advance()
            else_branch = self.parse_statement()
        self.expect(TokenType.FI)  # ALGOL 68 style closing
        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch)

    def parse_while_stmt(self) -> WhileStmt:
        """while expr do statement od"""
        self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        self.expect(TokenType.DO)
        body = self.parse_statement()
        self.expect(TokenType.OD)
        return WhileStmt(condition=condition, body=body)

    def parse_for_stmt(self) -> ForStmt:
        """for identifier : expr to expr [step expr] do statement"""
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
        """return expr ; OR result := expr ;"""
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
        """assert expr ;"""
        self.expect(TokenType.ASSERT)
        condition = self.parse_expression()
        self.expect(TokenType.SEMI)
        return AssertStmt(condition=condition)

    def parse_prob_block(self) -> ProbBlockStmt:
        """prob { statement* }"""
        self.expect(TokenType.PROB)
        self.expect(TokenType.LBRACE)
        statements = []
        while not self.match(TokenType.RBRACE) and not self.match(TokenType.EOF):
            statements.append(self.parse_statement())
        self.expect(TokenType.RBRACE)
        return ProbBlockStmt(statements=statements)

    def parse_causal_block(self) -> CausalBlockStmt:
        """causal { statement* }"""
        self.expect(TokenType.CAUSAL)
        self.expect(TokenType.LBRACE)
        statements = []
        while not self.match(TokenType.RBRACE) and not self.match(TokenType.EOF):
            statements.append(self.parse_statement())
        self.expect(TokenType.RBRACE)
        return CausalBlockStmt(statements=statements)

    def parse_verify_block(self) -> VerifyBlockStmt:
        """verify expr ; OR verify expr "message" ;"""
        self.expect(TokenType.VERIFY)
        condition = self.parse_expression()
        message = None
        if self.match(TokenType.STRING):
            message = self.current_token.value
            self.advance()
        self.expect(TokenType.SEMI)
        return VerifyBlockStmt(condition=condition, message=message)

    def parse_expression_statement(self) -> Stmt:
        """Parse an expression followed by semicolon as a statement."""
        expr = self.parse_expression()
        self.expect(TokenType.SEMI)
        return ExprStmt(expr=expr)

    # Pratt parser for expressions
    def parse_expression(self, min_prec: int = 0) -> Expr:
        """Parse expression with precedence climbing."""
        expr = self.parse_primary()

        while True:
            # Check if next token is an infix operator with sufficient precedence
            token = self.current_token
            if token.type not in self.PRECEDENCE or self.PRECEDENCE[token.type] < min_prec:
                break

            # For right-associative operators (like ^), we adjust precedence
            prec = self.PRECEDENCE[token.type]
            if token.type == TokenType.CARET:  # right-associative
                next_min = prec
            else:
                next_min = prec + 1

            self.advance()
            # Handle operator
            if token.type in (TokenType.LPAREN, TokenType.LBRACKET):
                # Function call or array indexing - handled in primary, shouldn't come here
                # Actually after primary we could have call or index as part of primary's postfix
                # So these are not infix operators but part of expression completion; we should handle them in primary via nud/led pattern? 
                # Our current design: parse_primary returns primary expression; then while loop handles postfix operators.
                # I need to handle call and index here as postfix.
                if token.type == TokenType.LPAREN:
                    # Function call: expr ( args )
                    args = self.parse_argument_list() if not self.match(TokenType.RPAREN) else []
                    self.expect(TokenType.RPAREN)
                    expr = CallExpr(callee=expr, args=args)
                elif token.type == TokenType.LBRACKET:
                    # Array indexing: expr [ index ]
                    index = self.parse_expression()
                    self.expect(TokenType.RBRACKET)
                    expr = ArrayIndexExpr(array=expr, index=index)
                # Continue to next iteration to handle further chaining (e.g., f()[i])
                continue
            else:
                # Binary infix operator
                right = self.parse_expression(next_min)
                expr = BinaryOpExpr(left=expr, op=token, right=right)

        return expr

    def parse_primary(self) -> Expr:
        """Parse primary expression."""
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

        # Identifier or record constructor
        if t in (TokenType.IDENT, TokenType.PRINTLN):
            # Peek ahead to see if this is a record constructor: identifier followed by LBRACE
            next_tok = self.peek()
            if next_tok and next_tok.type == TokenType.LBRACE:
                # Record constructor: TypeName { field: expr, ... }
                type_name = self.current_token.value
                self.advance()  # consume IDENT
                return self.parse_record_constructor(type_name)
            else:
                # Normal identifier with optional postfix (call, index, access)
                token = self.current_token
                self.advance()
                expr = IdentifierExpr(name=token.value, token=token)
                # Postfix: function call, array indexing, record access
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
            operand = self.parse_primary()  # unary binds tightly
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
        """Parse comma-separated argument expressions."""
        args = []
        if not self.match(TokenType.RPAREN):
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                self.advance()
                args.append(self.parse_expression())
        return args

    def peek(self) -> str:
        """Look at next character in token stream (not token). Not needed? We can peek at next token."""
        # Actually we need to peek at next token's type/value
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return None
