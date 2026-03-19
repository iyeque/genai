# ALGOL 26 Lexical Syntax Specification

*Version: Draft v0.1*
*Date: 2026-03-19*
*Part of: ALGOL_26_SPEC_v0.1.md*

---

## 1. Overview

The lexical syntax of ALGOL 26 defines how source text is partitioned into tokens. The lexer performs tokenization without semantic analysis, following these rules systematically.

**Key Properties:**
- **Case-sensitive**: `MyVar` ≠ `myvar`
- **Unicode-aware**: Full Unicode support for identifiers and strings
- **ALGOL 68 heritage**: Maintains compatibility where practical
- **Modern conventions**: C-like operators, `//` and `/* */` comments

---

## 2. Character Set

ALGOL 26 source files are encoded in **UTF-8**. The following character categories are recognized:

| Category | Characters | Notes |
|----------|------------|-------|
| Letters | Unicode L* categories (Lu, Ll, Lt, Lm, Lo) | Includes all alphabetic Unicode |
| Digits | `0-9` | ASCII digits |
| Underscore | `_` | ASCII underscore |
| Whitespace | Space, tab, LF, CR, VT, FF | See Section 7 |
| Other | All remaining Unicode code points | Treated as "others" or errors in specific contexts |

---

## 3. Identifiers

Identifiers name variables, functions, types, labels, and other program entities.

### 3.1 Syntax

```
identifier ::= letter (letter | digit | underscore)*
_xid       ::= '_' (letter | digit | underscore)*
```

**Rules:**
- Must start with a **letter** or **underscore** (if special "private" identifiers allowed)
- Subsequent characters may be **letters**, **digits**, or **underscores**
- Unicode letters are fully supported (e.g., `π`, `β`, `变量`, `변수`, `переменная`)

### 3.2 Special Identifiers

Identifiers beginning with underscore are reserved for compiler/internal use. User code may use them but with caution.

### 3.3 Examples

```algol26
x
myVariable
MAX_VALUE
α_β_γ
temperature_celsius
π_approx
var3
_privateInternal
 motivation      // trailing spaces trimmed
```

### 3.4 Reserved Identifiers (Keywords)

The following identifiers are **reserved words** and cannot be used as ordinary identifiers (see Section 4). All keywords are lowercase.

---

## 4. Keywords (Reserved Words)

### 4.1 Complete List

**Control Flow:**

| Keyword | Purpose |
|---------|---------|
| `if` | Conditional |
| `then` | Then-branch |
| `else` | Else-branch |
| `elif` | Else-if branch |
| `fi` | End if-block (ALGOL 68 style) |
| `case` | Case selection |
| `in` | Case alternative / comprehension |
| `out` | Output parameter |
| `for` | Loop |
| `while` | While loop |
| `do` | Loop body |
| `od` | End do-loop (ALGOL 68 style) |
| `repeat` | Repeat-until loop |
| `until` | Termination condition |
| `goto` | Jump to label |
| `return` | Function return |
| `break` | Exit loop |
| `continue` | Next iteration |
| `switch` | Switch statement |
| `default` | Default case |

**Declarations:**

| Keyword | Purpose |
|---------|---------|
| `begin` | Block start |
| `end` | Block end |
| `proc` | Procedure declaration |
| `func` | Function declaration |
| `type` | Type definition |
| `mode` | Mode (type) declaration (ALGOL 68 style) |
| `var` | Variable declaration |
| `const` | Constant declaration |
| `ref` | Reference (borrowed pointer) |
| `own` | Ownership declaration |
| `let` | Let-binding (immutable) |
| `struct` | Structure type |
| `union` | Union type |
| `enum` | Enumeration type |
| `class` | Class (optional, if OOP supported) |
| `interface` | Interface |

**Type Primitives:**

| Keyword | Type |
|---------|------|
| `int` | Integer |
| `real` | Floating-point |
| `bool` | Boolean |
| `char` | Character |
| `string` | String |
| `byte` | Byte |
| `void` | No value |
| `null` | Null value |

**Concurrency:**

| Keyword | Purpose |
|---------|---------|
| `async` | Asynchronous function |
| `await` | Wait for async result |
| `chan` | Channel |
| `actor` | Actor definition |
| `select` | Select on channels |
| `lock` | Mutex |
| `atomic` | Atomic operation |

**Advanced Features:**

