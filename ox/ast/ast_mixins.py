from sidekick import Just, Maybe, Node
from .ast_core import ExprLeaf, ExprNode, Expr, StmtNode, Stmt
from .utils import attr_property, from_template

__all__ = [
    "NameMixin",
    "AtomMixin",
    "VoidMixin",
    "CommandMixin",
    "BinaryMixin",
    "GetAttrMixin",
    "StmtExprMixin",
    "BlockMixin",
]


class NameMixin(ExprLeaf):
    """
    Base class for nodes that represent variable names.

    Name sub-classes are always expressions.
    """

    class Meta:
        abstract = True
        validate_name = None

    def __init__(self, value, **kwargs):
        if isinstance(value, NameMixin):
            value = value.value
        super().__init__(value, **kwargs)

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

    has_static_value = True

    class Meta:
        abstract = True
        types = ()

    @classmethod
    def _meta_finalize(cls):
        # Register valid atomic types into coerce function.
        coerce = cls._meta.coerce
        for kind in cls._meta.types:
            coerce.register(kind)(cls)

    def static_value(self) -> Maybe:
        return Just(self.value)

    def tokens(self, ctx):
        yield str(self.value)


class VoidMixin(ExprLeaf):
    """
    Represents an empty node.

    This might be useful to use in places that may require optional nodes.
    """

    class Meta:
        abstract = False

    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)

    def __bool__(self):
        return False

    def tokens(self, ctx):
        yield from ()

    def copy(self):
        return type(self)(**self._attrs)


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

    def tokens(self, ctx):
        yield from from_template(
            self._meta.command,
            {"expr": self.child_tokens(self.expr, "expr", ctx), "attr": [self.attr]},
        )


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

    def tokens(self, ctx):
        expr = self.child_tokens(self.expr, "expr", ctx)
        yield ctx.start_line()
        yield from from_template(self._meta.command, {"expr": expr})


class BlockMixin(Node, Stmt):
    """
    A block of sequential statements.
    """

    class Meta:
        abstract = True
        line_end = ""
        block_separators = ["", ""]

    def tokens(self, ctx):
        children = iter(self.children)
        line_end = self._meta.line_end

        try:
            first = next(children)
            yield from first.tokens(ctx)
            yield line_end
        except StopIteration:
            yield from self.tokens_empty_block(ctx)
        for child in children:
            yield "\n"
            yield from child.tokens(ctx)
            yield line_end

    def tokens_empty_block(self, ctx):
        """
        Yield tokens if block is empty.
        """
        yield from ()

    def tokens_as_block(self, ctx):
        """
        Return tokens rendering children as an indented block of statements.

        Respect language block syntax conventions (e.g.,  Python uses semi-colon
        followed by indentation, while C-family uses braces and indentation).
        """
        start, end = self._meta.separators
        yield start
        yield "\n"
        ctx.indent()
        yield from self.tokens(ctx)
        ctx.dedent()
        yield end
        yield "\n"
