from functools import lru_cache
from typing import Type


class NotImplementedDescriptor:
    """
    Simple descriptor that raises error when instance tries to access method
    or operator
    """

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        name = getattr(self, "name", "<unknown method>")
        cls = cls.__name__
        raise NotImplementedError(f"{cls} does not implement {name}")

    def __set_name__(self, owner, name):
        self.name = name


def wrap_tokens(it, wrap=True):
    """
    Wrap iterable with two parenthesis tokens.

    Args:
        it:
            Iterator of token elements
        wrap (bool):
            If False, simply yield the contents of it without wrapping it with
            delimiters.
    """
    if wrap is True:
        yield "("
        yield from it
        yield ")"
    elif wrap:
        left, right = wrap
        yield left
        yield from it
        yield right
    else:
        yield from it


def from_template(command, ctx):
    """
    Render template in given context. Return an interator over all tokens

    Args:
        command:
            String template.
        ctx:
            A mapping from names to token iterables. Each iterator yield a sequence
            of tokens used to construct the given string argument.
    """
    renderer = get_renderer(command)
    return renderer(ctx)


@lru_cache(256)
def get_renderer(template):
    """
    Return the renderer function for the given string.
    """

    def renderer_fallback(ctx):
        data = {k: "".join(v) for k, v in ctx.items()}
        return template.format(**data)

    return renderer_fallback


def attr_property(name, default=None, readonly=False):
    """
    Expose an attribute as a property.
    """

    @property
    def prop(self):
        return self.attrs.get(name, default)

    if readonly:
        return prop

    @prop.setter
    def prop(self, value):
        self.attr[name] = value

    return prop


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
        return unary_operator_sexpr(cls, cls._meta.annotations["op"].from_name(op))
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
        return binary_operator_sexpr(cls, cls._meta.annotations["op"].from_name(op))
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