| Keyword | Purpose |
|---------|---------|
| `prob` | Probabilistic block |
| `causal` | Causal modeling |
| `verify` | Verification annotation |
| `assume` | Assume condition |
| `assert` | Assert condition |
| `requires` | Precondition |
| `ensures` | Postcondition |
| `invariant` | Loop invariant |
| `kernel` | GPU/compute kernel |

**Module System:**

| Keyword | Purpose |
|---------|---------|
| `module` | Module definition |
| `import` | Import module |
| `export` | Export symbol |
| `from` | Import from module |

**Other:**

| Keyword | Purpose |
|---------|---------|
| `true` | Boolean true |
| `false` | Boolean false |
| `nil` | Nil/null reference |
| `self` | Current object/actor |
| `super` | Parent class |
| `this` | Current context (alternative to self) |
| `and` | Logical AND |
| `or` | Logical OR |
| `not` | Logical NOT |
| `xor` | Logical XOR |
| `mod` | Modulo |
| `div` | Integer division |
| `by` | By clause (for loops) |
| `to` | Range to |
| `downto` | Range downto |

### 4.2 Notes

- **ALGOL 68 compatibility**: Keywords `fi`, `od`, `in` (case), `out` preserve heritage.
- **Case**: All keywords are **lowercase only**. `IF`, `If`, `IfThen` are identifiers, not keywords.
- **Future-proofing**: Additional keywords may be added in later versions but never removed.

---

## 5. Literals

### 5.1 Numeric Literals

#### Integer Literals

```
decimal_int   ::= digit+ ( '_' digit+ )*  // underscores for readability
hex_int       ::= '0x' hex_digit+ ( '_' hex_digit+ )*
binary_int    ::= '0b' bin_digit+ ( '_' bin_digit+ )*
octal_int     ::= '0o' oct_digit+ ( '_' oct_digit+ )*
digit         ::= '0'..'9'
hex_digit     ::= digit | 'a'..'f' | 'A'..'F'
bin_digit     ::= '0' | '1'
oct_digit     ::= '0'..'7'
```

**Examples:**
```algol26
42
1_000_000        // one million
0xDEADBEEF       // hex
0b1010_1010      // binary
0o755            // octal
```

#### Floating-Point Literals

```
float_lit ::= (digit+ '.' digit* | '.' digit+) exponent? | digit+ exponent
exponent  ::= ('e' | 'E') ('+' | '-')? digit+
```

Underscores allowed between digits for readability.

**Examples:**
```algol26
3.14
2.71828
1.0
.5
5.0e10
6.022e23
1_234.567_89e-5
```

#### Complex Literals (if supported)

```algol26
1.0 + 2.5i      // real + imaginary
3i              // pure imaginary
```

### 5.2 Character Literals

```
char_lit ::= '\'' ( escaped_char | any_char_except_single_quote_or_backslash ) '\''
escaped_char ::= '\' ( '\'' | '"' | '\\' | 'n' | 't' | 'r' | 'b' | 'f' | 'v' | '0' | 'x' hex_digit+ | 'u' hex_digit+ | 'U' hex_digit+ )
```

**Examples:**
```algol26
'a'
'Z'
'\n'       // newline
'\t'       // tab
'\''       // single quote
'\\'       // backslash
'\x41'     // hex escape = 'A'
'\u03C0'   // Unicode pi
'\U0001F600' // Unicode emoji
```

### 5.3 String Literals

```
string_lit ::= '"' ( escaped_char | any_char_except_double_quote_or_backslash )* '"'
```

Strings are immutable sequences of characters.

**Examples:**
```algol26
"Hello, World!"
"Line 1\nLine 2"
"Quotes: \" \""
"Path: C:\\Users\\Alice"
"Unicode: مرحبا"
"Raw: first line\nsecond line"  // escape interpreted
```

*Note: Raw string literals (no escape processing) may be added as `r"..."` in future versions.*

### 5.4 Boolean Literals

```
bool_lit ::= 'true' | 'false'
```

These are keywords, not identifiers.

---

## 6. Operators and Punctuation

### 6.1 Operator Classification

| Category | Operators | Description |
|----------|-----------|-------------|
| Assignment | `:=`, `=` | Assignment / bind |
| Arithmetic | `+`, `-`, `*`, `/`, `%`, `^` | Add, subtract, multiply, divide, modulo, exponent |
| Relational | `=`, `/=`, `==`, `!=`, `<`, `>`, `<=`, `>=` | Equality, inequality, ordering |
| Logical | `and`, `or`, `not`, `&`, `|`, `~`, `xor` | AND, OR, NOT, bitwise, XOR |
| Bitwise | `&`, `\|`, `~`, `<<`, `>>` | Bit operations |
| Structural | `::`, `->`, `.`, `..`, `:` | Cons, pointer, member, range, type ascription |
| Delimiters | `(`, `)`, `[`, `]`, `{`, `}` | Grouping, indexing, blocks |
| Separators | `,`, `;` | Argument/statement separator |
| Misc | `@`, `?`, `!` | Decorators, optionals, warnings |

