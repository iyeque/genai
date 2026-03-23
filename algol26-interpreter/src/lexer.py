"""
ALGOL 26 Lexer

Implements lexical analysis for ALGOL 26 source code.
Token types based on LEXICAL_SYNTAX.md and GRAMMAR_BNF.md.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, List


class TokenType(Enum):
    # Identifiers and literals
    IDENT = auto()
    INTEGER = auto()
    REAL = auto()
    CHAR = auto()
    STRING = auto()
    BOOLEAN = auto()  # true/false

    # Keywords
    IF = auto()
    THEN = auto()
    ELSE = auto()
    FI = auto()
    WHILE = auto()
    DO = auto()
    OD = auto()
    FOR = auto()
    TO = auto()
    DOWNTO = auto()
    BY = auto()
    STEP = auto()
    BEGIN = auto()
    END = auto()
    PROC = auto()
    FUNC = auto()
    RETURN = auto()
    RESULT = auto()
    VAR = auto()
    CONST = auto()
    TYPE = auto()
    MODE = auto()
    REF = auto()
    OWN = auto()
    LET = auto()
    STRUCT = auto()
    UNION = auto()
    ENUM = auto()
    CLASS = auto()
    INTERFACE = auto()
    INT = auto()
    REAL_TYPE = auto()
    BOOL = auto()
    CHAR_TYPE = auto()
    STRING_TYPE = auto()
    BYTE_TYPE = auto()
    VOID = auto()
    ARRAY = auto()
    RECORD = auto()
    OF = auto()
    NULL = auto()
    TRUE = auto()
    FALSE = auto()
    NIL = auto()
    SELF = auto()
    SUPER = auto()
    THIS = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    XOR = auto()
    MOD = auto()
    DIV = auto()
    SKIP = auto()
    PRINTLN = auto()
    ASSERT = auto()
    # Advanced features
    PROB = auto()
    CAUSAL = auto()
    VERIFY = auto()
    GIVEN = auto()
    ASSUME = auto()
    REQUIRES = auto()
    ENSURES = auto()
    INVARIANT = auto()
    KERNEL = auto()
    # Concurrency
    ASYNC = auto()
    AWAIT = auto()
    CHAN = auto()
    ACTOR = auto()
    SELECT = auto()
    LOCK = auto()
    ATOMIC = auto()
    CONVERT = auto()
    # Modules
    MODULE = auto()
    IMPORT = auto()
    EXPORT = auto()
    FROM = auto()
    AS = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    CARET = auto()
    ASSIGN = auto()  # :=
    EQ = auto()
    NEQ = auto()  # <> or /=
    LT = auto()
    LTE = auto()
    GT = auto()
    GTE = auto()
    AND_OP = auto()  # &
    OR_OP = auto()   # |
    NOT_OP = auto()  # ~
    LSHIFT = auto()  # <<
    RSHIFT = auto()  # >>
    AMP = auto()     # &
    PIPE = auto()    # |
    TILDE = auto()   # ~
    # Structural
    COLON = auto()   # :
    DOT = auto()     # .
    DOTDOT = auto()  # ..
    ARROW = auto()   # ->
    FAT_ARROW = auto()  # =>
    DOUBLE_COLON = auto()  # ::
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    SEMI = auto()
    AT = auto()
    QUESTION = auto()
    EXCLAMATION = auto()

    # Special
    EOF = auto()
    ERROR = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', {self.line}:{self.column})"


class LexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


class Lexer:
    # Keywords mapping (lowercase)
    KEYWORDS = {
        # Control flow
        'if': TokenType.IF,
        'then': TokenType.THEN,
        'else': TokenType.ELSE,
        'fi': TokenType.FI,
        'while': TokenType.WHILE,
        'do': TokenType.DO,
        'od': TokenType.OD,
        'for': TokenType.FOR,
        'to': TokenType.TO,
        'downto': TokenType.DOWNTO,
        'by': TokenType.BY,
        'step': TokenType.STEP,
        'begin': TokenType.BEGIN,
        'end': TokenType.END,
        # Declarations
        'proc': TokenType.PROC,
        'func': TokenType.FUNC,
        'return': TokenType.RETURN,
        'result': TokenType.RESULT,
        'var': TokenType.VAR,
        'const': TokenType.CONST,
        'type': TokenType.TYPE,
        'mode': TokenType.MODE,
        'ref': TokenType.REF,
        'own': TokenType.OWN,
        'let': TokenType.LET,
        'struct': TokenType.STRUCT,
        'union': TokenType.UNION,
        'enum': TokenType.ENUM,
        'class': TokenType.CLASS,
        'interface': TokenType.INTERFACE,
        # Types
        'int': TokenType.INT,
        'real': TokenType.REAL_TYPE,
        'bool': TokenType.BOOL,
        'char': TokenType.CHAR_TYPE,
        'string': TokenType.STRING_TYPE,
        'byte': TokenType.BYTE_TYPE,
        'void': TokenType.VOID,
        'array': TokenType.ARRAY,
        'record': TokenType.RECORD,
        'of': TokenType.OF,
        'null': TokenType.NULL,
        'nil': TokenType.NIL,
        # Literals
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        # Other
        'self': TokenType.SELF,
        'super': TokenType.SUPER,
        'this': TokenType.THIS,
        'and': TokenType.AND,
        'or': TokenType.OR,
        'not': TokenType.NOT,
        'xor': TokenType.XOR,
        'mod': TokenType.MOD,
        'div': TokenType.DIV,
        'skip': TokenType.SKIP,
        'println': TokenType.PRINTLN,
        'assert': TokenType.ASSERT,
        # Advanced features
        'prob': TokenType.PROB,
        'causal': TokenType.CAUSAL,
        'verify': TokenType.VERIFY,
        'given': TokenType.GIVEN,
        'assume': TokenType.ASSUME,
        'requires': TokenType.REQUIRES,
        'ensures': TokenType.ENSURES,
        'invariant': TokenType.INVARIANT,
        'kernel': TokenType.KERNEL,
        # Concurrency
        'async': TokenType.ASYNC,
        'await': TokenType.AWAIT,
        'chan': TokenType.CHAN,
        'actor': TokenType.ACTOR,
        'select': TokenType.SELECT,
        'lock': TokenType.LOCK,
        'atomic': TokenType.ATOMIC,
        # Modules
        'module': TokenType.MODULE,
        'import': TokenType.IMPORT,
        'export': TokenType.EXPORT,
        'from': TokenType.FROM,
        'as': TokenType.AS,
    }

    # Multi-character operators (maximal munch - order by length decreasing)
    MULTI_CHAR_OPS = {
        ':=': TokenType.ASSIGN,
        '=>': TokenType.FAT_ARROW,  # Fat arrow for proc return
        '->': TokenType.ARROW,  # Both map to ARROW for simplicity
        '==': TokenType.EQ,
        '!=': TokenType.NEQ,
        '<>': TokenType.NEQ,  # ALGOL 68 style not equals
        '<=': TokenType.LTE,
        '>=': TokenType.GTE,
        '<<': TokenType.LSHIFT,
        '>>': TokenType.RSHIFT,
        '::': TokenType.DOUBLE_COLON,
        '..': TokenType.DOTDOT,
    }

    # Single-character operators
    SINGLE_CHAR_OPS = {
        '+': TokenType.PLUS,
        '-': TokenType.MINUS,
        '*': TokenType.STAR,
        '/': TokenType.SLASH,
        '%': TokenType.PERCENT,
        '^': TokenType.CARET,
        '=': TokenType.EQ,  # Note: for assignment we use := but = can be equality
        '<': TokenType.LT,
        '>': TokenType.GT,
        ':': TokenType.COLON,
        '.': TokenType.DOT,
        '(': TokenType.LPAREN,
        ')': TokenType.RPAREN,
        '{': TokenType.LBRACE,
        '}': TokenType.RBRACE,
        '[': TokenType.LBRACKET,
        ']': TokenType.RBRACKET,
        ',': TokenType.COMMA,
        ';': TokenType.SEMI,
        '@': TokenType.AT,
        '?': TokenType.QUESTION,
        '!': TokenType.EXCLAMATION,
    }

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.current_char = self.text[0] if text else None

    def error(self, message: str) -> LexerError:
        return LexerError(message, self.line, self.column)

    def advance(self, n: int = 1):
        """Advance position by n characters, updating line/column."""
        for _ in range(n):
            if self.current_char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
            if self.pos < len(self.text):
                self.current_char = self.text[self.pos]
            else:
                self.current_char = None

    def peek(self, n: int = 1) -> Optional[str]:
        """Look ahead n characters without consuming."""
        if self.pos + n - 1 < len(self.text):
            return self.text[self.pos:self.pos + n]
        return None

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def skip_comment(self):
        """Skip single-line or multi-line comment."""
        if self.current_char == '/' and self.peek(2) == '//':
            # Single-line comment
            self.advance(2)  # skip //
            while self.current_char is not None and self.current_char != '\n':
                self.advance()
        elif self.current_char == '/' and self.peek(2) == '/*':
            # Multi-line comment (supports nesting)
            self.advance(2)  # skip /*
            nest_level = 1
            while nest_level > 0 and self.current_char is not None:
                if self.current_char == '/' and self.peek() == '*':
                    nest_level += 1
                    self.advance(2)
                elif self.current_char == '*' and self.peek() == '/':
                    nest_level -= 1
                    self.advance(2)
                else:
                    self.advance()
            if nest_level > 0:
                raise self.error("Unterminated multi-line comment")
        else:
            raise self.error("Expected comment start")

    def read_identifier(self) -> str:
        """Read an identifier or keyword."""
        start_line = self.line
        start_col = self.column
        result = []
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            result.append(self.current_char)
            self.advance()
        value = ''.join(result)
        # Determine if keyword
        token_type = self.KEYWORDS.get(value.lower(), TokenType.IDENT)
        # Special case: boolean literals
        if value == 'true':
            token_type = TokenType.TRUE
        elif value == 'false':
            token_type = TokenType.FALSE
        return Token(token_type, value, start_line, start_col)

    def read_number(self) -> Token:
        """Read integer or real number literal."""
        start_line = self.line
        start_col = self.column
        result = []
        is_float = False

        # Read integer part (digits, possibly with underscores)
        while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '_'):
            result.append(self.current_char)
            self.advance()

        # Check for fractional part or exponent
        if self.current_char == '.':
            is_float = True
            result.append(self.current_char)
            self.advance()
            while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '_'):
                result.append(self.current_char)
                self.advance()

        # Check for exponent
        if self.current_char in ('e', 'E'):
            is_float = True
            result.append(self.current_char)
            self.advance()
            if self.current_char in ('+', '-'):
                result.append(self.current_char)
                self.advance()
            if self.current_char is None or not self.current_char.isdigit():
                raise self.error("Expected digit in exponent")
            while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '_'):
                result.append(self.current_char)
                self.advance()

        # Check for hex, binary, octal prefixes - simplified: in MVP we may not need full support
        # For MVP, we'll handle decimal and simple floats; hex/binary can be deferred

        value_str = ''.join(result)
        token_type = TokenType.REAL if is_float else TokenType.INTEGER

        # Validate underscores not at start/end/consecutive - simplified check
        # For MVP we can be lenient

        return Token(token_type, value_str, start_line, start_col)

    def read_char_literal(self) -> Token:
        """Read a character literal like 'a' or '\n'."""
        start_line = self.line
        start_col = self.column
        if self.current_char != '\'':
            raise self.error("Expected ' to start char literal")
        self.advance()  # consume opening quote

        if self.current_char is None:
            raise self.error("Unterminated char literal")

        # Handle escape sequences
        if self.current_char == '\\':
            self.advance()
            if self.current_char is None:
                raise self.error("Incomplete escape sequence")
            escape_char = self.current_char
            self.advance()
            # For MVP, we'll simplify escapes to just the character after backslash
            # Proper implementation would translate \n, \t, \xHH, etc.
            char_value = '\\' + escape_char  # Keep as two-char sequence for simplicity
        else:
            if self.current_char == '\'':
                raise self.error("Empty char literal")
            char_value = self.current_char
            self.advance()

        if self.current_char != '\'':
            raise self.error("Expected closing ' for char literal")
        self.advance()  # consume closing quote

        return Token(TokenType.CHAR, char_value, start_line, start_col)

    def read_string_literal(self) -> Token:
        """Read a string literal like \"hello\"."""
        start_line = self.line
        start_col = self.column
        if self.current_char != '"':
            raise self.error("Expected \" to start string literal")
        self.advance()  # consume opening quote

        result = []
        while self.current_char is not None and self.current_char != '"':
            if self.current_char == '\\':
                self.advance()
                if self.current_char is None:
                    raise self.error("Incomplete escape sequence in string")
                # Simplified: treat escape as literal backslash + char
                result.append('\\' + self.current_char)
                self.advance()
            else:
                result.append(self.current_char)
                self.advance()

        if self.current_char != '"':
            raise self.error("Unterminated string literal")
        self.advance()  # consume closing quote

        value = ''.join(result)
        return Token(TokenType.STRING, value, start_line, start_col)

    def read_operator_or_punctuator(self) -> Token:
        """Read an operator or punctuator using maximal munch."""
        start_line = self.line
        start_col = self.column

        # Try 3-char operators first (unlikely but for completeness)
        for length in range(4, 1, -1):  # 4, 3, 2
            peek = self.peek(length)
            if peek and peek in self.MULTI_CHAR_OPS:
                token_type = self.MULTI_CHAR_OPS[peek]
                self.advance(length)
                return Token(token_type, peek, start_line, start_col)

        # Single char
        ch = self.current_char
        if ch in self.SINGLE_CHAR_OPS:
            self.advance()
            return Token(self.SINGLE_CHAR_OPS[ch], ch, start_line, start_col)

        raise self.error(f"Unknown character '{ch}'")

    def next_token(self) -> Token:
        """Get the next token from the input."""
        while self.current_char is not None:
            # Skip whitespace
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            # Comments
            if self.current_char == '/' and self.peek(2) in ('//', '/*'):
                self.skip_comment()
                continue

            # Identifier or keyword
            if self.current_char.isalpha() or self.current_char == '_':
                return self.read_identifier()

            # Number
            if self.current_char.isdigit():
                return self.read_number()

            # Character literal
            if self.current_char == '\'':
                return self.read_char_literal()

            # String literal
            if self.current_char == '"':
                return self.read_string_literal()

            # Operators and punctuators
            return self.read_operator_or_punctuator()

        return Token(TokenType.EOF, '', self.line, self.column)

    def tokenize(self) -> List[Token]:
        """Tokenize entire input."""
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens
