# ALGOL 26 Minimal Viable Subset - BNF Grammar

**Version**: 0.1 draft  
**Date**: 2026-03-19  
**Scope**: Core language constructs for MVP interpreter  

---

## Notation

- `::=` defines a production rule
- `|` separates alternatives
- `[...]` denotes optional (0 or 1 occurrence)
- `{...}` denotes repetition (0 or more occurrences)
- `<token>` denotes a lexical token
- Non-terminals are in camelCase
- Keywords are in bold (lexical level)

---

## Lexical Grammar (Tokens)

### Identifiers and Literals

```
identifier ::= <ALPHANUMERIC_START> { <ALPHANUMERIC> | '_' }*
integer     ::= <DIGIT> { <DIGIT> }*
real        ::= <DIGIT> { <DIGIT> }* '.' <DIGIT> { <DIGIT> }*
charLiteral ::= '\'' <CHAR_CONTENT> '\''
stringLiteral ::= '"' { <CHAR_CONTENT> }* '"'
boolean     ::= 'true' | 'false'
```

### Keywords (reserved)

```
if      while     for      begin    end
proc    result    var      type     return
array   of        record   with     in
and     or        not      true     false
mod     div       skip     println  assert
```

### Operators

```
arithmeticOp   ::= '+' | '-' | '*' | '/' | '%'
comparisonOp   ::= '=' | '<>' | '<' | '<=' | '>' | '>='
logicalOp      ::= 'and' | 'or' | 'not'
assignmentOp   ::= ':='
indexOp        ::= '['
accessOp       ::= '.'
```

### Separators

```
semicolon ::= ';'
colon     ::= ':'
comma     ::= ','
lparen    ::= '('
rparen    ::= ')'
lbrace    ::= '{'
rbrace    ::= '}'
lbracket  ::= '['
rbracket  ::= ']'
```

### Comments and Whitespace

```
comment ::= '#' { <ANY_CHAR> }* '\n'
whitespace ::= (' ' | '\t' | '\n' | '\r')+
```

---

## Program Structure

```
program ::= (declaration)* statement*

declaration ::= varDecl
             | typeDecl
             | procDecl
             | constDecl

varDecl ::= 'var' identifier ':' typeName ['=' expr] ';'

typeName ::= identifier
           | 'int'
           | 'real'
           | 'bool'
           | 'char'
           | 'string'
           | 'array' '[' expr ']' 'of' typeName   # MVP: fixed-size arrays with constant size
           | 'record' '{' fieldList '}'
           | 'proc' '(' paramList ')' '=>' typeName  # Function type

fieldList ::= field { ',' field }*
field ::= identifier ':' typeName

paramList ::= [param { ',' param }]
param ::= identifier ':' typeName

procDecl ::= 'proc' identifier '(' [paramList] ')' ['=>' typeName] block
           | 'proc' identifier '(' [paramList] ')' ['=>' typeName] '=' expr ';'  # Expression form

constDecl ::= 'const' identifier ':' typeName '=' expr ';'

block ::= 'begin' statement* 'end'
```

---

## Statements

```
statement ::= assignment ';'
            | procCall ';'
            | ifStatement
            | whileStatement
            | forStatement
            | returnStatement ';'
            | block
            | expr ';'                      # Expression statement
            | 'skip' ';'
            | 'assert' expr ';'            # MVP: runtime assertion

assignment ::= identifier assignmentOp expr
             | arrayIndex assignmentOp expr
             | recordAccess assignmentOp expr

procCall ::= identifier '(' [expr { ',' expr }] ')'

ifStatement ::= 'if' expr 'then' statement ('else' statement)?

whileStatement ::= 'while' expr 'do' statement

forStatement ::= 'for' identifier ':' expr 'to' expr ['step' expr] 'do' statement

returnStatement ::= 'result' ':=' expr
                  | 'return' expr            # Alternative syntax
```

---

## Expressions

Expression grammar with precedence (highest to lowest):

### 1. Primary Expressions

```
expr ::= primary
       | arrayConstructor
       | recordConstructor
       | procLambda

primary ::= identifier
          | integer
          | real
          | boolean
          | charLiteral
          | stringLiteral
          | '(' expr ')'
          | arrayIndex
          | recordAccess
          | procCall
```

### 2. Unary Operations

```
unaryExpr ::= ('-' | 'not') primary
```

### 3. Multiplicative Operations

```
multExpr ::= unaryExpr { ('*' | '/' | '%' | 'mod' | 'div') unaryExpr }
```

### 4. Additive Operations

```
addExpr ::= multExpr { ('+' | '-') multExpr }
```

### 5. Comparison Operations

```
compExpr ::= addExpr { ('=' | '<>' | '<' | '<=' | '>' | '>=') addExpr }
```

### 6. Logical AND

```
andExpr ::= compExpr { 'and' compExpr }
```

### 7. Logical OR

```
orExpr ::= andExpr { 'or' andExpr }
```

**expr** resolves to **orExpr**

---

## Complex Expressions

