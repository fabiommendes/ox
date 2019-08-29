from inspect import Parameter

from .nodes_expr import Expr, Name, Lambda, expr

__all__ = ["e", "fn", "λ", "signature"]


class ExpressionMagic:
    """
    Magic expression object:

        e.x      <==> Name('x')
        e['x.y'] <==> Name('x').attr('y')
        e[value] <==> expr(value)
        e(arg)   <==> expr(arg)
    """

    def __init__(self, *, to_expr, to_name, mk_expr):
        self.__mk_expr = mk_expr
        self.__to_expr = to_expr
        self.__to_name = to_name

    def __call__(self, x):
        if isinstance(x, self.__mk_expr):
            return x
        else:
            return self.__to_expr(x)

    def __getattr__(self, name):
        return self.__to_name(name)

    def __getitem__(self, x):
        if isinstance(x, self.__mk_expr):
            return x
        elif isinstance(x, str):
            if "." in x:
                first, *rest = x.split()
                res = self.__to_name(first)
                for r in rest:
                    res = res.attr(r)
                return res
            return self.__to_name(x)
        else:
            return self.__to_expr(x)


class LambdaMagic:
    """
    Creates a lambda expression.

        fn(e.x, y=42)[e.x + e.y] <==> e(lambda x, y: x + y)
    """

    def __init__(self, *, to_expr, to_name, mk_lambda):
        self.__to_name = to_name
        self.__to_expr = to_expr
        self.__to_lambda = mk_lambda

    def __call__(self, *args, **kwargs):
        name = self.__to_name
        expr = self.__to_expr
        self.args = list(map(name, args))
        self.kwargs = {name(k): expr(v) for k, v in kwargs.items()}

    def __getitem__(self, value):
        return self.__to_lambda(self.args, self.kwargs, self.__to_expr(value))


def ternary(cond, then, other):
    """
    Creates a Python if expression of the form "<value> if <if_> else <else_>"

    Usage:
        >>> ternary(e.x > 0, e.x, 0)  # x if x > 0 else 0
        Ternary(BinOp(Op.GT, Name('x'), Int(0)), Name('x'), Int(0))

    Args:
        cond:
            The default value expression.
        then:
            The condition expression.
        other:
            The alternate expression.

    Returns:
        A Expr.IfExpr value.
    """
    return Ternary(
        cond if isinstance(cond, Expr) else e(cond),
        then if isinstance(cond, Expr) else e(then),
        other if isinstance(other, Expr) else e(other),
    )


def signature(*args, **kwargs):
    """
    Create a signature object representing a function definition.
    """
    kind = Parameter.POSITIONAL_ONLY
    params = []

    for arg in args:
        if isinstance(arg, (str, Symbol)):
            if arg == "*":
                kind = Parameter.KEYWORD_ONLY
                continue
            param = Parameter(str(arg), kind=kind)
        elif isinstance(arg, (str, Name)):
            param = Parameter(str(arg.value), kind=kind)
        else:
            raise TypeError(arg)
        params.append(param)

    if kind == Parameter.POSITIONAL_ONLY:
        kind = Parameter.POSITIONAL_OR_KEYWORD
    for name, value in kwargs.items():
        value = expr(value)
        param = Parameter(name, default=value, kind=kind)
        params.append(param)

    return Signature(params)


#
# Magic objects
#
e = ExpressionMagic(to_expr=expr, to_name=Name, mk_expr=Expr)
λ = fn = LambdaMagic(to_expr=expr, to_name=Name, mk_lambda=Lambda)

if __name__ == "__main__":
    from .nodes_stmt import *

    code = Block(
        [
            Import("math"),
            Import("math", "m"),
            ImportFrom("math")["cos", "sin":"func"],
            Break(),
            Continue(),
            Return(Name("x")),
            Yield(Name("x")),
            YieldFrom(Name("x")),
        ]
    )
    print(code.source())

    x = e["x"]
    y = e["y"]

    code = (
        If(x > y)(Assign((x, y), (y, x)), Return(42))
        .Elif(x < y)(Return(y))
        .Elif(x == 2)(e.print(x), e.print(y))
        .Else(
            For(x, y, Block([Assign(x, y)]), Block([Assign(x, y + 1)])),
            With(x, y, Block([Assign(x, y)])),
            Def(x, [y], {}, Block([Assign(x, y)])),
            Class(x, [y], {}, Block([Assign(x, y)])),
        )
    )

    code = If(x > 2)(Let(x=1, y=2), Return(x)).Elif(x < 2)(Yield()).Else(Let(x=1))

    print()
    print()
    print(repr(code))
    print(code.source())
