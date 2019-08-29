===========
Ox Tutorial
===========

This tutorial shows how to create a simple programming language from the ground
up. Creating a new programming language is obviously an enormous task, so we will
implement a simple functional language gradually, each time showcasing a new feature
of Ox that may be helpful for other projects.

The programming language in question was conceived in a Compilers course as an
educational experiment and is called Cremilda. The original version was very minimalist,
but we decided to extend it for the purpose of this tutorial. Although the main
goal of Cremilda is to exercise Ox and be the ideal subject for this tutorial, it is
actually an usable programming language that can be installed from pip and used in your
Python projects alongside with Python code.

Cremilda is a dynamic functional language that borrows some of Python semantics
(like the data types, operators, etc) and behaves very differently from Python
in other areas (e.g., no exceptions) and may force us to implement some non-trivial
translations. The snippets bellow show Cremilda's syntax in some common
programming examples:

.. code-block:: cremilda

    # Factorial function
    fat(n) =
        if n < 2 then 1 else n * fat(n);

    # Size of Collatz sequence for number
    collatz(n) =
        if n == 1 then
            1
        else if n % 2 == 0 then
            1 + collatz(div(n, 2))
        else
            1 + collatz(3 * n + 1)

In this first part, we will implement support for function declaration, conditionals,
booleans, floats and integers. Cremilda itself does not have loops (but you can loop
with recursion) and few extra complications will be covered later in more advanced parts
of the tutorial. Some parts of the implementation and minor variations are left
as an exercise to the reader :-)


Lexing rules
============

Let us start with a very basic grammar: we need to identify integers, floats, names,
booleans, and a few control symbols and operators. We only need to create
explicit regular expressions in our lexer for the first 3, since operators
and control keywords (like if, then, else) will be inserted in the grammar as
literals.

.. code-block:: python

    import ox

    lex = ox.lexer(
        INT={r'\d+': int},
        FLOAT={r'\d+\.\d+': float},
        NAME=r'(?!\d)[\w]+',
        CTRL=r'[-+*\/%=><!();]+',
        _COMMENTS=r'#[^\n]*',
        _WP='\s+',
    )


We have now a simple (but incomplete lexer) that can tokenize simple Cremilda
programs

>>> tokens = lex('even(x) = if x % 2 == 0 then 1 else 0;')
>>> list(tokens)  # doctest: +ELLIPSIS
[Token(NAME, 'even'), Token(CTRL, '('), ..., Token(INT, 0), Token(CTRL, ';')]

This minimal lexer will work for now.


Parsing
=======

The next step is to build the parser rules.

.. code-block:: python

    from lark import Lark

    grammar = Lark(r"""
    start : def+

    def  : NAME "(" args ")" "=" expr ";" -> fndef
         | NAME "=" expr ";"              -> vdef

    args : NAME ("," NAME)*

    ?expr : "if" logical "then" logical "else" expr  -> cond
          | logical

    ?logical : logical /or/ logical_and  -> binop
             | logical_and

    ?logical_and : logical_and /and/ cmp  -> binop
                 | cmp

    ?cmp  : math (CMP math)+  -> comparison
          | math

    ?math : math /[+-]/ term -> binop
          | term

    ?term : term /[*\/%]/ atom -> binop
          | atom

    ?atom : INT     -> int
          | FLOAT   -> float
          | NAME    -> name
          | "true"  -> true
          | "false" -> false
          | "nil"   -> nil
          | "(" expr ")"

    INT    : /\d+/
    FLOAT  : /\d+\.\d+/
    NAME.0 : /(?!\d)[\w]+/
    CMP    : /==|!=|>|<|>=|<=/
    %ignore /#[^\n]*/
    %ignore /\s+/
    """, parser='lalr')


>>> src = 'even(x) = if x % 2 == 0 then true else false;'
>>> print(grammar.parse(src).pretty())          # doctest: +NORMALIZE_WHITESPACE
start
  fndef
    even
    args	x
    cond
      comparison
        binop
          name x
          %
          int 2
        ==
        int 0
      true
      false