```
arrayIndex ::= identifier '[' expr ']'

recordAccess ::= identifier '.' identifier

arrayConstructor ::= '[' [expr { ',' expr}] ']'

recordConstructor ::= identifier '{' [fieldAssign { ',' fieldAssign}] '}'
fieldAssign ::= identifier ':' expr

procLambda ::= 'proc' '(' [paramList] ')' ['=>' typeName] '=' expr
             | 'proc' '(' [paramList] ')' ['=>' typeName] block
```

---

## Types (Type Name Productions)

```
typeName ::= primitiveType
           | arrayType
           | recordType
           | procType

primitiveType ::= 'int' | 'real' | 'bool' | 'char' | 'string'

arrayType ::= 'array' '[' expr ']' 'of' typeName   # MVP: constant size only

recordType ::= 'record' '{' fieldList '}'

procType ::= 'proc' '(' paramList ')' '=>' typeName
```

---

## Minimal Viable Subset (MVP) Marking

The following constructs are **essential** for the Week 2 interpreter prototype:

### ✓ MVP CORE (Must Implement)

```
✓ program
✓ varDecl, constDecl
✓ typeName (int, real, bool, char, string, array, record)
✓ assignment, procCall
✓ ifStatement, whileStatement, forStatement
✓ block
✓ expr (full precedence hierarchy)
✓ identifier, integer, real, boolean, charLiteral, stringLiteral
✓ arithmeticOps (+, -, *, /, %)
✓ comparisonOps (=, <>, <, <=, >, >=)
✓ logicalOps (and, or, not)
✓ arrayIndex, recordAccess
✓ procDecl (with parameters, return type, recursion)
✓ arrayConstructor, recordConstructor
✓ assert statement
✓ println builtin
```

### ➜ DEFERRED TO POST-MVP

```
○ 'step' in for loops (use default +1)
○ 'causal' blocks (probabilistic programming)
○ 'prob' expressions
○ 'verify' annotations
○ 'kernel' blocks (GPU)
○ 'async'/'await' concurrency
○ 'channel' types
○ 'mod'/'div' integer ops (can use % and /)
○ full dependent types / refinement types
○ type inference (require explicit types)
○ generics / parametric polymorphism
○ modules / imports
○ error handling (exceptions)
○ string operations beyond literals
○ type coercions (require explicit conversions)
```

---

## Example Programs

### Example 1: Hello World

```
begin
  println("Hello, ALGOL 26 World!")
end
```

### Example 2: Variables, Types, and Control Flow

```
begin
  var x: int := 10;
  var y: real := 3.14;
  var flag: bool := true;
  var name: string := "ALGOL";
  
  if x > 5 and flag then
    begin
      println("x is greater than 5");
      y := y * 2.0
    end
  else
    println("x is not greater than 5");
  
  var i: int := 0;
  while i < 10 do
    begin
      println(i);
      i := i + 1
    end;
  
  for j: int := 1 to 5 do
    println(j * j)
end
```

### Example 3: Arrays and Records

```
type Point = record { x: real, y: real };
type Grid = array [10] of int;

begin
  var p: Point := Point { x: 1.5, y: 2.5 };
  var nums: Grid := [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  
  println("Point: (", p.x, ", ", p.y, ")");
  println("Sum: ", nums[1] + nums[10]);
  
  // Array modification
  for i: int := 1 to 10 do
    nums[i] := nums[i] * 2
end
```

### Example 4: Functions and Recursion

```
proc factorial(n: int) => int =
  if n <= 1 then
    1
  else
    n * factorial(n - 1);

proc greet(name: string) =>
  begin
    println("Hello, ", name, "!")
  end;

proc fib(n: int) => int =
  if n <= 1 then
    n
  else
    fib(n - 1) + fib(n - 2);

begin
  println("5! = ", factorial(5));
  greet("ALGOL 26");
  println("fib(10) = ", fib(10))
end
```

### Example 5: More Complex Expressions

```
begin
  var a: int := 10;
  var b: int := 3;
  var result: int;
  
  result := (a + b) * (a - b) mod 5;
  println("Result: ", result);
  
  // Logical expressions
  var condition: bool := (a > b) and (b > 0) or (a = 0);
  println("Condition: ", condition);
  
  // Nested array indexing
  type Matrix = array [3] of array [3] of int;
  var m: Matrix := [[1,2,3],[4,5,6],[7,8,9]];
  println("Center: ", m[2][2])
end
```

---

## Grammar Summary for Parser Implementation

This BNF is designed for a **recursive descent parser** with a **Pratt parser** for expressions. The token stream should include:

- Keywords as distinct tokens
- Operators with precedence levels:
  1. `-`, `not` (unary prefix)
  2. `*`, `/`, `%`, `mod`, `div`
  3. `+`, `-`
  4. `=`, `<>`, `<`, `<=`, `>`, `>=`
  5. `and`
  6. `or`

The grammar avoids left recursion. All statements are terminated by semicolons, except block-structured forms (`if`, `while`, `for`) which can contain single statements or blocks.

**Note**: ALGOL 26 preserves ALGOL 68's "compound statement" (`begin...end`) and "result" variable for function returns, while also supporting `return` as an alternative.

---

*End of BNF grammar draft. Ready for implementation and inclusion in ALGOL_26_SPEC_v0.1.md.*