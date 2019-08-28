from pathlib import Path

from lark import Lark, InlineTransformer
from sidekick import pipeline

from ox.backend.python.nodes_expr import Atom, Name, BinOp, GetAttr
from ox.backend.python.nodes_stmt import Symbol
from ox.algorithms import reduce_op_chain as op_chain

path = Path(__file__).parent.parent / "grammars" / "python-template.lark"
grammar = Lark(open(path), parser="lalr")
fn = staticmethod
cte = lambda x: lambda *args: x
atom = lambda cls, *opts: lambda *args: Atom(cls(args[-1], *opts))


class PythonT(InlineTransformer):
    int = atom(int)
    hex = fn(lambda x: int(x[2:], 16))
    oct = fn(lambda x: int(x[2:], 8))
    bin = fn(lambda x: int(x[2:], 2))
    float = atom(float)
    complex = atom(complex)
    string = atom(eval)
    true = cte(Atom(True))
    false = cte(Atom(False))
    none = cte(Atom(None))
    ellipsis = cte(Atom(...))
    name = fn(pipeline(Symbol, Name))
    opchain = fn(lambda *xs: xs[0] if len(xs) == 1 else op_chain(xs, expr=BinOp))
    getattr = GetAttr


def parse_stmt(st):
    tree = grammar.parse(st + "\n")
    tree = PythonT().transform(tree)
    print(tree.pretty() if hasattr(tree, "pretty") else tree)
    return tree


parse_stmt("x and y or z")
parse_stmt("a + b * c")
parse_stmt("[1, 2.0, 3j, 0b11, 0b10, 0o10, 0x10, True, False, None, ...]")
parse_stmt("a.b.c")
parse_stmt('"string"')
# parse_stmt('{a:b, **d}')


parse_stmt("print('hello world')")
# parse_stmt("if x:\n    y")
# parse_stmt("if x:\n    y\nelse:\n   z")
parse_stmt("return")
parse_stmt("return x")
parse_stmt("del x")
parse_stmt("del x, y")
parse_stmt("del [x, y]")
parse_stmt("del (x, y)")
# parse_stmt("yield")
# parse_stmt("yield x")
# parse_stmt("yield from x")
parse_stmt("x = y")
# parse_stmt("x = yield")
# parse_stmt("x = yield 42")
parse_stmt("break")
parse_stmt("continue")
# parse_stmt("def f(x):\n    x")
# parse_stmt("def f(x, y=1):\n    x")
# parse_stmt("for x in y:\n    x")
# parse_stmt("while x:\n    x")
# parse_stmt("with x as y:\n    x")
