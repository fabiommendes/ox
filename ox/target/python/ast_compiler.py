import ast
from ast import parse as ast_parse

from ox.backend.python import nodes_expr as expr
from ox.backend.python import nodes_stmt as stmt
from ox.backend.python.nodes_expr import expr as to_expr, register as register_expr
from ox.backend.python.nodes_stmt import stmt as to_stmt, register as register_stmt
from ox.target.python.operators import Op

__all__ = ["parse_expr", "parse_stmt"]

AST = ast.expr.__base__
OPERATOR_MAP = {
    # Arithmetic
    ast.Add: Op.ADD,
    ast.Sub: Op.SUB,
    ast.Mult: Op.MUL,
    ast.Div: Op.TRUEDIV,
    ast.MatMult: Op.MATMUL,
    ast.Mod: Op.MOD,
    ast.FloorDiv: Op.FLOORDIV,
    ast.Pow: Op.POW,
    # Comparison
    ast.Gt: Op.GT,
    ast.GtE: Op.GE,
    ast.Lt: Op.LT,
    ast.LtE: Op.LE,
    ast.Eq: Op.EQ,
    ast.NotEq: Op.NE,
    ast.Is: Op.IS,
    ast.IsNot: Op.IS_NOT,
    ast.In: Op.IN,
    ast.NotIn: Op.NOT_IN,
    ast.Or: Op.OR_,
    ast.And: Op.AND_,
    # Bitwise
    ast.BitOr: Op.OR,
    ast.BitAnd: Op.AND,
    ast.BitXor: Op.XOR,
    ast.RShift: Op.RSHIFT,
    ast.LShift: Op.LSHIFT,
}


def parse_expr(src):
    """
    Parse a string that represents a Python expression and return the
    corresponding Expr instance.
    """
    e, = ast_parse(src).body
    assert isinstance(e, ast.Expr)
    return to_expr(e.value)


def parse_stmt(src):
    """
    Parse a string that represents a Python statement and return the
    corresponding Expr instance.
    """
    body = ast_parse(src).body
    if len(body) == 1:
        return to_stmt(body[0])
    else:
        return stmt.Block([to_stmt(x) for x in body])


# Utility functions
cte = lambda c: lambda x: c
dbg = lambda x, *args: print(x, *args) or x
fields = lambda cls, fs, T=to_expr: lambda e: cls(*(T(getattr(e, f)) for f in fs))
emap = lambda xs: map(to_expr, xs)

# Simple expression handlers
register_expr(ast.Attribute, lambda e: expr.GetAttr(to_expr(e.value), e.attr))
register_expr(ast.BinOp, fields(expr.BinOp, ["op", "left", "right"]))
register_expr(ast.Ellipsis, lambda e: expr.Atom(...))
register_expr(ast.IfExp, fields(expr.Ternary, ["test", "body", "orelse"]))
register_expr(ast.List, lambda e: expr.List([*emap(e.elts)]))
register_expr(ast.Name, lambda e: expr.Name(e.id))
register_expr(ast.NameConstant, lambda e: expr.Atom(e.value))
register_expr(ast.Num, lambda e: expr.Atom(e.n))
register_expr(ast.Set, lambda e: expr.Set([*emap(e.elts)]))
register_expr(ast.Str, lambda e: expr.Atom(e.s))
register_expr(ast.Tuple, lambda e: expr.Tuple([*emap(e.elts)]))
register_expr(ast.Dict, lambda e: expr.Dict([*zip(emap(e.keys), emap(e.values))]))

# Simple statement handlers
register_stmt(ast.Return, lambda s: stmt.Return(to_expr(s.value)))
register_stmt(ast.Break, lambda s: stmt.Break())
register_stmt(ast.Continue, lambda s: stmt.Continue())

# Programmatically register functions
for ast_op, op in OPERATOR_MAP.items():
    register_expr(ast_op, cte(op))


# Complex translations
@register_expr(ast.Call)
def _(e):
    func = to_expr(e.func)
    args = [*map(to_expr, e.args)]
    kwargs = {kw.arg: to_expr(kw.value) for kw in e.keywords}
    return expr.Call(func, args, kwargs)


@register_expr(ast.BoolOp)
def _(e):
    op = OPERATOR_MAP[type(e.op)]
    *values, x, y = e.values
    res = expr.BinOp(op, to_expr(x), to_expr(y))
    while values:
        res = expr.BinOp(op, to_expr(values.pop()), res)
    return res


@register_expr(ast.Compare)
def _(e):
    ops = [OPERATOR_MAP[type(op)] for op in e.ops]
    values = [to_expr(e.left), *map(to_expr, e.comparators)]
    return expr.Compare(ops, values)


@register_stmt(ast.If)
def _(s):
    cond = to_expr(s.test)
    then = stmt.Block(map(to_stmt, s.body))
    other = stmt.Block(map(to_stmt, s.orelse))
    return stmt.If(cond, then, other)


