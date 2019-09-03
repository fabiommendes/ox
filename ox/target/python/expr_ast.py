from typing import Union

from sidekick import curry, uncons, Node
from .operators import UnaryOp as UnaryOpEnum, BinaryOp as BinaryOpEnum, ComparisonOp
from ... import ast
from ...ast import Tree
from ...ast.utils import wrap_tokens, attr_property, intersperse

PyAtom = (type(None), type(...), bool, int, float, complex, str, bytes)
PyAtomT = Union[None, bool, int, float, complex, str, bytes]  # ..., NotImplemented
PyContainerT = Union[list, tuple, set, dict]

__all__ = [
    "Expr",
    "ExprLeaf",
    "ExprNode",
    "to_expr",
    "register_expr",
    "Atom",
    "Name",
    "And",
    "Or",
    "BinOp",
    "UnaryOp",
    "Compare",
    "GetAttr",
    "GetItem",
    "Slice",
    "Call",
    "Ternary",
    "Call",
    "Lambda",
    "ArgDef",
    "Yield",
    "YieldFrom",
    "Container",
    "Tuple",
    "List",
    "Set",
    "Dict",
]


class Expr(ast.Expr):
    """
    Base class for Python AST nodes that represent expressions.
    """

    class Meta:
        root = True
        abstract = True

    def attr(self, attr: str) -> "Expr":
        return GetAttr(self, attr)

    def index(self, value) -> "Expr":
        return ...  # TODO

    def binary_op(self, op, other: "Expr") -> "Expr":
        op = BinaryOpEnum.from_name(op)
        return BinOp(op, self, other)

    def unary_op(self, op) -> "Expr":
        op = UnaryOpEnum.from_name(op)
        return UnaryOp(op, self)

    def comparison_op(self, op, other, *args) -> "ExprNode":
        return ...  # TODO


class ExprLeaf(ast.ExprLeaf, Expr):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        abstract = True


class ExprNode(ast.ExprNode, Expr):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        abstract = True


class Void(ast.VoidMixin, Expr):
    """
    Empty node.

    Used to represent absence in places that require an optional expression
    node.
    """

    def attr(self, attr: str) -> Expr:
        raise TypeError("invalid operation with void node: getattr")

    def index(self, value) -> Expr:
        raise TypeError("invalid operation with void node: getindex")

    def binary_op(self, op, other) -> Expr:
        raise TypeError("invalid operation with void node: binary operator")

    def unary_op(self, op) -> Expr:
        raise TypeError("invalid operation with void node: unary operator")

    def comparison_op(self, op, other, *args) -> Expr:
        raise TypeError("invalid operation with void node: comparison operator")

    def from_static_children(self):
        return Void()


to_expr = Expr._meta.coerce
register_expr = curry(2, to_expr.register)


# ==============================================================================
# LEAF NODES
# ==============================================================================


class Atom(ast.AtomMixin, ExprLeaf):
    """
    Atomic data such as numbers, strings, etc.

    Value is always known statically and is represented by the corresponding
    Python value.
    """

    class Meta:
        types = PyAtom

    def from_static_children(self, value):
        if isinstance(value, PyAtom):
            return Atom(value, **self._attrs)
        raise TypeError

    def _repr_as_child(self):
        return self._repr()

    def tokens(self, ctx):
        # Ellipsis is repr'd as "Ellipsis"
        yield "..." if self.value is ... else repr(self.value)


class Name(ast.NameMixin, ExprLeaf):
    """
    A Python name
    """

    class Meta:
        types = (str,)

    def from_static_children(self, value):
        return to_expr(value)


# ==============================================================================
# REGULAR NODES
# ==============================================================================


class And(ast.BinaryMixin, ExprNode):
    """
    Short-circuit "and" operator.
    """

    lhs: Expr
    rhs: Expr

    class Meta:
        sexpr_symbol = "and"
        command = "{lhs} and {rhs}"

    def from_static_children(self, lhs, rhs):
        return to_expr(lhs and rhs)


class Or(ast.BinaryMixin, ExprNode):
    """
    Short-circuit "or" operator.
    """

    lhs: Expr
    rhs: Expr

    class Meta:
        sexpr_symbol = "or"
        command = "{lhs} or {rhs}"

    def from_static_children(self, lhs, rhs):
        return to_expr(lhs or rhs)


