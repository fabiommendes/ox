from types import MappingProxyType

from sidekick.tree import NodeOrLeaf
from .utils import NotImplementedDescriptor

BINARY_OPERATORS = MappingProxyType(
    {
        "+": "__add__",
        "//": "__floordiv__",
        "<<": "__lshift__",
        "@": "__matmul__",
        "%": "__mod__",
        "*": "__mul__",
        "**": "__pow__",
        ">>": "__rshift__",
        "-": "__sub__",
        "/": "__truediv__",
        "&": "__and___",
        "^ ": "__xor__",
        "|": "__or___",
        "==": "__eq__",
        ">=": "__ge__",
        ">": "__gt__",
        "<=": "__le__",
        "<": "__lt__",
        "!=": "__ne__",
    }
)

RBINARY_OPERATORS = MappingProxyType(
    {
        "+": "__radd__",
        "//": "__rfloordiv__",
        "<<": "__rlshift__",
        "@": "__rmatmul__",
        "%": "__rmod__",
        "*": "__rmul__",
        "**": "__rpow__",
        ">>": "__rrshift__",
        "-": "__rsub__",
        "/": "__rtruediv__",
        "&": "__rand___",
        "^ ": "__rxor__",
        "|": "__ror___",
    }
)

UNARY_OPERATORS = MappingProxyType({"~": "__invert__", "-": "__neg__", "+": "__pos__"})


class WrapperMeta(type):
    """
    Metaclass for Wrapper types.

    It inspect the _meta object of the base expression classes to create the
    dunder methods of the class.
    """

    def __init__(
        cls,
        name,
        bases,
        ns,
        roots=(),
        binary_operators=BINARY_OPERATORS,
        rbinary_operators=RBINARY_OPERATORS,
        unary_operators=UNARY_OPERATORS,
    ):
        super().__init__(name, bases, ns)

        cls.__sexpr_heads = sexpr_heads = {}
        cls.__roots = roots = tuple(roots)
        for root in roots:
            sexpr_heads.update(root._meta.sexpr_symbol_map)

        # Create unary and binary operators
        cls.make_operators(cls.make_binary_operator, binary_operators)
        cls.make_operators(cls.make_rbinary_operator, rbinary_operators)
        cls.make_operators(cls.make_unary_operator, unary_operators)

        # Special methods
        cls.__getattr__ = cls.make_getattr() or cls.__getattr__
        cls.__getitem__ = cls.make_getitem() or cls.__getitem__
        cls.__call__ = cls.make_fcall() or cls.__call__

    def make_operators(cls, factory, mapping):
        """
        Create operators from factory function and mapping.

        Args:
            factory:
                Function that receive (constructor, operator), where constructor
                is a (e1, e2) -> e3 and is used to construct the wrapped dunder method.
            mapping:
                A mapping from operator to constructor function.
        """
        for op, method_name in mapping.items():
            try:
                constructor = cls.__sexpr_heads[op]
                method = factory(constructor, op)
                setattr(cls, method_name, method)
            except KeyError:
                pass

    def make_binary_operator(cls, fn, op):
        """
        Create a method that wraps a binary operator 'op' from a function 'fn'
        that receives two expression instances.
        """
        from .ast_base import AST

        def bin_op(wrapped, other):
            lhs: AST = unwrap(wrapped)
            rhs = lhs._meta.coerce(unwrap(other))
            if isinstance(rhs, lhs._meta.root):
                return cls(fn(lhs, rhs))
            return NotImplemented

        return bin_op

    def make_rbinary_operator(cls, fn, op):
        """
        Create a method that wraps a reverse binary operator 'op' from a
        function 'fn'  that receives two expression instances.

        It uses the same function as make_binary_operator. The wrapper flips the
        order of arguments.
        """
        from .ast_base import AST

        def bin_op(wrapped, other):
            rhs: AST = unwrap(wrapped)
            lhs = rhs._meta.coerce(unwrap(other))
            return cls(fn(lhs, rhs))

        return bin_op

    def make_unary_operator(cls, fn, op):
        """
        Create a method that wraps an unary operator 'op' from a function 'fn'
        that receives a single expression instance.
        """
        from .ast_base import AST

        def unary_op(wrapped):
            arg: AST = unwrap(wrapped)
            return cls(fn(op, arg))

        return unary_op

    def make_fcall(cls):
        """
        Creates the __call__ method for wrapped instances.
        """
        fn = cls.__get_role("fcall")
        if fn is None:
            return None

        def __call__(*args, **kwargs):
            args = map(unwrap, args)
            kwargs = {k: unwrap(v) for k, v in kwargs.items()}
            return cls(fn(*args, **kwargs))

        return __call__

    def make_getitem(cls):
        """
        Creates the __getitem__ method for wrapped instances.
        """
        fn = cls.__get_role("getitem")
        if fn is None:
            return None

        def __getitem__(self, idx):
            return cls(fn(unwrap(self), unwrap(idx)))

        return __getitem__

    def make_getattr(cls):
        """
        Creates the __getattr__ method for wrapped instances.
        """
        fn = cls.__get_role("getattr")
        if fn is None:
            return None

        def __getattr__(self, attr):
            return cls(fn(unwrap(self), unwrap(attr)))

        return __getattr__

    def __get_role(cls, role):
        for root in cls.__roots:
            try:
                return root._meta.wrapper_roles[role]
            except KeyError:
                pass
        return None


class Wrapper(metaclass=WrapperMeta):
    """
    Base Wrapper object class.
    """

    __slots__ = ("__ref",)

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
    __eq__ = NotImplementedDescriptor()

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
    __hash__ = lambda self: hash(self.__ref)


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


def unwrap_nested(obj: Wrapper):
    """
    Remove ast from wrapper.

    Non-wrapped objects are returned as-is, making this function idempotent.
    """
    fn = unwrap_nested
    if isinstance(obj, Wrapper):
        wrapped = obj._Wrapper__ref
        if isinstance(wrapped, NodeOrLeaf) and wrapped.parent is None:
            return wrapped.copy()
        return wrapped
    elif isinstance(obj, list):
        return list(map(unwrap_nested, obj))
    elif isinstance(obj, tuple):
        return tuple(map(unwrap_nested, obj))
    elif isinstance(obj, set):
        return set(map(unwrap_nested, obj))
    elif isinstance(obj, dict):
        return {fn(k): fn(v) for k, v in obj.items()}
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