@register_stmt(ast.Delete)
def _(s):
    targets = s.targets
    if len(targets) == 1 and isinstance(targets[0], (ast.List, ast.Tuple)):
        targets = targets[0].elts
    return stmt.Del(map(to_expr, targets))


@register_stmt(ast.Expr)
def _(s):
    if isinstance(s.value, ast.Yield):
        return stmt.Yield(to_expr(s.value.value))
    elif isinstance(s.value, ast.YieldFrom):
        return stmt.YieldFrom(to_expr(s.value.value))
    return stmt.ExprStmt(to_expr(s.value))


@register_stmt(ast.Assign)
def _(s):
    target, = map(to_expr, s.targets)
    if isinstance(s.value, ast.Yield):
        return stmt.YieldAssign(target, to_expr(s.value.value))
    elif isinstance(target, ast.YieldFrom):
        return stmt.YieldFromAssign(target, to_expr(s.value.value))
    return stmt.Assign(target, to_expr(s.value))


@register_stmt(ast.FunctionDef)
def _(s):
    # TODO: better function representation
    # (probably we should use a safer way than what Python does with arguments)
    name = s.name
    a = s.args
    arg_name = a.vararg and a.vararg.arg
    kwarg_name = a.vararg and a.vararg.arg
    kw_args = [arg.arg for arg in a.kwonlyargs]
    kw_defaults = list(map(to_expr, a.kw_defaults))

    defaults = list(map(to_expr, a.defaults))
    args = [arg.arg for arg in a.args]
    kwargs = dict(zip(args[-len(defaults) :], defaults))
    args = args[: len(args) - len(defaults)]
    body = stmt.Block(list(map(to_stmt, s.body)))
    return stmt.Def(name, args, kwargs, body)


@register_stmt(ast.For)
def _(s):
    body = stmt.Block(list(map(to_stmt, s.body)))
    other = stmt.Block(list(map(to_stmt, s.orelse)))
    return stmt.For(to_expr(s.target), to_expr(s.descendants), body, other)


@register_stmt(ast.While)
def _(s):
    body = stmt.Block(list(map(to_stmt, s.body)))
    other = stmt.Block(list(map(to_stmt, s.orelse)))
    return stmt.While(to_expr(s.test), body, other)


@register_stmt(ast.With)
def _(s):
    body = stmt.Block(list(map(to_stmt, s.body)))
    items = []
    for item in s.items:
        name = stmt.Symbol(item.optional_vars and item.optional_vars.id)
        items.append((to_expr(item.context_expr), name))
    return stmt.While(items, body)


print(parse_expr("x + y"))
print(parse_expr("[1 + 2 + 3 - 4]"))
print(parse_expr("[1, 2.0, True, None, NotImplemented]"))
print(parse_expr("[(1, 2), {1, 2}, {1: 2}]"))
print(parse_expr("a * b / c + d @ e % f - h ** i // j"))
print(parse_expr("a | b & c >> d << e"))
print(parse_expr("a and b and c"))
print(parse_expr("a or b or c and d"))
print(parse_expr("a > b >= c < d"))
print(parse_expr("a > b and b < c or a >= b and b <= c"))
print(parse_expr("a == b and a is b or a != b and a is not b"))
print(parse_expr("a if b else c"))
print(parse_expr("..."))
print(parse_expr("a.b.c"))
print(parse_expr("1 + 2j"))
print(parse_expr("'string'"))
# print(parse_expr("fn(x + y, z=1)"))
# print(parse_expr("[a, *b, c]"))
# print(parse_expr("{a, *b, c}"))
# print(parse_expr("{a: b, **c, d: e}"))
# print(parse_expr("f(a, *b, c)"))
# print(parse_expr("f(a, **b)"))
# print(parse_expr("a[b]"))
# print(parse_expr("a[b, c]"))
# print(parse_expr("a[b:c:None,:,...,:]"))
# print(parse_expr("lambda x: y"))

print(parse_stmt("print('hello world')"))
print(parse_stmt("if x:\n    y"))
print(parse_stmt("if x:\n    y\nelse:\n   z"))
print(parse_stmt("return"))
print(parse_stmt("return x"))
print(parse_stmt("del x"))
print(parse_stmt("del x, y"))
print(parse_stmt("del [x, y]"))
print(parse_stmt("del (x, y)"))
print(parse_stmt("yield"))
print(parse_stmt("yield x"))
print(parse_stmt("yield from x"))
print(parse_stmt("x = y"))
print(parse_stmt("x = yield"))
print(parse_stmt("x = yield 42"))
print(parse_stmt("break"))
print(parse_stmt("continue"))
print(parse_stmt("def f(x):\n    x"))
print(parse_stmt("def f(x, y=1):\n    x"))
print(parse_stmt("for x in y:\n    x"))
print(parse_stmt("while x:\n    x"))
print(parse_stmt("with x as y:\n    x"))
