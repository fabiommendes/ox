from .ast_core import ExprLeaf, ExprNode, Expr, StmtNode
from .utils import attr_property, wrap_tokens, from_template

__all__ = [
    "NameMixin",
    "AtomMixin",
    "CommandMixin",
    "BinaryMixin",
    "GetAttrMixin",
    "StmtExprMixin",
]


class NameMixin(ExprLeaf):
    """
    Base class for nodes that represent variable names.

    Name sub-classes are always expressions.
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
    boolean values and thus are better represented by atoms. NotImplemented,
    however, is just a builtin constant (you can reassign it to a different
    value if you want). The default Python AST in ox represents it using a name
    rather than an atom.

    Atom sub-classes are always expressions.
    """

    class Meta:
        abstract = True
        source = str
        types = ()

    @classmethod
    def _meta_finalize(cls):
        # Register valid atomic types into coerce function.
        coerce = cls._meta.coerce
        for kind in cls._meta.types:
            coerce.register(kind)(cls)

    def tokens(self, ctx):
        yield self._meta.source(self.value)


class CommandMixin(ExprNode):
    """
    Command that modifies a single expression (ex.: yield <expr>)
    """

    expr: Expr

    class Meta:
        abstract = True
        command = "{expr}"


class BinaryMixin(ExprNode):
    """
    A command that involves a pair of expressions (ex.: <expr> and <expr>).
    """

    lhs: Expr
    rhs: Expr

    class Meta:
        abstract = True
        command = "{lhs} {rhs}"


class GetAttrMixin(ExprNode):
    """
    Attribute access (<expr>.<name>).
    """

    expr: Expr
    attr: str = attr_property("attr")

    class Meta:
        abstract = True
        command = "{expr}.{attr}"

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
            "expr": wrap_tokens(self.expr.tokens(ctx), self.wrap_expr_with()),
            "attr": [self.attr],
        }
        yield from from_template(self._meta.command, ctx)


#
# Statement mixins
#
class StmtExprMixin(StmtNode):
    """
    Command that modifies a single expression (ex.: yield <expr>)
    """

    expr: Expr

    class Meta:
        abstract = True
        command = "{expr}"

    def wrap_expr_with(self):
        """
        Return True/False/None or a pair of enclosing brackets used to wrap
        expression when generating tokens.
        """
        return False

    def tokens(self, ctx):
        yield from from_template(
            self._meta.command,
            {"expr": wrap_tokens(self.expr.tokens(ctx), self.wrap_expr_with())},
        )
