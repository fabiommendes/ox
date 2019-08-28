from functools import lru_cache
from typing import Type

from sidekick.tree import SExprBase
from .base import AST, Leaf, Node
from .utils import wrap_tokens, from_template, attr_property
from ..operators import BinaryOp, Op


class Expr(AST):
    """
    Base class for AST nodes that represent expressions.

    Most programming languages distinguish between Expressions, syntactic
    constructs that represent values that can be freely composed, and Statements,
    which represent declarations, control flow and generally speaking cannot
    be included inside expressions.

    This class serves as a generic base class for expression nodes for any custom
    language.
    """

    is_expr = True

    class Meta:
        abstract = True

    #
    # Construction of sub-nodes
    #
    def attr(self, attr: str) -> "ExprNode":
        """
        Return an expression node representing ``obj.<attr>``.
        """
        raise NotImplementedError

    def index(self, value) -> "ExprNode":
        """
        Return an expression node representing ``obj[<value>]``.
        """
        raise NotImplementedError

    def call(*args, **kwargs):
        """
        Create expression that calls current value with the given
        positional and keyword arguments.
        """
        self, *args = args
        raise NotImplementedError

    def method(*args, **kwargs):
        """
        Return an expression node equivalent to a calling method with given
        arguments.
        """
        self, method, *args = args
        return self.attr(method).call(*args, **kwargs)

    #
    # Operators
    #
    def binary_op(self, op, other) -> "ExprNode":
        """
        Create a new expression node representing the action of the given
        binary operator acting on the current node.
        """
        raise NotImplementedError

    def unary_op(self, op) -> "ExprNode":
        """
        Creates new expression representing the result of the given unary
        operator acting on the current expression node.
        """
        raise NotImplementedError

    def comparison_op(self, op, other, *args) -> "ExprNode":
        """
        Create a new expression node representing ``self == other``.
        """
        raise NotImplementedError


# ==============================================================================
# LEAF NODES
# ==============================================================================

class ExprLeaf(Leaf, Expr):
    """
    Base class for expression leaf types.
    """

    class Meta:
        abstract = True

    def _repr_as_child(self):
        return self._repr()


class NameMixin(ExprLeaf):
    """
    Base class for nodes that represent variable names.
    """

    class Meta:
        abstract = True
        validate_name = None

    def tokens(self, ctx):
        yield self.value


class AtomMixin(ExprLeaf):
    """
    Base class for nodes that represent atomic types like ints, floats, strings
    etc.

    Only use this class to wrap atomic types that have literal representations
    on the language. Builtin constants usually should be represented as Names.
    In Python, for instance, True and False are reserved words associated with
    some specific value and thus are better represented by atoms. NotImplemented,
    however, is just a builtin constant (you can reassign it to a different
    value if you want). The default Python AST in ox represents it using a name.
    """

    class Meta:
        abstract = True
        source = str
        types = ()

    @classmethod
    def _meta_finalize(cls):
        coerce = cls._meta.coerce
        for kind in cls._meta.types:
            coerce.register(kind)(cls)

    def tokens(self, ctx):
        yield self._meta.source(self.value)


# ==============================================================================
# REGULAR NODES
# ==============================================================================

class ExprNode(Node, SExprBase, Expr):
    """
    Base class for expression node types.
    """

    class Meta:
        abstract = True

    __eq__ = SExprBase.__eq__

    def _repr(self, children=True):
        return Node._repr(self, children=children)

    def __repr__(self):
        args = []
        for attr in self._meta.annotations:
            args.append(repr(getattr(self, attr)))
        args = ', '.join(args)
        return f'{self.__class__.__name__}({args})'


class SingleCommandMixin(ExprNode):
    """
    A simple command that modifies a single expression (ex.: yield <expr>)
    """
    expr: Expr

    class Meta:
        abstract = True
        command = "{expr}"


class GetAttrMixin(ExprNode):
    """
    Attribute access (<expr>.<name>).
    """
    expr: Expr
    attr: str = attr_property('attr')

    class Meta:
        abstract = True
        command = '{expr}.{attr}'

    @classmethod
    def _meta_getattr(cls, expr, attr):
        """
        Implement constructor that creates a attribute access expression.
        """
        return cls(expr, attr)

    def wrap_expr_with(self):
        """
        Return a pair of parenthesis or other enclosing brackets.

        Must return True, False or a pair of enclosing tokens.
        """
        return False

    def tokens(self, ctx):
        ctx = {
            'expr': wrap_tokens(self.expr.tokens(ctx), self.wrap_expr_with()),
            'attr': [self.attr],
        }
        yield from from_template(self._meta.command, ctx)


class UnaryOpMixin(ExprNode):
    """
    Unary operator (ex.: +<expr>)
    """
    op: Op
    expr: Expr

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
            ops = binary_class._meta.annotations['op']
            binary_ops.update(op.value for op in ops)

        for op in cls._meta.annotations['op']:
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
            op = self._meta.annotations['op'].from_name(op)
        super().__init__(op, expr, **kwargs)


class BinaryMixin(ExprNode):
    """
    A command that involves a pair of expressions (ex.: <expr> and <expr>).
    """
    lhs: Expr
    rhs: Expr

    class Meta:
        abstract = True
        command = "{lhs} {rhs}"


class BinaryOpMixin(ExprNode):
    """
    A binary operator (ex.: <expr> + <expr>).
    """
    op: BinaryOp
    lhs: Expr
    rhs: Expr

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
            ops = unary_class._meta.annotations['op']
            unary_ops.update(op.value for op in ops)

        for op in cls._meta.annotations['op']:
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
        cls.operators = cls._meta.annotations['op']

    def __init__(self, op, lhs, rhs, **kwargs):
        if isinstance(op, str):
            op = self._meta.annotations['op'].from_name(op)
        super().__init__(op, lhs, rhs, **kwargs)


#
# Utility functions
#
@lru_cache(250)
def unary_operator_sexpr(cls: Type[UnaryOpMixin], op):
    """
    Create an S-expr constructor for the given unary operator.

    Args:
        cls (type):
            UnaryOpMixin subclass.
        op:
            String description or enum item associated with the bound operator.
    """
    if isinstance(op, str):
        return unary_operator_sexpr(cls, cls._meta.annotations['op'].from_name(op))
    to_expr = cls._meta.coerce

    def constructor(expr, **kwargs):
        expr = to_expr(expr)
        return cls(op, expr, **kwargs)

    return constructor


@lru_cache(250)
def binary_operator_sexpr(cls: Type[BinaryOpMixin], op):
    """
    Create an S-expr constructor for the given binary operator.

    Args:
        cls (type):
            BinaryOpMixin subclass.
        op:
            String description or enum item associated with the bound operator.
    """
    if isinstance(op, str):
        return binary_operator_sexpr(cls, cls._meta.annotations['op'].from_name(op))
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
def flexible_operator_sexpr(binary_cls: Type[BinaryOpMixin],
                            unary_cls: Type[UnaryOpMixin], op):
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