class UnaryOp(ast.UnaryOpMixin, ExprNode):
    """
    Unary operators like +, -, ~ and not.
    """

    tag: UnaryOpEnum
    expr: Expr

    class Meta:
        sexpr_skip = ("+", "-")

    def tokens(self, ctx):
        yield self.op.value
        yield from self.expr.tokens(ctx)

    def from_static_children(self, child):
        return to_expr(self.tag.function(child))


class BinOp(ast.BinaryOpMixin, ExprNode):
    """
    Regular binary operators like for arithmetic and bitwise arithmetic
    operations. It excludes comparisons and bitwise operations since they are
    treated differently by Python grammar.
    """

    tag: BinaryOpEnum
    lhs: Expr
    rhs: Expr

    class Meta:
        sexpr_unary_op_class = UnaryOp

    def from_static_children(self, lhs, rhs):
        return to_expr(self.tag.function(lhs, rhs))

    def wrap_child_tokens(self, child, role):
        if isinstance(child, BinOp):
            return self.precedence_level > child.precedence_level
        elif isinstance(child, (UnaryOp, And, Or)):
            return True
        return False

    def tokens(self, ctx):
        yield from self.child_tokens(self.lhs, "lhs", ctx)
        yield f" {self.op.value} "
        yield from self.child_tokens(self.rhs, "rhs", ctx)


class Compare(ExprNode):
    """
    Chains of comparison operators.

    It is necessary to distinguish Compare() from BinOp() since the first accept
    arbitrary chains of comparison operations like (a < b < c).
    """

    __slots__ = ("_tag",)
    precedence_level = 3

    @property
    def op_list(self):
        if isinstance(self._tag, ComparisonOp):
            return [self._tag] * (len(self._children) - 1)
        return self._tag

    def __init__(self, tag, children, **kwargs):
        if isinstance(tag, str):
            tag = ComparisonOp.from_name(tag)
        if isinstance(tag, ComparisonOp):
            pass
        elif len(tag) != len(children) - 1:
            raise ValueError(
                "list of operators must be one element smaller than list of operands"
            )
        else:
            tag = list(tag)
        if len(children) < 2:
            raise ValueError("must have at least 2 children")
        self._tag = tag
        Node.__init__(self, children, **kwargs)

    def child_tokens(self, child, role, ctx):
        wrap = isinstance(child, (And, Or))
        yield from wrap_tokens(child.tokens(ctx), wrap)

    def tokens(self, ctx):
        first, rest = uncons(self.child_tokens(x, "child", ctx) for x in self._children)
        yield from first
        for op, item in zip(self.op_list, rest):
            yield f" {op.value} "
            yield from item


class Starred(ExprNode):
    """
    A starred or kw-starred element.

    Can only be present as function arguments or list, set, tuples and dictionary
    elements.
    """

    expr: Expr
    kwstar: bool = False

    def tokens(self, ctx):
        wrap = isinstance(self.expr, (And, Or))
        yield ("**" if self.kwstar else "*")
        yield from wrap_tokens(self.expr.tokens(ctx), wrap)


class Keyword(ExprNode):
    """
    A keyword argument.

    Can only be present as a child of a function call node.
    """

    expr: Expr
    name: str = attr_property("name")

    def __init__(self, expr, name, **kwargs):
        super().__init__(expr, name, **kwargs)

    def tokens(self, ctx):
        yield self.name
        yield "="
        yield from self.expr.tokens(ctx)


class GetAttr(ast.GetAttrMixin, ExprNode):
    """
    Get attribute expression (<expr>.<attr>).
    """

    expr: Expr
    attr: str

    def wrap_child_tokens(self, child, role):
        value = self.expr
        if isinstance(value, (BinOp, UnaryOp, And, Or)):
            return True
        if isinstance(value, Atom) and isinstance(value.value, (int, float, complex)):
            return True
        return False


class GetItem(ExprNode):
    """
    Get item expression (<expr>[<index>])
    """

    expr: Expr
    index: Expr

    def tokens(self, ctx):
        wrap = isinstance(self.expr, (BinOp, UnaryOp, And, Or))
        yield from wrap_tokens(self.expr.tokens(ctx), wrap=wrap)
        yield from wrap_tokens(self.index.tokens(ctx), "[]")


