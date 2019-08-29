from functools import singledispatch
from inspect import Signature
from typing import List as ListOf, Dict as DictOf, Optional, Union, Any, Tuple

from sidekick import fn

from .nodes_expr import Expr, Name, Atom, expr as to_expr, register as expr_register
from ox.target.python.operators import Inplace
from ..core_nodes import StmtNode
from ..helpers import LetMagic

Symbol = str
NOT_GIVEN = object()


class DescriptorMeta(type):
    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        else:
            return self(instance)


class Stmt(StmtNode):
    """
    Represent Python statements.
    """

    _to_expr = lambda _, x: x if isinstance(x, Expr) else to_expr(x)
    _to_stmt = lambda _, x: x if isinstance(x, Stmt) else stmt(x)


# Definitions
class BodyMixin:
    body: "Block"
    other: "Block"
    _other_block_name: str = "else"

    def tokens_for_context(self, ctx):
        yield ":\n"
        yield from self.body.tokens_for_context(ctx, indent=True)

        try:
            other = self.other
            if not other:
                raise AttributeError
        except AttributeError:
            pass
        else:
            yield "\n"
            yield ctx.start_line()
            yield self._other_block_name
            yield ":\n"
            yield from self.other.tokens_for_context(ctx, indent=True)


class SimpleMixin(StmtNode):
    command: str = None

    def tokens_for_context(self, ctx):
        cmd = self.command or type(self).__name__.lower()
        yield ctx.start_line() + cmd


class ExprMixin(Stmt):
    expr: Expr
    command = property(lambda self: type(self).__name__.lower())
    _default = NOT_GIVEN

    def __init__(self, expr: Any = NOT_GIVEN, **kwargs):
        if expr is NOT_GIVEN:
            if self._default is NOT_GIVEN:
                raise TypeError("missing required first argument")
            expr = self._to_expr(self._default)
        super().__init__(self._to_expr(expr), **kwargs)

    def tokens_for_context(self, ctx):
        cmd = self.command
        yield ctx.start_line() + cmd
        if self.expr != self._default:
            if cmd:
                yield " "
            yield from self.expr.tokens(ctx)


class Block(Stmt):
    """
    A block of commands.

    Usually this is initialized indirectly as a child of another Node. A block
    can also be used to represent a sequence of statements or a module
    definition.

    Examples:
        mod = Block([
            ImportFrom("math")['sin', 'cos'],        # from math import sin, cos
            ImportFrom("random")['random'],          # from random import random
            let(x=e.random(),                        # x = random()
                one=e.cos(x**2) + e.sin(e.x**2)),    # one = cos(x**2) + sin(x**2)
        ])
    """

    data: ListOf[Stmt]

    def __init__(self, data=(), **kwargs):
        super().__init__(list(data), **kwargs)

    def __setitem__(self, i, item) -> None:
        self.data[i] = stmt(i)

    def __delitem__(self, i) -> None:
        del self.data[i]

    def __getitem__(self, i) -> Stmt:
        if isinstance(i, int):
            return self.data[i]

        items = [i] if not isinstance(i, (tuple, list)) else i
        convert = self._convert_item
        for item in items:
            self.append(convert(item))
        return self

    def __len__(self) -> int:
        return len(self.data)

    def __bool__(self):
        return bool(self.data)

    def _convert_item(self, item):
        if isinstance(item, slice):
            lhs = item.start
            rhs = to_expr(item.stop)
            after = item.step

            if isinstance(lhs, str):
                if lhs in EXPR_STATEMENTS:
                    if after is not None:
                        raise ValueError(f"Illegal step: {after}")
                    return EXPR_STATEMENTS[lhs](rhs)
                elif lhs in VOID_STATEMENTS:
                    if rhs is not None or after is not None:
                        raise ValueError(f"Illegal value: {rhs or after}")
                    return VOID_STATEMENTS[lhs]()
                else:
                    lhs = Name(lhs)

            elif after:
                raise ValueError(f"Illegal step: {after}")
            return Assign(to_expr(lhs), to_expr(item.stop))
        return stmt(item)

    def insert(self, index: int, obj: Stmt) -> None:
        self.data.insert(index, stmt(obj))

    def tokens_for_context(self, ctx, indent=False):
        if indent:
            ctx.indent()

        if not self.data:
            yield ctx.start_line() + "pass"
        else:
            stream = iter(self.data)
            yield from next(stream).tokens_for_context(ctx)

            for node in stream:
                yield "\n"
                if isinstance(node, (Class, Def, DefFull)):
                    yield "\n"
                yield from node.tokens_for_context(ctx)

        if indent:
            ctx.dedent()


