from typing import Union

from sidekick import curry
from .operators import UnaryOp as UnaryOpEnum, BinaryOp as BinaryOpEnum
from ... import ast
from ...ast.utils import wrap_tokens

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


expr = Expr._meta.coerce
register_expr = curry(2, expr.register)


# ==============================================================================
# LEAF NODES
# ==============================================================================

class ExprLeaf(Expr, ast.ExprLeaf):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        root = Expr
        abstract = True


class Atom(ExprLeaf, ast.AtomMixin):
    """
    Atomic data such as numbers, strings, etc.

    Value is always known statically and is represented by the corresponding
    Python value.
    """

    class Meta:
        # root = Expr
        types = PyAtom

    def _repr_as_child(self):
        return self._repr()

    def tokens(self, ctx):
        yield "..." if self.value is ... else repr(self.value)


class Name(ExprLeaf, ast.NameMixin):
    """
    Represent a Python name
    """

    class Meta:
        types = str,

    def _repr_as_child(self):
        return self._repr()


# ==============================================================================
# REGULAR NODES
# ==============================================================================

class ExprNode(Expr, ast.ExprNode):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        root = Expr
        abstract = True


class And(ExprNode):
    """
    Short-circuit "and" operator.
    """
    lhs: Expr
    rhs: Expr

    class Meta:
        sexpr_symbol = 'and'


class Or(ExprNode):
    """
    Short-circuit "or" operator.
    """
    lhs: Expr
    rhs: Expr

    class Meta:
        sexpr_symbol = 'or'


class UnaryOp(ExprNode, ast.UnaryOpMixin):
    """
    Unary operators like +, -, ~ and not.
    """
    op: UnaryOpEnum
    expr: Expr

    class Meta:
        sexpr_skip = ('+', '-')

    def tokens(self, ctx):
        yield self.op.value
        yield from self.expr.tokens(ctx)


class BinOp(ExprNode, ast.BinaryOpMixin):
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