class Slice(ExprNode):
    """
    Slice expression allowed inside GetItem indexes.
    """

    start: Expr
    stop: Expr
    step: Expr

    def __init__(self, start=None, stop=None, step=None, **kwargs):
        start = start or Atom(None)
        stop = stop or Atom(None)
        step = step or Atom(None)
        super().__init__(start, stop, step, **kwargs)

    def tokens(self, ctx):
        is_none = lambda x: isinstance(x, Atom) and x.value is None
        start = self.start
        stop = self.stop
        step = self.step

        if is_none(start) and is_none(stop) and is_none(step):
            yield ":"
            return

        if not is_none(start):
            yield from start.tokens(ctx)
        yield ":"
        if not is_none(stop):
            yield from stop.tokens(ctx)
        yield ":"
        if not is_none(step):
            yield from step.tokens(ctx)


class Call(ExprNode):
    """
    Call expression with argument list.
    """

    expr: Expr
    args: Tree

    # noinspection PyMethodParameters
    @classmethod
    def from_args(*args, **kwargs):
        """
        Create element that represents a function call from positional and
        keyword arguments passed to function.

        This is the same as creating a node with empty arguments, then adding
        values using the add_args() method.
        """
        cls, e, *args = args
        return cls(e, Tree("args", list(generate_call_args(*args, **kwargs))))

    _meta_fcall = from_args

    def add_args(*args, **kwargs):
        """
        Add argument(s) to argument tree. Return a list with new arguments.

        This function accepts several different signatures:

        call.add_args(expr):
            Add a simple argument. Argument must be a valid Python
            expression.
        call.add_args('*', name_or_str):
        call.add_args('*name'):
            Like before, but adds a star argument.
        call.add_args('**', name_or_str):
        call.add_args('**name'):
            Like before, but adds a double start (keyword expansion) argument.
        call.add_args(name=value):
            Add one or more keyword arguments.

        Those signatures can be combined.
        """
        self, *args = args
        args = list(generate_call_args(*args, **kwargs))
        self.args.children.extend(args)
        return args

    def tokens(self, ctx):
        e = self.expr
        if isinstance(e, (BinOp, UnaryOp, And, Or)):
            yield from wrap_tokens(self.expr.tokens(ctx))
        elif isinstance(e, Atom) and isinstance(e.value, (int, float, complex)):
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


def generate_call_args(*args, **kwargs):
    """
    Yield arguments from a function call signature.
    """
    has_keyword = False
    msg = "cannot set positional argument after keyword argument"

    args = iter(args)
    for arg in args:
        if isinstance(arg, str):
            if arg.startswith("**"):
                has_keyword = True
                yield Starred(next(args) if arg == "**" else Name(arg[2:]), kwstar=True)
            elif arg.startswith("*"):
                if has_keyword:
                    raise ValueError(msg)
                yield Starred(next(args) if arg == "*" else Name(arg[1:]))
            else:
                raise TypeError("expect expression, got str")
        else:
            if not isinstance(arg, Expr):
                cls_name = arg.__class__.__name__
                raise TypeError(f"expect expression, got {cls_name}")
            yield arg

    for name, value in kwargs.items():
        yield Keyword(value, name=name)


class Yield(ast.CommandMixin, ExprNode):
    """
    "yield <expr>" expression.
    """

    expr: Expr

    class Meta:
        command = "(yield {expr})"


class YieldFrom(ast.CommandMixin, ExprNode):
    """
    "yield from <expr>" expression.
    """

    expr: Expr

    class Meta:
        command = "(yield from {expr})"


class Lambda(ExprNode):
    """
    Lambda function.
    """

    args: Tree
    expr: Expr

    # noinspection PyMethodParameters
    @classmethod
    def from_args(*args, **kwargs):
        """
        Construct lambda expression from body, *args, **kwargs passed to this
        function.
        """
        cls, expr, *args = args
        return cls(Tree("args", generate_def_args(*args, **kwargs)), expr)

    def tokens(self, ctx):
        if self.args.children:
            yield "lambda "
            yield from intersperse(
                ", ", map(lambda x: x.tokens(ctx), self.args.children)
            )
            yield ": "
        else:
            yield "lambda: "
        yield from self.expr.tokens(ctx)


def generate_def_args(*args, **kwargs):
    """
    Yield arguments from a function (lambda) definition signature.
    """
    args = iter(args)
    for arg in args:
        if arg in "**":
            arg += next(args)
        new = ArgDef.from_expression(arg)
        yield new
    for name, value in kwargs.items():
        yield ArgDef(Name(name), default=value)


