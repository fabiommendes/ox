Ox is simple "compiler of compilers" framework based on the excellent Lark
library.

.. _Lark:: http://github.com/lark-parser/lark


Why Ox?
=======

Python have a few good libraries for creating parsers (like PLY, Lark, PyParsing, etc)
using various different algorithms and approaches. Ox uses Lark internally and
leverage its builtin capabilities for handling different parsing algorithms, automatic
creation and shaping of parsing trees and a convenient EBNF syntax to describe grammars.
None of those libraries, however, cover other features expected in a complete "compiler of
compilers suite". Namely, Lark is concerned only with parsing, but does not
implement code analysis and generation.

Ox is a minimalistic framework and provides a few utilities in this area. It will
never be nowhere near a Python replacement for, say, LLVM, but it was created
to be useful for a few projects of mine and since Python can be much more productive
than C++, it might even compete with LLVM in some cases. You might find Ox useful
if you want to create a language that targets Python since it has some since features to
conveniently generate Python code.

Ox is not stable enough to be recommended for production code yet. It was created
as a tool for an introductory compilers course at University of Brasilia and this
use case will always play an important part on the design decisions and the overall
shape of this library. One explicit pedagogical goal of Ox is to make the
boundaries of the different compilation phases very explicit and easily
pluggable into each other. This approach is good for
teaching, but it does not lead to the most efficient or robust
implementations of real compilers. Ox, as most compiler generators, is good for
quick experimentation but it is limited in terms of performance and, more
importantly, Ox parsers generally fail to provide nice error messages for
syntax errors. We hope to work on those areas, but it is still a low priority.
 

Concepts
========
 
Compilation is usually broken into a few steps:

1) Tokenization/lexical analysis: a string of source code is broken into a 
   list of tokens. Ox lexers are any function that receives a string of source
   code and return a sequence (or any iterable) of tokens.
2) Parsing: the sequence of tokens is converted into a syntax tree. In Ox, the parser
   is derived from a grammar in EBNF form. It receives a list of tokens and
   outputs an arbitrary parse tree.
3) Semantic analysis: the parse tree is scanned for semantic errors (e.g. 
   invalid variable names, invalid type signatures, etc). The parse tree may
   be converted to different representations in this process.
4) Code optimization: many optimizations are applied in order to generate 
   efficient internal representations. This is highly dependent on the target
   language and runtime and it tends to be the largest part of a real compiler.
5) Code generation: the intermediate representation is used to emit code in the
   target language. The target language is often a low level language such as
   assembly or machine code. Nothing prevents us from emitting Python or
   Javascript, however.

Ox is mostly concerned with steps 1, 2 (via Lark) and 5. The library has very
limited support to semantic analysis and almost no help for code optimization.


Installation
============

Ox can be installed using pip::

    $ python3 -m pip install ox-parser --user

It only works on Python 3.6+.


Usage
=====

We show how to build a simple calculator using Ox. The following examples
explicitly separate parsing into separate steps of lexical, syntactic and semantic
analysis and code generation. Even with Ox, it is possible to blur those
lines a little bit, but you have to read the documentation to know how to do that ;-)

Lexer
-----

Ox can build a lexer function from a list of token names associated with their
corresponding regular expressions:

.. code-block:: python

    import ox
    
    lexer = ox.lexer(
        NUMBER={r'\d+(\.\d*)?': float},
        NAME=r'[a-z]+',
        PLUS=r'[+-]',
        MUL=r'[*\/]',
        WS=r'\s+',
        ignore=['WS'],
    )


Each argument can be either a regular expression or a dictionary mapping
the regular expression to a function. This function is used to associate a value
to the token instead of just using its string content.

This declares a tokenizer function that receives a string of source code and
returns a sequence of tokens:
 
>>> tokens = lexer('21 + 21')
>>> list(tokens)
[Token(NUMBER, 21.0), Token(PLUS, '+'), Token(NUMBER, 21.0)]

We can easily retrieve the value or the type for each token on the list:

>>> [tk.value for tk in lexer('21 + 21')]  # values
[21.0, '+', 21.0]
>>> [tk.type for tk in lexer('21 + 21')]   # token types
['NUMBER', 'PLUS', 'NUMBER']


Parser
------

The next step is to pass the list of tokens to a parser in order to
generate the parse tree. We can easily declare a parser in Ox from a mapping 
of grammar rules to their corresponding handler functions.

Each handler function receives a number of inputs from its corresponding
grammar rule and return an AST node. In the example bellow, we return tuples
to build our AST as LISP-like S-expressions.

.. code-block:: python

    binop = lambda x, op, y: (op.value, x, y)

Now the rules:

.. code-block:: python

    parser = ox.parser(lexer,
    	expr={
    		'expr PLUS term': binop,
    		'term': None,
    	},
    	term={
    		'term MUL atom': binop,
    		'atom': None,
    	},
    	atom={
    		'NUMBER | NAME': lambda x: x.value,
    		 '"(" expr ")"': None,
    	}
    )


The parser consumes a list of tokens and convert them to an AST:

>>> parser('2 + 2 * 20')
('+', 2.0, ('*', 2.0, 20.0))


Interpreter
-----------

The AST makes it easy to analyze and evaluate an expression. We can
write a simple evaluator as follows:

.. code-block:: python

    import operator as op

    operations = {'+': op.add, '-': op.sub, '*': op.mul, '/': op.truediv}
    
    def eval_ast(node):
        if isinstance(node, tuple):
            head, *tail = node
            func = operations[head]
            args = (eval_ast(x) for x in tail)
            return func(*args)
        else:
            return node


The eval function receives an AST, but we can easily compose it with the other
functions in order to accept string inputs. (Ox functions understand sidekick's 
pipeline operators. The arrow operator ``>>`` composes two functions by passing
the output of each function to the function in the pipeline following the arrow
direction).

>>> eval_expr = parser >> eval_ast
>>> eval_expr('2 + 2 * 20')
42.0

We can call this function in a loop to have a nice calculator written with only
a few lines of Python code!

.. code-block:: python

    def eval_loop():
        expr = input('expr: ')
        print('result:', eval_expr(expr))


What about the name?
====================

Ox was initially based on PLY, which is is a Pythonic implementation/interpretation
of Yacc. The most widespread Yacc implementation is of course GNU Bison. We
decided to keep the bovine theme alive and used Ox. The correct pronunciation
(if we can impose such a thing) is in Portuguese: [ɔ-ʃis] (for Portuguese speakers: *ó-xis*).
