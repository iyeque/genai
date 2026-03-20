"""
ALGOL 26 Lexer

Simple lexer implementation with tokenization.
Supports keywords, identifiers, literals, and operators.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
import re


class TokenType(Enum):
    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    IDENTIFIER = auto()
    
    # Keywords
    MODULE = auto()
    IMPORT = auto()
    EXPORT = auto()
    AS = auto()
    FUNC = auto()
    LET = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    MATCH = auto()
    TYPE = auto()
    TRUE = auto()
    FALSE = auto()
    RETURN = auto()
    
    # Symbols
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    COMMA = auto()       # ,
    DOT = auto()        # .
    DOTDOT = auto()     # ..
    COLON = auto()      # :
    SEMICOLON = auto()  # ;
    ASSIGN = auto()     # =
    ARROW = auto()      # ->
    PIPE = auto()       # |
    PLUS = auto()       # +
    MINUS = auto()      # -
    STAR = auto()       # *
    SLASH = auto()      # /
    EQ = auto()         # ==
    NEQ = auto()        # !=
    LT = auto()         # <
    GT = auto()         # >
    LE = auto()         # <=
    GE = auto()         # >=
    AND = auto()        # &&
    OR = auto()         # ||
    NOT = auto()        # !
    
    # Special
    NEWLINE = auto()
    EOF = auto()
    ERROR = auto()


@dataclass(frozen=True)
class Token:
    """Token with type, value, and position"""
    token_type: TokenType
    value: str
    line: int
    column: int
    
    def __repr__(self) -> str:
        return f"Token({self.token_type.name}, '{self.value}', line={self.line}, col={self.column})"


class Lexer:
    """
    Simple lexer for ALGOL 26.
    Tokenizes source code into Token stream.
    """
    
    KEYWORDS = {
        'module': TokenType.MODULE,
        'import': TokenType.IMPORT,
        'export': TokenType.EXPORT,
        'as': TokenType.AS,
        'func': TokenType.FUNC,
        'let': TokenType.LET,
        'if': TokenType.IF,
        'then': TokenType.THEN,
        'else': TokenType.ELSE,
        'while': TokenType.WHILE,
        'for': TokenType.FOR,
        'in': TokenType.IN,
        'match': TokenType.MATCH,
        'type': TokenType.TYPE,
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        'return': TokenType.RETURN,
    }
    
    # Single-character symbols
    SINGLE_CHAR_TOKENS = {
        '(': TokenType.LPAREN,
        ')': TokenType.RPAREN,
        '{': TokenType.LBRACE,
        '}': TokenType.RBRACE,
        '[': TokenType.LBRACKET,
        ']': TokenType.RBRACKET,
        ',': TokenType.COMMA,
        '.': TokenType.DOT,
        ':': TokenType.COLON,
        ';': TokenType.SEMICOLON,
        '=': TokenType.ASSIGN,
        '|': TokenType.PIPE,
        '+': TokenType.PLUS,
        '-': TokenType.MINUS,
        '*': TokenType.STAR,
        '/': TokenType.SLASH,
        '!': TokenType.NOT,
    }
    
    # Two-character symbols
    TWO_CHAR_TOKENS = {
        '..': TokenType.DOTDOT,
        '->': TokenType.ARROW,
        '==': TokenType.EQ,
        '!=': TokenType.NEQ,
        '<=': TokenType.LE,
        '>=': TokenType.GE,
        '&&': TokenType.AND,
        '||': TokenType.OR,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def tokenize(self) -> List[Token]:
        """Tokenize the entire source code"""
        while self.pos < len(self.source):
            token = self._next_token()
            if token:
                self.tokens.append(token)
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens
    
    def _next_token(self) -> Optional[Token]:
        """Get next token from source"""
        # Skip whitespace (including newlines)
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch.isspace():
                if ch == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1
            else:
                break
        
        if self.pos >= len(self.source):
            return None
        
        # Record starting position for this token
        start_line = self.line
        start_col = self.column
        ch = self.source[self.pos]
        
        # Check two-character tokens
        if self.pos + 1 < len(self.source):
            two_char = self.source[self.pos:self.pos+2]
            if two_char in self.TWO_CHAR_TOKENS:
                self.pos += 2
                self.column += 2
                return Token(self.TWO_CHAR_TOKENS[two_char], two_char, start_line, start_col)
        
        # Single-character tokens
        if ch in self.SINGLE_CHAR_TOKENS:
            self.pos += 1
            self.column += 1
            return Token(self.SINGLE_CHAR_TOKENS[ch], ch, start_line, start_col)
        
        # Identifier or keyword
        if ch.isalpha() or ch == '_':
            return self._read_identifier(start_line, start_col)
        
        # Number
        if ch.isdigit():
            return self._read_number(start_line, start_col)
        
        # String
        if ch == '"' or ch == "'":
            return self._read_string(start_line, start_col)
        
        # Unknown character
        self.pos += 1
        self.column += 1
        return Token(TokenType.ERROR, ch, start_line, start_col)
    
    def _read_identifier(self, line: int, col: int) -> Token:
        """Read an identifier or keyword"""
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self.pos += 1
            self.column += 1
        
        text = self.source[start:self.pos]
        token_type = self.KEYWORDS.get(text, TokenType.IDENTIFIER)
        return Token(token_type, text, line, col)
    
    def _read_number(self, line: int, col: int) -> Token:
        """Read numeric literal (int or float)"""
        start = self.pos
        
        # Integer part
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self.pos += 1
            self.column += 1
        
        # Fractional part?
        if self.pos < len(self.source) and self.source[self.pos] == '.':
            # Check if it's a float (look ahead for digit)
            if self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit():
                self.pos += 1
                self.column += 1
                while self.pos < len(self.source) and self.source[self.pos].isdigit():
                    self.pos += 1
                    self.column += 1
                num_str = self.source[start:self.pos]
                return Token(TokenType.FLOAT, num_str, line, col)
        
        num_str = self.source[start:self.pos]
        return Token(TokenType.INT, num_str, line, col)
    
    def _read_string(self, line: int, col: int) -> Token:
        """Read string literal"""
        quote = self.source[self.pos]
        self.pos += 1
        self.column += 1
        start = self.pos
        
        while self.pos < len(self.source) and self.source[self.pos] != quote:
            if self.source[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
        
        if self.pos >= len(self.source):
            # Unterminated string
            text = self.source[start:self.pos]
            self.pos += 1
            self.column += 1
            return Token(TokenType.ERROR, text, line, col)
        
        text = self.source[start:self.pos]
        self.pos += 1
        self.column += 1
        return Token(TokenType.STRING, text, line, col)


def tokenize(source: str) -> List[Token]:
    """Convenience function to tokenize source code"""
    lexer = Lexer(source)
    return lexer.tokenize()