The next step is a transformer

.. code-block:: python

    from lark import InlineTransformer
    fn = staticmethod

    class CremildaT(InlineTransformer):
        int = int
        float = float
        name = str
        true = fn(lambda: True)
        false = fn(lambda: False)
        start = fn(lambda *args: ('mod', dict(args)))
        fndef = fn(lambda name, args, body: (name.value, ('lambda', args, body)))
        vdef = fn(lambda name, body: (name.value, body))
        args = fn(lambda *args: [x.value for x in args])
        binop = fn(lambda lhs, op, rhs: (op.value, lhs, rhs))
        atom = fn(lambda x: x.value)
        cond = fn(lambda cond, then, other: ('if', cond, then, other))

        def comparison(self, first, op, *args):
            if len(args) == 1:
                return (op.value, first, args[0])
            raise NotImplementedError


>>> ast = grammar.parse(src)
>>> CremildaT().transform(ast)
('mod', {'even': ('lambda', ['x'], ('if', ('==', ('%', 'x', 2), 0), True, False))})


Interpreter
===========


.. code-block:: python

	from collections import ChainMap
	import operator as op

	def eval(expr, ns):
		if isinstance(expr, str):
			return ns[expr]
		elif not isinstance(expr, tuple):
			return expr

		head, *args = expr
		if head == 'mod':
			data, = args
			v = None
			for k, v in data.items():
				ns[k] = data[k] = eval(v, ns)
			return data

		elif head == 'if':
			cond, then, other = args
			if eval(cond, ns):
				return eval(then, ns)
			else:
				return eval(other, ns)

		elif head == 'lambda':
			names, body = args

			def fn(*values):
				args = dict(zip(names, values))
				local_ns = ChainMap(args, ns)
				return eval(body, local_ns)

			return fn

		else:
			fn = ns[head]
			return fn(*(eval(x, ns) for x in args))

	ns = {'%': op.mod, '==': op.eq} # ...


>>> mod = eval(CremildaT().transform(ast), ns)
>>> even = mod['even']
>>> even(2)
True


Compiler
========

Building Python code
--------------------

Python has builtin utilities to parse and validate Python code. In the worst case
scenario, one could manually build strings of code and validate them with
the builtin :func:`compile` function. This is cumbersome and brittle.

A better approach would be to manually build syntax trees using the builtin
:mod:`ast` module and dump Python code from the end result. Unfortunately, the
ast module is poorly documented and inconvenient to use. It exists mostly to
expose some internals of the Python interpreter to advanced developers who might
want to understand or interfere with the process of translating a string of
Python source code into actual bytecode that can be executed by the interpreter.

Ox implements its own independent module to represent syntax trees. Ox syntax
trees are...

// >>> from ox.backend.python import node, Atom
// >>> x = node(Name, 'x')
// >>> one = node(Atom, 1)
// >>> add = node(BinOp, x, one, op='+')
// >>> node(42) == node(Atom, 42)
// >>> node.parse('x + 1')
// >>> node.parse('$x = 1', x=2)

Builder objects
---------------

// >>> py.x + 1
// py('x + 1')
// >>> node(py.x + 1)
// >>> py('x + 1')



Compiling Cremilda
------------------

>>> mod = CremildaT().transform(ast)
>>> even_ast = mod[1]['even']
>>> even_ast
('lambda', ['x'], ('if', ('==', ('%', 'x', 2), 0), True, False))


.. code-block:: python
	#from ox.backend.python import *

	def to_python(expr):
		if not isinstance(expr, tuple):
			return e[expr]

		head, *args = expr

		if head == 'mod':
			data, = args
			return let({k: to_python(v) for k, v in data.items()})

		elif head == 'if':
			return cond(*map(to_python, args))

		elif head == 'lambda':
			names, body = args
			return fn(*names)[to_python(body)]

		elif head in operators:
			return binop(head, *map(to_python, args))

		else:
			return e[head](*map(to_python, args))

// >>> to_python(even_ast)