class Class(BodyMixin, Stmt):
    """
    A class definition.

    Examples:
        Class['Point'](                          # class Point:
            Def['__init__'](e.self, e.x, e.y)(   #     def __init__(self, x, y):
                let(self__x=e.x,                 #         self.x = x
                    self__y=e.y)                 #         self.y = y
            )
        )
    """

    name: Name
    bases: ListOf[Expr]
    options: DictOf[Name, Expr]
    body: Block

    def tokens_for_context(self, ctx):
        yield ctx.start_line() + f"class {self.name}"
        args = ", ".join(map(str, self.bases))
        kwargs = ", ".join(f"{k}={v}" for k, v in self.options.items())
        bases = ", ".join(filter(None, [args, kwargs]))
        yield f"({bases})" if bases else ""
        yield from super().tokens_for_context(ctx)


class Def(BodyMixin, Stmt):
    """
    A function definition.
    """

    name: Name
    args: ListOf[Name]
    kwargs: DictOf[Name, Expr]
    body: Block

    def tokens_for_context(self, ctx):
        yield ctx.start_line() + f"def {self.name}("
        args = ", ".join(map(str, self.args))
        kwargs = ", ".join(f"{k}={v}" for k, v in self.kwargs.items())
        yield ", ".join(filter(None, [args, kwargs]))
        yield ")"
        yield from super().tokens_for_context(ctx)


class DefFull(Stmt):
    name: Name
    signature: Signature
    body: Block


# Simple statements
class Assign(Stmt):
    """
    Simple assignment statement. (e.g., x = y)
    """

    lhs: Expr
    rhs: Expr
    expr = property(lambda self: self.rhs)

    def __init__(self, lhs, rhs, **kwargs):
        super().__init__(to_expr(lhs), to_expr(rhs), **kwargs)

    def tokens_for_context(self, ctx):
        yield from yield_op_statement_tokens(self, " = ", ctx)


class OpAssign(Stmt):
    """
    Complex assignment statement with inplace operator (e.g., x += 1)
    """

    op: Inplace
    lhs: Expr
    rhs: Expr
    expr = property(lambda self: self.rhs)

    def tokens_for_context(self, ctx):
        yield from yield_op_statement_tokens(self, f" {self.op.value} ", ctx)


class YieldAssign(Stmt):
    """
    Assignment from "yield" statement (e.g., x = yield other)
    """

    lhs: Name
    rhs: Expr
    expr = property(lambda self: self.rhs)

    def tokens_for_context(self, ctx):
        yield from yield_op_statement_tokens(self, f" = yield ", ctx)


class YieldFromAssign(Stmt):
    """
    Assignment from "yield from" statement (e.g., x = yield from other)
    """

    lhs: Name
    rhs: Expr
    expr = property(lambda self: self.rhs)

    def tokens_for_context(self, ctx):
        yield from yield_op_statement_tokens(self, f" = yield from ", ctx)


class Break(SimpleMixin, Stmt):
    """
    Simple break statement (e.g., break).
    """


class Continue(SimpleMixin, Stmt):
    """
    Simple continue statement (e.g., continue).
    """


