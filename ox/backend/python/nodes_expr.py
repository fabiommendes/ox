from typing import List as ListOf, Tuple as TupleOf, Dict as DictOf


class Container(Data):
    """
    Base class for tuples, lists, dicts and sets.
    """

    children: ListOf[Expr]
    separators = None
    is_empty = property(lambda self: len(self.value) == 0)

    def tokens_for_context(self, ctx):
        a, b = self.separators
        n = len(self.children)

        yield a
        if n:
            stream = iter(self.children)
            yield from next(stream).tokens(ctx)
            for item in stream:
                yield ", "
                yield from item.tokens(ctx)
        if isinstance(self, Tuple) and n == 1:
            yield ","
        yield b


class Tuple(Container):
    """
    Tuple literals.
    """

    children: ListOf[Expr]
    separators = "()"


class List(Container):
    """
    List literals.
    """

    children: ListOf[Expr]
    separators = "[]"


class Set(Container):
    """
    Set literals.
    """

    children: ListOf[Expr]
    separators = "{}"

    def tokens_for_context(self, ctx):
        if self.is_empty:
            yield "set()"
        else:
            yield from super().tokens_for_context(ctx)


class Dict(Container):
    """
    Dict literals.
    """

    children: ListOf[TupleOf[Expr, Expr]]
    separators = "{}"

    def tokens_for_context(self, ctx):
        a, b = self.separators
        n = len(self.value)

        yield a
        if n:
            stream = iter(self.value)
            k, v = next(stream)
            yield from k.tokens(ctx)
            yield ": "
            yield from v.tokens(ctx)

            for k, v in stream:
                yield ", "
                yield from k.tokens(ctx)
                yield ": "
                yield from v.tokens(ctx)
        yield b


# Operators and function calls
class Compare(Expr):
    """
    Chains of comparison operators.

    It is necessary to distinguish Compare() from BinOp() since the first accept
    arbitrary chains of comparison operations like (a < b < c).
    """

    ops: ListOf[Op]
    operands: ListOf[Expr]
    precedence = Op.EQ.precedence_level

    def __init__(self, ops, operands, **kwargs):
        if len(ops) == 0 and len(ops) < len(operands) + 1:
            raise ValueError("expect exactly 1 extra operand after operators")
        ops = [*map(Op.from_name, ops)]
        operands = [x if isinstance(x, Expr) else expr(x) for x in operands]
        super().__init__(ops, operands, **kwargs)

    def tokens_for_context(self, ctx):
        item, tail = uncons(self.operands)
        wrap = precedence_wrap(item, self.precedence)
        yield from wrap_tokens(item.tokens(ctx), wrap=wrap)
        for op, item in zip(self.ops, tail):
            yield f" {op.value} "
            wrap = precedence_wrap(item, self.precedence)
            yield from wrap_tokens(item.tokens(ctx), wrap=wrap)


class Ternary(Expr):
    cond: Expr
    then: Expr
    other: Expr
    precedence = Op.OR_.precedence_level - 1

    def tokens_for_context(self, ctx):
        cond, then, other = self.cond, self.then, self.other
        yield from wrap_tokens(
            then.tokens(ctx), wrap=isinstance(then, Ternary)
        )
        yield " if "
        yield from wrap_tokens(
            cond.tokens(ctx), wrap=isinstance(cond, Ternary)
        )
        yield " else "
        yield from other.tokens(ctx)


class GetItem(Expr):
    value: Expr
    index: Expr

    def tokens_for_context(self, ctx):
        wrap = wrap_value(self.value)
        yield from wrap_tokens(self.value.tokens(ctx), wrap=wrap)
        yield from wrap_tokens(self.index.tokens(ctx), "[]", wrap=wrap)


# # Comprehensions
# ListComp(Expr):
#     ('item', Expr),
#     ('vars', Expr),
#     ('seq', Expr),
#     ('cond', Expr),
# ])
# SetComp(Expr):
#     ('item', Expr),
#     ('vars', Expr),
#     ('seq', Expr),
#     ('cond', Expr),
# ])
# Generator(Expr):
#     ('item', Expr),
#     ('vars', Expr),
#     ('seq', Expr),
#     ('cond', Expr),
# ])
# DictComp(Expr):
#     ('key', Expr),
#     ('value', Expr),
#     ('vars', Expr),
#     ('seq', Expr),
#     ('cond', Expr),
# ])

# Lambdas
class Lambda(Expr):
    args: ListOf[Name]
    kwargs: DictOf[Name, Expr]
    body: Expr

    def __init__(self, args=None, kwargs=None, body=None, **extra):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        if body is None:
            body = Atom(None)
        super().__init__(args, kwargs, body, **extra)

    def tokens_for_context(self, ctx):
        pos_args = ", ".join(map(str, self.args))
        kw_args = ", ".join(f"{k}={v.source(ctx)}" for k, v in self.kwargs.items())
        args = ", ".join(filter(None, [pos_args, kw_args]))
        yield f"lambda {args}: " if args else "lambda: "
        yield from self.body.tokens(ctx)


no_wrap = (Call, GetItem, GetAttr, Container, Name)

# equal = mk_expr_binary_op(Op.EQ)
# not_equal = mk_expr_binary_op(Op.NE)