### 6.2 Multi-character Operators

ALGOL 26 uses **maximal munch** (longest match):

```
:=   assignment (ALGOL 68 style)
==   equality
!=   inequality
/=   not equals (ALGOL 68 style, alternative to !=)
>>=  right shift assign
<<=  left shift assign
+=   add assign
-=   subtract assign
*=   multiply assign
/=   divide assign
%=   modulo assign
^=   exponent assign
::   cons operator (list construction)
->   function type / pointer
..   range (inclusive)
...  variadic / ellipsis (if supported)
```

### 6.3 Operator Precedence (High to Low)

1. `.`, `[]`, `()` (member access, indexing, call)
2. `!`, `~`, unary `-`, unary `+`, `*` (dereference) — right associative
3. `^` (exponentiation) — right associative
4. `*`, `/`, `%` — left associative
5. `+`, `-` — left associative
6. `<<`, `>>` — left associative
7. `&` (bitwise AND) — left associative
8. `^` (bitwise XOR) — left associative
9. `|` (bitwise OR) — left associative
10. `=`, `/=`, `==`, `!=`, `<`, `>`, `<=`, `>=` — non-associative (comparisons)
11. `and` — left associative
12. `or` — left associative
13. `?:` (ternary) — right associative
14. Assignment (`:=`, `=`, `+=`, etc.) — right associative
15. `,` (comma) — left associative
16. `;` (statement separator) — not an operator

*Note: Parentheses `( )` override precedence.*

### 6.4 Examples

```algol26
a + b * c           // + lower than *
(a + b) * c         // parentheses override
a := b + c * d      // assignment lowest
x^y^z               // right-assoc: x^(y^z)
1 .. 10             // range
list :: elem        // construct list
f(x, y, z)          // function call
arr[i]              // indexing
obj.field           // member access
```

---

## 7. Comments

ALGOL 26 supports two comment styles:

### 7.1 Single-line Comments

```
// ... rest of line ...
```

Everything from `//` to end-of-line (LF/CRLF/CR) is ignored. Cannot be nested.

**Examples:**
```algol26
x := 5  // assign 5
// This entire line is a comment
```

### 7.2 Multi-line Comments

```
/* ... */
```

Everything between `/*` and matching `*/` is ignored. Comments **can be nested** (each `/*` requires a matching `*/`).

**Examples:**
```algol26
/* This is a
   multi-line
   comment */

/* Nested:
   /* inner */ outer continues
*/
```

**Non-comment example:**
```algol26
x = /* comment */ 5  // valid, value is 5
```

### 7.3 Documentation Comments (Optional)

If documentation generator is implemented, `/** ... */` (Javadoc style) may be recognized specially, but lexically it's still a comment.

---

## 8. Whitespace

Whitespace tokens (space, tab, newline, carriage return, vertical tab, form feed) are **insignificant** except where needed to separate tokens.

**Examples:**
```algol26
x=y      // valid (no whitespace needed)
x = y    // valid
x   =   y  // valid
x
= y      // valid across newline
```

**Exceptions:**
- Cannot split a multi-character token: `x: =` is two tokens (`:` and `=`), **not** `:=`
- Cannot merge across string/char literals: `"hello world"` is one token
- Newlines may be statement separators in some contexts (like `;`), but semicolons are preferred

### 8.1 Statement Separation

A statement may be terminated by:
- Semicolon `;`
- Newline (if enabled by context; discouraged in complex expressions)
- End of block (`end`, `}`)

**Recommended**: Always use `;` between statements for clarity.

---

## 9. Lexical Ambiguities and Resolution

### 9.1 Ambiguity: `:` vs `:=`

- `:` alone is a separate token (type ascription, label marker)
- `:=` is the assignment operator
- **Resolution**: Maximal munch — `:` followed by `=` forms `:=`, not `:` + `=`

### 9.2 Ambiguity: `/` vs `//` vs `/*`

- `/` is division operator
- `//` starts single-line comment
- `/*` starts multi-line comment
- **Resolution**: Maximal munch — `//` or `/*` take precedence over `/`

