.. image:: https://api.codeclimate.com/v1/badges/5f489830d64da789bce2/maintainability
   :target: https://codeclimate.com/github/fabiommendes/ox/maintainability
   :alt: Maintainability
.. image:: https://api.codeclimate.com/v1/badges/5f489830d64da789bce2/test_coverage
   :target: https://codeclimate.com/github/fabiommendes/ox/test_coverage
   :alt: Test Coverage
.. image:: https://img.shields.io/github/license/fabiommendes/ox
   :alt: GitHub
.. image:: https://img.shields.io/pypi/v/ox-parser
   :alt: PyPI

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
analysis and code generation. Compilers for complex languages usually blur of those
lines a little bit, and Ox has some support for that.

Lexer
-----

A lexer reads a string and generate a sequence of tokens. Ox builds the lexer function from
a list of token names associated with their corresponding regular expressions:

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

.. code-block:: python

    # Handle binary operations
    binop = lambda x, op, y: (op.value, x, y)

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


The parser consumes a list of tokens and convert them to an AST passing each
element (terminals and non-terminals) to their corresponding handler function.
The rule "expr: expr PLUS term", for instance, produces tree elements, an "expr"
node, followed by a "PLUS" terminal and a "term" node. Those arguments are passed
to the handler function ``binop``, which generates a node of the syntax tree.

In the example above, we create tuples to build our AST as LISP-like S-expressions.

The resulting parser is again just a function that receives a string of code
and return the abstract syntax tree.

>>> parser('2 + 2 * 20')
('+', 2.0, ('*', 2.0, 20.0))


Interpreter
-----------

We can easily evaluate an algebraic expression from syntax trees.
Bellow is a very straightforward expression evaluator:

.. code-block:: python

    import operator as op

    operations = {'+': op.add, '-': op.sub, '*': op.mul, '/': op.truediv}
    
    def eval_ast(node, env):
        if isinstance(node, tuple):
            head, *tail = node
            func = operations[head]
            args = (eval_ast(x, env) for x in tail)
            return func(*args)
        elif isinstance(node, str):
            return env[node]
        else:
            return node

The user should pass a dictionary of all free variables with their corresponding
numeric values.

The eval function receives an AST, but we can easily compose it with the other
functions in order to accept string inputs.

>>> eval_expr = parser >> eval_ast
>>> eval_expr('2 + 2 * 20')
42.0

Ox functions understand sidekick's pipeline operators. The arrow operator ``>>``
composes two functions by passing the output of each function to the function
in the pipeline following the arrow direction

We can call this function in a loop to have a nice calculator written with only
a few lines of Python code!

.. code-block:: python

    def eval_loop(env):
        expr = input('expr: ')
        print('result:', eval_expr(expr, env))


Compiler
--------

The final step is to build a compiler. The goal with this simple calculator is to read
a string containing a mathematical expression and create a Python function that evaluates
this code. The function receive the missing variables as keyword arguments.
This is somewhat of a pointless exercise since our calculator language is
already a subset of Python. Anyway, it demonstrates how to approach code generation
in Ox and showcase some of its capabilities for analysing Python code.

Notice how the main compiler function looks deceptively like the
interpreter.

.. code-block:: python

    import operator as op
    from ox.target.python import py

    operations = {'+': op.add, '-': op.sub, '*': op.mul, '/': op.truediv}

    def compile_expression(node):
        if isinstance(node, tuple):
            head, *tail = node
            func = operations[head]
            args = (compile_expression(x) for x in tail)
            return func(*args)
        elif isinstance(node, str):
            return py[node]
        else:
            return py(node)

There are a few notable differences: we do not pass an environment dictionary to the
compiler and the leaf nodes are wrapped into the ``py`` special object.  Let us call
this function to check what it does:

>>> compile_expression(parser('1 + 1'))
py['1 + 1']

The py object is an expression factory that construct Python abstract syntax
tree nodes by always selecting the tree node that replicates any operation
performed with it. For instance, accessing an attribute creates a node that
represents a Python name:

>>> py.x
py['x']

Add it with a value or to other nodes creates an AST that represents the sum
of two expressions

>>> py.x + py.y + 1
py['x + y + 1']

