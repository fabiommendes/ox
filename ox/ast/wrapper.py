from types import MappingProxyType

from sidekick.tree import NodeOrLeaf
from .utils import NotImplementedDescriptor

BINARY_OPERATORS = MappingProxyType({
    "+": '__add__',
    "//": '__floordiv__',
    "<<": '__lshift__',
    "@": '__matmul__',
    "%": '__mod__',
    "*": '__mul__',
    "**": '__pow__',
    ">>": '__rshift__',
    "-": '__sub__',
    "/": '__truediv__',
    "&": '__and___',
    "^ ": '__xor__',
    "|": '__or___',
    "==": '__eq__',
    ">=": '__ge__',
    ">": '__gt__',
    "<=": '__le__',
    "<": '__lt__',
    "!=": '__ne__',
})

RBINARY_OPERATORS = MappingProxyType({
    "+": '__radd__',
    "//": '__rfloordiv__',
    "<<": '__rlshift__',
    "@": '__rmatmul__',
    "%": '__rmod__',
    "*": '__rmul__',
    "**": '__rpow__',
    ">>": '__rrshift__',
    "-": '__rsub__',
    "/": '__rtruediv__',
    "&": '__rand___',
    "^ ": '__rxor__',
    "|": '__ror___',
})

UNARY_OPERATORS = MappingProxyType({
    "~": '__invert__',
    "-": '__neg__',
    "+": '__pos__',
})


class WrapperMeta(type):
    """
    Metaclass for Wrapper types.

    It inspect the _meta object of the base expression classes to create the
    dunder methods of the class.
    """

    def __init__(cls, name, bases, ns, roots=(),
                 binary_operators=BINARY_OPERATORS,
                 rbinary_operators=RBINARY_OPERATORS,
                 unary_operators=UNARY_OPERATORS):
        super().__init__(name, bases, ns)

        cls._sexpr_heads = sexpr_heads = {}
        for root in roots:
            sexpr_heads.update(root._meta.sexpr_symbol_map)
        cls.make_operators(cls.make_binary_operator, binary_operators)
        cls.make_operators(cls.make_rbinary_operator, rbinary_operators)
        cls.make_operators(cls.make_unary_operator, unary_operators)

    def make_operators(cls, factory, mapping):
        for op, method_name in mapping.items():
            try:
                constructor = cls._sexpr_heads[op]
                method = factory(constructor, op)
                setattr(cls, method_name, method)
            except KeyError:
                pass

    def make_binary_operator(cls, fn, op):
        from .base import AST

        def bin_op(wrapped, other):
            lhs: AST = unwrap(wrapped)
            rhs = lhs._meta.coerce(unwrap(other))
            if isinstance(rhs, lhs._meta.root):
                return cls(fn(lhs, rhs))
            return NotImplemented

        return bin_op

    def make_rbinary_operator(cls, fn, op):
        from .base import AST

        def bin_op(wrapped, other):
            lhs: AST = unwrap(wrapped)
            rhs = unwrap(other)
            if isinstance(rhs, lhs._meta.root):
                return cls(fn(op, rhs, lhs))
            return NotImplemented

        return bin_op

    def make_unary_operator(cls, fn, op):
        from .base import AST

        def unary_op(wrapped):
            arg: AST = unwrap(wrapped)
            return cls(fn(op, arg))

        return unary_op

    def make_function_call(cls):
        raise NotImplementedError

    def make_getitem(cls):
        raise NotImplementedError

    def make_getattr(cls):
        raise NotImplementedError


class Wrapper(metaclass=WrapperMeta):
    """
    Base Wrapper object class.
    """
    __slots__ = ('__ref',)

    def __init__(self, obj):
        self.__ref = obj

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def __repr__(self):
        return f"wrap({self.__ref})"

    # Arithmetic operators
    __add__ = NotImplementedDescriptor()
    __sub__ = NotImplementedDescriptor()
    __mul__ = NotImplementedDescriptor()
    __matmul__ = NotImplementedDescriptor()
    __mod__ = NotImplementedDescriptor()
    __truediv__ = NotImplementedDescriptor()
    __floordiv__ = NotImplementedDescriptor()
    __pow__ = NotImplementedDescriptor()
    __radd__ = NotImplementedDescriptor()
    __rsub__ = NotImplementedDescriptor()
    __rmul__ = NotImplementedDescriptor()
    __rmatmul__ = NotImplementedDescriptor()
    __rmod__ = NotImplementedDescriptor()
    __rtruediv__ = NotImplementedDescriptor()
    __rfloordiv__ = NotImplementedDescriptor()
    __rpow__ = NotImplementedDescriptor()

    # Comparison operators
    __gt__ = NotImplementedDescriptor()
    __lt__ = NotImplementedDescriptor()
    __ge__ = NotImplementedDescriptor()
    __le__ = NotImplementedDescriptor()

    # Bitwise operators
    __or__ = NotImplementedDescriptor()
    __xor__ = NotImplementedDescriptor()
    __and__ = NotImplementedDescriptor()
    __rshift__ = NotImplementedDescriptor()
    __lshift__ = NotImplementedDescriptor()
    __ror__ = NotImplementedDescriptor()
    __rxor__ = NotImplementedDescriptor()
    __rand__ = NotImplementedDescriptor()
    __rrshift__ = NotImplementedDescriptor()
    __rlshift__ = NotImplementedDescriptor()

    # Unary operators
    __pos__ = NotImplementedDescriptor()
    __neg__ = NotImplementedDescriptor()
    __invert__ = NotImplementedDescriptor()

    # Other special methods
    __getitem__ = NotImplementedDescriptor()
    __getattr__ = NotImplementedDescriptor()
    __call__ = NotImplementedDescriptor()


#
# Wrapping and unwrapping functions
#

# noinspection PyUnresolvedReferences,PyProtectedMember
def unwrap(obj: Wrapper):
    """
    Remove ast from wrapper.

    Non-wrapped objects are returned as-is, making this function idempotent.
    """
    if isinstance(obj, Wrapper):
        wrapped = obj._Wrapper__ref
        if isinstance(wrapped, NodeOrLeaf) and wrapped.parent is None:
            return wrapped.copy()
        return wrapped
    return obj


def wrap(obj, wrapper_class=Wrapper):
    """
    Wrap element into expression wrapper.

    Wrapped objects accept operators and create new expressions on the
    fly by creating the corresponding expression node.
    """

    if isinstance(obj, Wrapper):
        return obj
    return wrapper_class(obj)