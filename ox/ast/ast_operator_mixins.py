from functools import lru_cache
from typing import Type

from sidekick import alias
from .ast_core import ExprNode, Expr
from ..operators import Op, BinaryOp

__all__ = [
    "BinaryOpMixin",
    "UnaryOpMixin",
    "unary_operator_sexpr",
    "binary_operator_sexpr",
    "flexible_operator_sexpr",
]


class BinaryOpMixin(ExprNode):
    """
    A binary operator (ex.: <expr> + <expr>).
    """

    tag: BinaryOp
    lhs: Expr
    rhs: Expr

    op = alias("_tag")
    operators = BinaryOp
    precedence_level = property(lambda self: self.op.precedence_level)

    class Meta:
        abstract = True
        command = "{lhs} {op} {rhs}"
        sexpr_skip = ()
        sexpr_unary_op_class = None

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        """
        Create a dictionary mapping symbols to the corresponding constructors
        for the given class.
        """
        skip = cls._meta.sexpr_skip
        unary_class: Type[UnaryOpMixin] = cls._meta.sexpr_unary_op_class
        symbol_map = {}
        unary_ops = set()

        if unary_class:
            ops = unary_class._meta.annotations["tag"]
            unary_ops.update(op.value for op in ops)

        for op in cls._meta.annotations["tag"]:
            symbol_map[op] = binary = binary_operator_sexpr(cls, op)
            if op.value in skip:
                pass
            elif op.value in unary_ops:
                fn = flexible_operator_sexpr(cls, unary_class, op.value)
                symbol_map[op.value] = fn
            else:
                symbol_map[op.value] = binary
        return symbol_map

    @classmethod
    def _meta_finalize(cls):
        super()._meta_finalize()
        cls.operators = cls._meta.annotations["tag"]

    def __init__(self, op, lhs, rhs, **kwargs):
        if isinstance(op, str):
            op = self._meta.annotations["tag"].from_name(op)
        super().__init__(op, lhs, rhs, **kwargs)


class UnaryOpMixin(ExprNode):
    """
    Unary operator (ex.: +<expr>)
    """

    tag: Op
    expr: Expr

    op = alias("_tag")

    class Meta:
        abstract = True
        command = "{op} {expr}"
        sexpr_skip = ()
        sexpr_binary_op_class = None

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        """
        Create a dictionary mapping symbols to the corresponding constructors
        for the given class.
        """

        skip = cls._meta.sexpr_skip
        binary_class: Type[BinaryOpMixin] = cls._meta.sexpr_binary_op_class
        symbol_map = {}
        binary_ops = set()

        if binary_class:
            ops = binary_class._meta.annotations["tag"]
            binary_ops.update(op.value for op in ops)

        for op in cls._meta.annotations["tag"]:
            symbol_map[op] = unary = unary_operator_sexpr(cls, op)
            if op.value in skip:
                pass
            elif op.value in binary_ops:
                fn = flexible_operator_sexpr(binary_class, cls, op.value)
                symbol_map[op.value] = fn
            else:
                symbol_map[op.value] = unary
        return symbol_map

    def __init__(self, op, expr, **kwargs):
        if isinstance(op, str):
            op = self._meta.annotations["op"].from_name(op)
        super().__init__(op, expr, **kwargs)


@lru_cache(250)
def unary_operator_sexpr(cls: Type["UnaryOpMixin"], op):
    """
    Create an S-expr constructor for the given unary operator.

    Args:
        cls (type):
            UnaryOpMixin subclass.
        op:
            String description or enum item associated with the bound operator.
    """
    if isinstance(op, str):
        return unary_operator_sexpr(cls, cls._meta.annotations["tag"].from_name(op))
    to_expr = cls._meta.coerce

    def constructor(expr, **kwargs):
        expr = to_expr(expr)
        return cls(op, expr, **kwargs)

    return constructor


@lru_cache(250)
def binary_operator_sexpr(cls: Type["BinaryOpMixin"], op):
    """
    Create an S-expr constructor for the given binary operator.

    Args:
        cls (type):
            BinaryOpMixin subclass.
        op:
            String description or enum item associated with the bound operator.
    """
    if isinstance(op, str):
        return binary_operator_sexpr(cls, cls._meta.annotations["tag"].from_name(op))
    to_expr = cls._meta.coerce

    if op.left_associative:

        def constructor(*args, **kwargs):
            lhs, rhs, *exprs = [to_expr(e) for e in args]
            new = cls(op, lhs, rhs, **kwargs)

            if exprs:
                exprs.reverse()
            while exprs:
                new = cls(op, new, exprs.pop(), **kwargs)
            return new

    else:

        def constructor(*args, **kwargs):
            *exprs, lhs, rhs = [to_expr(e) for e in args]
            new = cls(lhs, rhs, **kwargs)

            while exprs:
                new = cls(op, exprs.pop(), new, **kwargs)
            return new

    return constructor


@lru_cache(250)
def flexible_operator_sexpr(
    binary_cls: Type["BinaryOpMixin"], unary_cls: Type["UnaryOpMixin"], op
):
    """
    Create an S-expr constructor for the given pair of operators. This function
    is needed when the same operator is used both in unary and binary forms
    (e.g., "+").

    Args:
        binary_cls (type):
            BinaryOpMixin subclass.
        unary_cls (type):
            UnaryOpMixin subclass.
        op:
            String description for operator.
    """
    unary = unary_operator_sexpr(unary_cls, op)
    binary = binary_operator_sexpr(binary_cls, op)

    def constructor(*args, **kwargs):
        if len(args) == 1:
            return unary(*args, **kwargs)
        else:
            return binary(*args, **kwargs)

    return constructor