### 9.3 Ambiguity: Identifier vs Keyword

- `if` is keyword
- `iff` (if and only if) is identifier
- **Resolution**: Exact match only — reserved words cannot be used as identifiers even in contexts where they wouldn't be ambiguous

### 9.4 Ambiguity: `'a'` vs `"a"`

- Single quotes → character literal (type `char`)
- Double quotes → string literal (type `string`)
- **Resolution**: Distinguish by quote type

### 9.5 Ambiguity: Hex/Octal/Binary Prefixes

- `0x` → hexadecimal
- `0b` → binary
- `0o` → octal
- `0` alone → decimal zero (not octal!)
- **Resolution**: Two-character prefix determines base; `0` followed by digit without `x/b/o` is decimal.

### 9.6 Ambiguity: Integer vs Float

- `5` → integer
- `5.0` → float
- `5.` → float
- `.5` → float
- **Resolution**: Presence of decimal point determines float

### 9.7 Ambiguity: Negative Numbers vs Subtraction

- `-5` is a negative integer literal (unary minus applied to 5)
- `a - b` is subtraction
- **Resolution**: Lexer produces `-` token and `5` token separately; parser interprets based on context.

### 9.8 String Escape Sequences

Escape sequences are interpreted in the lexer or string parser:

| Escape | Meaning |
|--------|---------|
| `\'` | Single quote |
| `\"` | Double quote |
| `\\` | Backslash |
| `\n` | Newline (LF) |
| `\t` | Tab |
| `\r` | Carriage return |
| `\b` | Backspace |
| `\f` | Form feed |
| `\v` | Vertical tab |
| `\0` | NUL (zero byte) |
| `\xHH` | Hex byte (exactly 2 hex digits) |
| `\uHHHH` | Unicode code point (4 hex digits) |
| `\UHHHHHHHH` | Unicode code point (8 hex digits) |

Invalid escapes are lexer errors.

### 9.9 Unterminated Strings/Comments

- Unterminated string (`"unterminated`) → lex error
- Unterminated comment (`/* comment`) → lex error
- Position tracked for error messages.

### 9.10 Unicode in Identifiers

Unicode allows confusable characters (e.g., Latin `a` vs Greek `α`). For portability, compilers may issue warnings for mixed-script identifiers but **must accept** valid Unicode.

---

## 10. Token Stream Format

The lexer outputs a sequence of tokens, each with:

```text
Token {
  type: KEYWORD | IDENT | INT | FLOAT | CHAR | STRING | OPERATOR | PUNCTUATOR | COMMENT | WHITESPACE | ERROR
  value: string   // raw text
  line: int       // starting line number
  col: int        // starting column number
}
```

Whitespace and comment tokens may be dropped in typical mode, but retained for error reporting and source maps.

---

## 11. Example Lexical Analysis

Source:
```algol26
// Compute factorial
proc factorial(n: int) => int =
  if n <= 1 then 1 else n * factorial(n - 1) fi;

begin
  println("Factorial of 5 = ", factorial(5))
end
```

Token stream (simplified):

| Type     | Value     |
|----------|-----------|
| COMMENT  | `// Compute factorial` |
| KEYWORD  | `proc` |
| IDENT    | `factorial` |
| PUNCT    | `(` |
| IDENT    | `n` |
| PUNCT    | `:` |
| KEYWORD  | `int` |
| PUNCT    | `)` |
| OPERATOR | `=>` |
| KEYWORD  | `int` |
| OPERATOR | `=` |
| ... | ... |

---

## 12. Implementation Notes

### 12.1 Lexer Algorithm

1. Read source as UTF-8 byte stream, decode to Unicode scalar values
2. Skip BOM if present (`U+FEFF`)
3. Process characters sequentially using maximal munch:
   - Try to match longest operator/punctuator first (`>=`, `>>=`, `::`, etc.)
   - Check for comment start (`//` or `/*`)
   - Check for string/char literals (`"`, `'`)
   - Check for numeric literals (digit sequences with optional `.` and exponent)
   - Otherwise, identifier: run of letters/digits/underscores
   - Check if identifier is a keyword (lowercase only)
4. Track line and column for error messages
5. On error, report location and attempt recovery (e.g., skip to next newline)

### 12.2 State Machine

Lexer states:
- `DEFAULT` — normal code
- `LINE_COMMENT` — after `//`, until newline
- `BLOCK_COMMENT` — after `/*`, until `*/` (nesting count)
- `STRING` — inside `"..."`
- `CHAR` — inside `'...'`