class Del(Stmt):
    """
    Del statement (e.g., del value).
    """

    targets: ListOf[Expr]

    def __init__(self, targets, **kwargs):
        targets = list(targets)
        super().__init__(targets, **kwargs)
        if not self.targets:
            raise ValueError("empty target")

    def tokens_for_context(self, ctx):
        item, *rest = self.targets
        yield "del "
        yield from item.tokens(ctx)
        for item in rest:
            yield ", "
            yield from item.tokens(ctx)


class ExprStmt(ExprMixin, Stmt):
    """
    Statement with a single expression child. (e.g., print("hello world")).
    """

    expr: Expr
    command = ""


class Return(ExprMixin, Stmt):
    """
    Return statement. (e.g., return x).
    """

    expr: Expr
    _default = Atom(None)


class Yield(ExprMixin, Stmt):
    """
    Yield statement. (e.g., yield x).
    """

    expr: Expr
    _default = Atom(None)


class YieldFrom(ExprMixin, Stmt):
    """
    Yield from statement. (e.g., yield from x).
    """

    expr: Expr
    command = "yield from"


# Control flow and compound statements
class If(Stmt):
    """
    If statement.

    Examples:
        If(e.x % 2 == 0)(         # if x % 2 == 0:
            Return(e.x // 2),     #     return x // 2
        ).Else(                   # else:
            Return(3 * e.x + 1),  #     return 3 * x + 1
        )
    """

    cond: Expr
    then: Block
    other: Union[Block, "If"]
    __next = None
    __tip = None

    def Elif(self, cond):
        tip = self.__tip or self
        tip.other = tip = If(cond)
        self.__next = "then"
        self.__tip = tip
        return self

    def Else(self, *args, **kwargs):
        tip = self.__tip or self
        tip.other.append(Let(*args, **kwargs))
        return self

    def __new__(cls, cond, *args, **kwargs):
        new = object.__new__(cls)

        if not args or kwargs:
            cond = to_expr(cond)
            new.__init__(cond, Block([]), Block([]))
            new.__next = "then"
            return new
        return new

    def __init__(self, *args, **kwargs):
        if self.__next is None:
            super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        if self.__next is None:
            msg = "can set block only after an If(), Elif() or Else access"
            raise RuntimeError(msg)
        tip = self.__tip or self
        data = Let(*args, **kwargs)
        if self.__next == "then":
            tip.then.append(data)
        self.__next = None
        return self

    def tokens_for_context(self, ctx, command="if"):
        yield ctx.start_line()
        yield command + " "
        yield from self.cond.tokens(ctx)
        yield ":\n"
        yield from self.then.tokens_for_context(ctx, indent=True)

        if isinstance(self.other, If):
            yield "\n"
            yield from self.other.tokens_for_context(ctx, command="elif")
        elif self.other:
            yield "\n"
            yield ctx.start_line()
            yield "else:\n"
            yield from self.other.tokens_for_context(ctx, indent=True)


class For(BodyMixin, Stmt):
    """
    For statement.

    Examples:
        For(e.n, e.range(10))(    # for n in range(10):
            let('S', '+=', e.n),  #     S += n
        ).Else(                   # else:
            e.print("break"),     #     print("break")
        )
    """

    var: Expr
    expr: Expr
    body: Block
    other: Block

    def tokens_for_context(self, ctx):
        yield ctx.start_line() + "for "
        yield from self.var.tokens(ctx)
        yield " in "
        yield from self.expr.tokens(ctx)
        yield from super().tokens_for_context(ctx)


class While(BodyMixin, Stmt):
    """
    While block

    Examples:
        While(e.S < 100)(         # while S < 100:
            Let('S', '+=', e.n),  #     S += n
        )
    """

    expr: Expr
    body: Block
    other: Block

    def tokens_for_context(self, ctx):
        yield ctx.start_line() + "while "
        yield from self.expr.tokens(ctx)
        yield from super().tokens_for_context(ctx)