The resulting value is always a wrapped AST node that replicates the operation
performed to it. It accepts almost all Python operators, attribute access,
function calling, and indexing. It fails with most named binary operators like "and",
"or", "is" and "is not".

S-Expression notation
.....................

We can construct more complex AST nodes calling the py object as if it is
constructing a LISP-like S-Expression. The idea is that any tree node can
be represented as a "head" symbol and a list of arguments. The head is
always an string, and the list of arguments depends on the expression
being generated. Usually, this is very straightforward, like

>>> py('return', py.x)
py['return x']

Python syntax, however, can be very subtle and complicated in some places,
and you'll surely have to consult the documentation to understand those
corner cases. That said, we need to know how to declare a function to continue
with our little project. This is one of those complicated bits since
argument specification in Python can be really non-trivial.

Our goal is to convert something like this::

    (2 * x) + 1

To something like this:

.. code-block:: python

    def func(x):
        return (2 * x) + 1

A function node is declared as a `def`` S-Expression with 3 arguments: the name
the list of arguments, and the body as a list of statements.

>>> py('def', py.func, [py.x], [py('return', (2 * py.x) + 1)])

It accepts more complicated declarations with keyword arguments, type annotations,
variadic arguments, etc. We will not cover that for now, but we encourage you to
try figuring out how those advanced features work.


Extracting trees from py objects
................................

The py object provides a powerful mechanism to generate syntax trees, but it has a serious
limitation: the wrapped AST cannot have any method since calling methods
and accessing attributes simply create new and more complex nodes.

>>> (py.x + py.y).source()
py['(x + y).source()']

Once the basic abstract tree is created, it must be extracted from the
factory object. This is done with the unwrap function

>>> from ox.ast.python import unwrap
>>> unwrap(py.x + py.y)
BinOp('+', py.x, py.y)

The resulting objects have many useful tree-related methods for introspection,
searching, transformation, and code generation. For instance, we can convert
any tree to a string of Python code calling its source() method,

>>> ast = py.x + py.y
>>> ast.source()
'x + y'

Python AST nodes implement lots of useful functions. We refer for the documentation
for a complete list, but let us investigate a few that may be relevant for us now.
In order to complete our calculator, we need to inspect the free variables of the parsed
expression tree. This is easily done:

>>> list(ast.free_vars())
['x', 'y']

Ox can also evaluate expressions whose values we can determine statically. This
is called "constant propagation" in compilers terminology and it is implemented
by the simplify method. Consider the trivial expression,

>>> ast = unwrap(py(40) + py(2))
>>> ast
BinOp('+', 40, 2)

Now, let us simplify it to hold only the computed 42 number:

>>> ast.simplify()
Atom(42)

Constant propagation is a subtle topic and is heavily dependent on typing information
about each expression. For instance, we cannot simplify ``x + 40 + 2`` to ``x + 42``
unless we know that x is an integer or some other compatible numeric type. Python
is very dynamic and any class can override operators do do any funny stuff
they like, including violating basic laws of arithmetic.


Wrapping up
...........

We now know how to complete the puzzle for building a full compiler (or maybe
should we say "transpiler") from *Calculator* to *Python*.

.. code-block:: python

    def compile_ast(ast, function_name='calc'):
        expr = unwrap(compile_expression(ast))
        expr = expr.simplify()
        args = sorted(expr.free_vars())
        fn = py('def', function_name, args, [
            py('return', expr),
        ])
        return fn.source()


    def compile_calculator(expr, function_name='calc'):
        return compile_ast(parser(expr), function_name=function_name)

Now we can simply call "compile_calculator" to convert it from *Calculator*
to Python:

>>> print(compile_ast('40 + 2 + x'))
def calc(x):
    return 42 + x

We can make it available into our own Python code running it with eval():

>>> func = eval(compile_ast('40 + 2 + x'))
>>> func(1)
43


What about the name?
====================

Ox was initially based on PLY, which is is a Pythonic implementation/interpretation
of Yacc. The most widespread Yacc implementation is of course GNU Bison. We
decided to keep the bovine theme alive and used Ox. The correct pronunciation
(if we can impose such a thing) is in Portuguese: [ɔ-ʃis] (for Portuguese speakers: *ó-xis*).