class ArgDef(ExprNode):
    """
    Argument definition.
    """

    arg: Expr
    default: Expr
    annotation: Expr

    @classmethod
    def from_expression(cls, expr: Union[Expr, str]):
        """
        Initialize ArgDef from expression or string.
        """
        if isinstance(expr, str):
            if expr.startswith("**"):
                return ArgDef(Starred(Name(expr[2:]), kwstar=True))
            elif expr.startswith("**"):
                return ArgDef(Starred(Name(expr[1:])))
            else:
                return ArgDef(Name(expr))
        elif isinstance(expr, ArgDef):
            return expr
        elif isinstance(expr, Name):
            return ArgDef(expr)
        elif isinstance(expr, Starred):
            return ArgDef(expr)
        elif isinstance(expr, Keyword):
            return ArgDef(Name(expr.name), expr.expr.copy())
        else:
            cls_name = expr.__class__.__name__
            raise TypeError(f"expect expression, got {cls_name}")

    @property
    def name(self):
        if isinstance(self.arg, Name):
            return self.arg.value
        elif isinstance(self.arg, Starred):
            return self.arg.expr.value
        else:
            raise RuntimeError("expression must be a name or starred argument")

    def __init__(self, name, default=None, annotation=None, **kwargs):
        default = Void() if default is None else default
        annotation = Void() if annotation is None else annotation
        super().__init__(name, default, annotation, **kwargs)

    def tokens(self, ctx):
        yield from self.arg.tokens(ctx)
        if self.annotation:
            yield ": "
            yield from self.annotation.tokens(ctx)
            if self.default:
                yield " = "
                yield from self.default.tokens(ctx)
        if self.default:
            yield "="
            yield from self.default.tokens(ctx)

    def __eq__(self, other):
        if (
            not isinstance(other, ArgDef)
            and isinstance(self.default, Void)
            and isinstance(self.annotation, Void)
        ):
            return self.arg == other
        return super().__eq__(other)


class Ternary(ExprNode):
    """
    Ternary operator (<then> if <cond> else <other>)
    """

    cond: Expr
    then: Expr
    other: Expr

    def tokens(self, ctx):
        cond, then, other = self.cond, self.then, self.other
        yield from wrap_tokens(then.tokens(ctx), wrap=isinstance(then, Ternary))
        yield " if "
        yield from wrap_tokens(cond.tokens(ctx), wrap=isinstance(cond, Ternary))
        yield " else "
        yield from other.tokens(ctx)


class Container(ExprNode):
    """
    Base class for linear container types.
    """

    class Meta:
        abstract = True
        separator = ", "
        brackets = "", ""

    is_empty = property(lambda self: len(self._children) == 0)

    def __init__(self, children, **kwargs):
        Node.__init__(self, children, **kwargs)

    def tokens(self, ctx):
        left, right = self._meta.brackets
        sep = self._meta.separator
        yield left
        if self._children:
            yield from intersperse(sep, (x.tokens(ctx) for x in self._children))
        yield right


class Tuple(Container):
    """
    Tuple literal.
    """

    class Meta:
        brackets = "()"

    def tokens(self, ctx):
        if len(self.children) == 1:
            yield "("
            yield from self.children[0].tokens(ctx)
            yield ",)"
        else:
            yield from super().tokens(ctx)


class List(Container):
    """
    List literal.
    """

    class Meta:
        brackets = "[]"


class Set(Container):
    """
    Set literal.
    """

    class Meta:
        brackets = "{}"

    def tokens(self, ctx):
        if self.is_empty:
            yield "set()"
        else:
            yield from super().tokens(ctx)


class Dict(Container):
    """
    Dictionary literal.
    """

    class Meta:
        brackets = "{}"

    @classmethod
    def from_items(cls, pairs, **kwargs):
        """
        Create dictionary from list of pairs.
        """
        items = []
        for k, v in pairs:
            items.append(k)
            items.append(v)
        return cls(items, **kwargs)

    def tokens(self, ctx):
        children = iter(self._children)
        yield "{"
        for idx, k in enumerate(children):
            if idx:
                yield ", "
            yield from k.tokens(ctx)
            yield ": "
            yield from next(children).tokens(ctx)
        yield "}"