class With(BodyMixin, Stmt):
    """
    With block

    Examples:
        With(e.open(e.path), 'fd')(      # with open(path) as fd:
            e.fd.write('hello world!')   #     fd.write('hello world!')
        )
    """

    items: ListOf[Tuple[Expr, Optional[Symbol]]]
    body: Block

    def tokens_for_context(self, ctx):
        yield ctx.start_line() + "with "
        for expr, name in self.items:
            yield from self.expr.tokens(ctx)
            if name is not None:
                yield f" as {name}"
        yield from super().tokens_for_context(ctx)


# Imports
class Import(Stmt):
    """
    Import statement

    Examples:
        Import('math')          # import math
        Import('numpy', 'np')   # import numpy as np
    """

    module: Symbol
    name: Name

    def __init__(self, module, name=None, **kwargs):
        if name is None:
            name = Name(str(module))
        super().__init__(module, name, **kwargs)

    def tokens_for_context(self, ctx):
        mod = str(self.module)
        name = str(self.name)
        yield ctx.start_line()
        yield f"import {mod}" if mod == name else f"import {mod} as {name}"


class ImportFrom(Stmt):
    """
    Import statement

    Examples:
        ImportFrom('math')['sin', 'sqrt': 'fn']   # from math import sin, sqrt as fn
    """

    module: Symbol
    names: DictOf[Symbol, Name]

    def __init__(self, module, names=None, **kwargs):
        names = names or {}
        names = {Symbol(k): Name(v) for k, v in names.items()}
        super().__init__(Symbol(module), names, **kwargs)

    def __getitem__(self, item):
        # Getitem, effectively implemented as setitem ;)
        if isinstance(item, slice):
            if item.step is not None:
                raise ValueError("cannot set step value in slice.")
            self.add(item.start, item.stop)
        elif isinstance(item, tuple):
            for x in item:
                self.__getitem__(x)
        else:
            self.add(item)
        return self

    def add(self, name, alias=None):
        alias = alias or name
        self.names[Symbol(name)] = Name(alias)

    def tokens_for_context(self, ctx):
        mod = str(self.module)
        names = ((str(k), str(v)) for k, v in self.names.items())
        parts = [(f"{k} as {v}" if k != v else "k") for k, v in names]
        if not names:
            return

        yield ctx.start_line()
        yield f"from {mod} import "
        data = ", ".join(parts)
        yield f"({data})" if len(parts) != 1 else data


def yield_op_statement_tokens(obj: Stmt, op: str, ctx):
    yield ctx.start_line()
    yield from obj.lhs.tokens(ctx)
    yield op
    yield from obj.rhs.tokens(ctx)


#
# Utilities
#
EXPR_STATEMENTS = {
    "return": Return,
    "yield": Yield,
    "yield from": YieldFrom,
    "del": Del,
}
VOID_STATEMENTS = {"continue": Continue, "break": Break}


@singledispatch
def stmt(x):
    """
    Convert element to a Statement instance.
    """
    try:
        return ExprStmt(to_expr(x))
    except TypeError:
        cls = type(x).__name__
        raise TypeError(f"{cls} cannot be coerced to Statement")


register = fn.curry(2, lambda tt, func: stmt.register(tt)(func))

register(Stmt, lambda x: x)
register(Expr, ExprStmt)
register(list, lambda x: Block(list(map(stmt, x))))
register(tuple, lambda x: Block(list(map(stmt, x))))


@expr_register(StmtNode)
def _(obj):
    msg = "Python statement cannot be converted to expression: %r" % obj
    raise TypeError(msg)


def stmt_list(obj):
    """
    Convert obj into a list of statements.

    Block -> obj.data
    Statement -> [obj]
    List or tuple -> list(obj)
    Other -> [stmt(obj)]
    """
    if isinstance(obj, Block):
        return obj.data
    elif isinstance(obj, Stmt):
        return [obj]
    elif isinstance(obj, (list, tuple)):
        return list(map(stmt, obj))
    else:
        return [stmt(obj)]


#
# Magic objects
#
Let = LetMagic(
    to_name=Name,
    to_expr=to_expr,
    mk_assign=Assign,
    mk_inplace=OpAssign,
    mk_block=Block,
    to_stmt=stmt,
)
