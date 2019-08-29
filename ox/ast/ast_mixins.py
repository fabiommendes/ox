from typing import Type

from .ast_core import ExprLeaf, ExprNode, Expr
from .utils import attr_property, wrap_tokens, from_template, \
    unary_operator_sexpr, \
    binary_operator_sexpr, \
    flexible_operator_sexpr
from ..operators import Op, BinaryOp


class NameMixin(ExprLeaf):
    """
    Base class for nodes that represent variable names.
    """

    class Meta:
        abstract = True
        validate_name = None

    def tokens(self, ctx):
        yield self.value

    def free_vars(self, include=(), exclude=()):
        xs = {self.value}
        xs.difference_update(exclude)
        return xs


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
