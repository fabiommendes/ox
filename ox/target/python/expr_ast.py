from typing import Union, Optional

import ox.ast.ast_mixins
from ox.ast import Tree
from sidekick import curry
from .operators import UnaryOp as UnaryOpEnum, BinaryOp as BinaryOpEnum
from ... import ast
from ...ast.utils import wrap_tokens, attr_property

PyAtom = (type(None), type(...), bool, int, float, complex, str, bytes)
PyAtomT = Union[None, bool, int, float, complex, str, bytes]  # ..., NotImplemented
PyContainerT = Union[list, tuple, set, dict]


class Expr(ast.Expr):
    """
    Base class for Python AST nodes that represent expressions.
    """

    class Meta:
        root = True
        abstract = True


class ExprLeaf(Expr, ast.ExprLeaf):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        abstract = True


class ExprNode(Expr, ast.ExprNode):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        abstract = True


expr = Expr._meta.coerce
register_expr = curry(2, expr.register)


# ==============================================================================
# LEAF NODES
# ==============================================================================


class Atom(ExprLeaf, ox.ast.ast_mixins.AtomMixin):
    """
    Atomic data such as numbers, strings, etc.

    Value is always known statically and is represented by the corresponding
    Python value.
    """

    class Meta:
        types = PyAtom

    def _repr_as_child(self):
        return self._repr()

    def tokens(self, ctx):
        # Ellipisis is repr'd as "Ellipisis"
        yield "..." if self.value is ... else repr(self.value)


class Name(ExprLeaf, ox.ast.ast_mixins.NameMixin):
    """
    Represent a Python name
    """

    class Meta:
        types = (str,)


# ==============================================================================
# REGULAR NODES
# ==============================================================================


class And(ExprNode):
    """
    Short-circuit "and" operator.
    """

    lhs: Expr
    rhs: Expr

    class Meta:
        sexpr_symbol = "and"


class Or(ExprNode):
    """
    Short-circuit "or" operator.
    """

    lhs: Expr
    rhs: Expr

    class Meta:
        sexpr_symbol = "or"


class UnaryOp(ExprNode, ox.ast.ast_mixins.UnaryOpMixin):
    """
    Unary operators like +, -, ~ and not.
    """

    op: UnaryOpEnum
    expr: Expr

    class Meta:
        sexpr_skip = ("+", "-")

    def tokens(self, ctx):
        yield self.op.value
        yield from self.expr.tokens(ctx)


class BinOp(ExprNode, ox.ast.ast_mixins.BinaryOpMixin):
    """
    Regular binary operators like for arithmetic and bitwise arithmetic
    operations. It excludes comparisons and bitwise operations since they are
    treated differently by Python grammar.
    """

    op: BinaryOpEnum
    lhs: Expr
    rhs: Expr

    class Meta:
        sexpr_unary_op_class = UnaryOp

    def check_wrap(self, other):
        if isinstance(other, BinOp):
            return self.precedence_level < other.precedence_level
        elif isinstance(other, (UnaryOp, And, Or)):
            return True
        return False

    def tokens(self, ctx):
        wrap = self.check_wrap(self.lhs)
        yield from wrap_tokens(self.lhs.tokens(ctx), wrap=wrap)
        yield f" {self.op.value} "
        wrap = self.check_wrap(self.rhs)
        yield from wrap_tokens(self.rhs.tokens(ctx), wrap=wrap)


class GetAttr(ExprNode, ox.ast.ast_mixins.GetAttrMixin):
    """
    Get attribute expression.
    """

    expr: Expr
    attr: str

    def wrap_expr_with(self):
        expr = self.expr
        if isinstance(expr, (BinOp, UnaryOp, And, Or)):
            return True
        if isinstance(expr, Atom) and isinstance(expr.value, (int, float, complex)):
            return True
        return False


class Call(ExprNode):
    """
    Call expression with argument list.
    """

    expr: Expr
    args: Tree

    @classmethod
    def make_args(*args, **kwargs):
        """
        Create args list from positional and keyword arguments.
        """
        cls, *args = args
        children = list(cls._yield_args(args, kwargs))
        return Tree("args", children)

    @classmethod
    def _yield_args(cls, args, kwargs):
        for arg in args:
            if isinstance(arg, str):
                if arg.startswith("**"):
                    yield Arg(Name(arg[2:]), name=None, stars=2)
                elif arg.startswith("*"):
                    yield Arg(Name(arg[1:]), name=None, stars=1)
                else:
                    raise ValueError(f"invalid argument specification {arg!r}")
            else:
                yield arg
        for name, value in kwargs.items():
            yield Arg(value, name=name, stars=0)

    @classmethod
    def from_args(*args, **kwargs):
        cls, expr, *args = args
        args = cls.make_args(*args, **kwargs)
        return cls(expr, args)

    _meta_fcall = from_args

    def wrap_arg(self, arg):
        """
        Return true if it must wrap argument in parenthesis.
        """
        return False

    def tokens(self, ctx):
        expr = self.expr
        if isinstance(expr, (BinOp, UnaryOp, And, Or)):
            yield from wrap_tokens(self.expr.tokens(ctx))
        elif isinstance(expr, Atom) and isinstance(expr.value, (int, float, complex)):
            yield from wrap_tokens(self.expr.tokens(ctx))
        else:
            yield from self.expr.tokens(ctx)

        children = iter(self.args.children)

        yield "("
        try:
            arg = next(children)
        except StopIteration:
            pass
        else:
            yield from arg.tokens(ctx)
            for arg in children:
                yield ", "
                yield from arg.tokens(ctx)
        yield ")"


class Arg(ExprNode):
    """
    Represents an argument in a function call.
    """

    expr: Expr
    name: Optional[str] = attr_property("name")
    stars: int = attr_property("stars")

    def tokens(self, ctx):
        if self.name:
            yield self.name
            yield "="
        elif self.stars:
            yield "*" * self.stars
        yield from self.expr.tokens(ctx)


class Yield(ExprNode):
    """
    "yield" expression.
    """

    expr: Expr
    _command = "yield"

    def tokens(self, ctx):
        yield "("
        yield self._command + " "
        if not isinstance(self.expr, Atom) or self.expr.value is not None:
            yield from self.expr.tokens(ctx)
        yield ")"


class YieldFrom(Yield):
    """
    "yield from" Expression.
    """

    expr: Expr
    _command = "yield from"