Transitions are deterministic.

### 12.3 Performance

- Streaming lexer (no need to load entire file in memory)
- Use hash table for keyword lookup (O(1))
- Pre-scan for BOM and encoding declaration if future `#encoding` pragma added

---

## 13. Future Extensions

Potential additions to lexical syntax in ALGOL 26 v1.0+:

- Raw string literals: `r"no escapes\n"`  
- Byte string literals: `b"bytes"`
- Character literals with multiple codepoints (graphemes)
- Regex literals: `r/pattern/flags`
- Interpolated strings: `"Hello, {name}!"`
- Shebang line support for scripts: `#!/usr/bin/env algo26`
- Encoding pragma: `#encoding "utf-8"`

These are **not** part of v0.1.

---

## Appendix A: Complete Character Classes Reference

```
Letter         = UniCategory(Lu | Ll | Lt | Lm | Lo)
Digit          = '0'..'9'
HexDigit       = Digit | 'A'..'F' | 'a'..'f'
BinDigit       = '0' | '1'
OctDigit       = '0'..'7'
Underscore     = '_'
Whitespace     = ' ' | '\t' | '\n' | '\r' | '\v' | '\f'
LineTerminator = '\n' | '\r' | '\r\n'
```

---

## Appendix B: Keywords Cross-Reference (Alphabetical)

| Keyword | Category | Introduced In |
|---------|----------|---------------|
| `actor` | Concurrency | v0.1 |
| `and` | Logical | v0.1 |
| `array` | (See type system spec) | v0.1 |
| `assert` | Verification | v0.1 |
| `async` | Concurrency | v0.1 |
| `await` | Concurrency | v0.1 |
| `begin` | Block | v0.1 |
| `bool` | Type | v0.1 |
| `break` | Control | v0.1 |
| `by` | Loop | v0.1 |
| `causal` | Causal | v0.1 |
| `case` | Control | v0.1 |
| `chan` | Concurrency | v0.1 |
| `char` | Type | v0.1 |
| `class` | OOP (optional) | v0.1 |
| `const` | Declaration | v0.1 |
| `continue` | Control | v0.1 |
| `default` | Switch | v0.1 |
| `div` | Arithmetic | v0.1 |
| `do` | Loop | v0.1 |
| `downto` | Range | v0.1 |
| `else` | Conditional | v0.1 |
| `end` | Block | v0.1 |
| `enum` | Type | v0.1 |
| `fi` | Block end | v0.1 |
| `false` | Boolean | v0.1 |
| `for` | Loop | v0.1 |
| `from` | Import | v0.1 |
| `func` | Function | v0.1 |
| `if` | Conditional | v0.1 |
| `import` | Module | v0.1 |
| `in` | Case / Comprehension | v0.1 |
| `int` | Type | v0.1 |
| `interface` | OOP (optional) | v0.1 |
| `let` | Binding | v0.1 |
| `lock` | Concurrency | v0.1 |
| `mod` | Arithmetic | v0.1 |
| `module` | Module | v0.1 |
| `not` | Logical | v0.1 |
| `null` | Null | v0.1 |
| `od` | Block end | v0.1 |
| `or` | Logical | v0.1 |
| `out` | Parameter | v0.1 |
| `own` | Ownership | v0.1 |
| `prob` | Probabilistic | v0.1 |
| `proc` | Procedure | v0.1 |
| `real` | Type | v0.1 |
| `ref` | Borrowing | v0.1 |
| `repeat` | Loop | v0.1 |
| `requires` | Verification | v0.1 |
| `return` | Control | v0.1 |
| `select` | Concurrency | v0.1 |
| `self` | Object | v0.1 |
| `string` | Type | v0.1 |
| `struct` | Type | v0.1 |
| `super` | Inheritance | v0.1 |
| `switch` | Control | v0.1 |
| `then` | Conditional | v0.1 |
| `this` | Context | v0.1 |
| `to` | Range | v0.1 |
| `true` | Boolean | v0.1 |
| `type` | Declaration | v0.1 |
| `until` | Loop | v0.1 |
| `union` | Type | v0.1 |
| `verify` | Verification | v0.1 |
| `void` | Type | v0.1 |
| `while` | Loop | v0.1 |
| `xor` | Logical | v0.1 |

---

**End of Lexical Syntax Specification**

*This document will be incorporated into `ALGOL_26_SPEC_v0.1.md`.*
