import inspect
from enum import Enum
from functools import singledispatch
from typing import Optional, Type, Dict, Callable, Union

from sidekick.tree import Leaf, Node, NodeOrLeaf
from .ast_meta_mixin import HasMetaMixin, META_ARGUMENTS
from .wrapper import Wrapper, unwrap
from ..logging import log

ID = lambda x: x
SExprKey = Union[str, 'HasMetaMixin', Enum]


class Meta:
    """
    Meta base class store information about the node class.
    """

    parent: Optional['Meta'] = None
    root: HasMetaMixin
    type: Type[HasMetaMixin]
    sexpr_symbol_map: Dict[SExprKey, Callable[..., HasMetaMixin]]

    root_name = property(lambda self: self.root_meta.type.__name__)

    @property
    def fullname(self):
        cls = self.type
        return f'{cls.__module__}.{cls.__name__}'

    def __init__(self, cls, extra=None, *, abstract=False, root=None,
                 sexpr_symbol=None,
                 sexpr_symbol_map=None):

        cls._meta = self
        if extra:
            for k, v in extra.items():
                setattr(self, k, v)

        self.type = cls
        self.abstract = abstract

        # Set root meta node
        if root is True:
            self.is_root = True
            self.root = cls
            self.root_meta = self
        elif root is None or root is False:
            for sub in cls.mro()[1:]:
                if issubclass(sub, HasMetaMixin) and sub is not HasMetaMixin:
                    if sub._meta.is_root:
                        self.root = sub._meta.type
                        self.root_meta = self.root._meta
                        self.is_root = False
                        break
        elif isinstance(root, type) and issubclass(root, HasMetaMixin):
            self.is_root = False
            self.root = root
            self.root_meta = root._meta
        else:
            raise ValueError(f'invalid root node: {root}')

        # Collect information about class hierarchy
        self.is_leaf = issubclass(cls, Leaf)
        self.is_node = issubclass(cls, Node)
        self.subclasses = set()
        self.leaf_subclasses = set()
        self.node_subclasses = set()
        assert not (self.is_leaf and self.is_node), cls.__mro__

        if not abstract and not self.is_root:
            meta = self.root_meta
            meta.subclasses.add(cls)
            if self.is_leaf:
                meta.leaf_subclasses.add(cls)
            if self.is_node:
                meta.node_subclasses.add(cls)

        # Derived properties
        self.annotations = getattr(cls, "__annotations__", {})
        self.attributes = tuple(self.annotations)

        # Register s-expr factory mappings
        if self.root_meta is self or self.is_root:
            sexpr_map = {}
        else:
            sexpr_map = self.root_meta.sexpr_symbol_map
        self.sexpr_symbol_map = sexpr_map
        if sexpr_symbol_map:
            sexpr_map.update(sexpr_symbol_map(self.type))
        if sexpr_symbol:
            sexpr_map[sexpr_symbol] = sexpr(self, sexpr_symbol)
        sexpr_map[self.type] = sexpr(self)

        # S-expr mappings
        self.tag_attribute = None
        items = self.annotations.items()
        if self.is_node and items:
            first_arg, first_arg_type = next(iter(items))
            if not issubclass(first_arg_type, NodeOrLeaf):
                self.tag_attribute = first_arg
        self.children_attributes = tuple(self.children())

        # Wrapper expressions
        self.wrapper_roles = {} if self.is_root else self.root_meta.wrapper_roles
        for role in ['getattr', 'getitem', 'fcall']:
            if hasattr(cls, '_meta_' + role):
                self.wrapper_roles[role] = getattr(cls, '_meta_' + role)

    def __repr__(self):
        return f'Meta({self.type.__name__})'

    def __getattr__(self, item):
        if not item.startswith('_'):
            for cls in self.type.mro()[1:]:
                if (issubclass(cls, HasMetaMixin)
                        and cls is not HasMetaMixin
                        and item in cls._meta.__dict__):
                    value = getattr(cls._meta, item)
                    setattr(self, item, value)
                    return value
        raise AttributeError(item)

    def init(self):
        """
        Init custom attributes.
        """

        # Construct sexpr symbol map from classmethod.
        sexpr_map = self.type._meta_sexpr_symbol_map()
        for k, v in sexpr_map.items():
            if k not in self.sexpr_symbol_map:
                self.sexpr_symbol_map[k] = v
            else:
                log.debug(f'repeated S-Expr constructor: {k}')

        # Create coerce function for root nodes
        if self.is_root:
            self.coerce = self.coerce_function()
        else:
            self.coerce = self.root_meta.coerce

    def coerce_function(self):
        """
        Return a coerce function for the given node.

        Coerce functions should be registered only on root nodes.
        """
        name = self.root_name

        @singledispatch
        def coerce(x):
            cls = type(x).__name__
            raise TypeError(f'{cls} cannot be converted to {name}')

        register = (lambda cls, fn: coerce.register(cls)(fn))
        register(self.type, ID)
        register(Wrapper, lambda x: coerce(unwrap(x)))
        return coerce

    def children(self):
        """
        Iterate over all attributes that are treated as child nodes.
        """
        yield from (k for k, v in self.annotations.items() if is_ast_type(v))

    def tag_descriptor(self):
        """
        Return a descriptor object for the tag attribute.
        """

        if self.is_leaf:
            return None
        elif self.tag_attribute is None:
            return property(type)
        else:
            attr = self.tag_attribute
            return property(lambda x: getattr(x, attr))


#
# Constants and utility functions
#
META_ARGUMENTS.extend(inspect.getfullargspec(Meta.__init__).kwonlyargs)


def sexpr(meta: Meta, symbol: str = None):
    """
    Creates a S-expr factory function from meta object and

    Args:
        meta:
            Meta object for class.
        symbol:
            String with symbol value.
    """
    cls = meta.type

    def sexpr_constructor(*args, **kwargs):
        return cls(*args, **kwargs)

    return sexpr_constructor


def is_ast_type(cls):
    """
    Return True if type is as subclass of Node or Leaf.
    """
    return isinstance(cls, type) and issubclass(cls, NodeOrLeaf)