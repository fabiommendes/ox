import inspect
from enum import Enum
from functools import singledispatch
from types import SimpleNamespace
from typing import Optional, Type, Dict, Callable, Union

from sidekick.tree import Leaf, Node, NodeOrLeaf
from .children import make_children_class
from .wrapper import Wrapper, unwrap
from ..logging import log

ID = lambda x: x
SExprKey = Union[str, 'HasMetaMixin', Enum]


class ASTMeta(type):
    """
    Metaclass for all AST types.
    """

    def __new__(mcs, name, bases, ns):
        if 'Meta' in ns:
            ns = dict(ns)
            del ns['Meta']
        if ns.get('__slots__', ...) is not None:
            ns.setdefault('__slots__', get_slots(ns))
        return super().__new__(mcs, name, bases, ns)

    def __init__(cls, name, bases, ns):
        super().__init__(name, bases, ns)

        # Create _meta object
        cls: Type[HasMetaMixin]
        meta_ns = ns.get('Meta', SimpleNamespace)()
        meta_class = cls._meta_class()
        meta_args = cls._meta_args(meta_ns)
        cls._meta = meta_class(cls, **meta_args)
        cls._meta.init()
        cls._init = cls._make_init_method()
        cls.tag = cls._meta.tag_descriptor()
        if issubclass(cls, Node):
            cls._children_class = make_children_class(cls._meta)
        cls._meta_finalize()
        log.info(f'Class created: {cls._meta.fullname}, root: '
                 f'{cls._meta.root_meta.fullname}')

    def _make_init_method(cls):
        """
        Create method for class.
        """

        if cls._meta.abstract:
            msg = f'cannot create instance of abstract class {cls.__name__}'

            def _abstract_init(*args, **kwargs):
                raise TypeError(msg)

            return _abstract_init

        # TODO: init method should be created by dynamic code evaluation like
        # namedtuples. This is somewhat fragile, but it can significantly boost
        # performance of the constructor
        if issubclass(cls, Leaf):
            return cls._generic_leaf_init_method()
        else:
            return cls._generic_node_init_method()

    def _generic_leaf_init_method(cls):
        return Leaf.__init__

    def _generic_node_init_method(cls):
        meta = cls._meta
        posargs = tuple(meta.annotations)
        children = tuple(k for k, v in meta.annotations.items() if is_ast_type(v))
        children_set = set(children)
        tag_attr = meta.tag_attribute

        def _init(self, *args, parent=None, **kwargs):
            self._children = self._children_class(self)
            self._parent = parent

            if len(args) > len(posargs):
                n = len(posargs)
                raise TypeError(f'expected at most {n} positional arguments.')

            n_children = 0
            for k, v in zip(posargs, args):
                if k in kwargs:
                    raise TypeError(f'repeated keyword argument: {k!r}')
                if k in children_set:
                    if v.parent is None:
                        v._parent = self
                        setattr(self, k, v)
                        n_children += 1
                    else:
                        raise ValueError(f'node already has parent: {v.parent!r}')
                elif k == tag_attr:
                    setattr(self, k, v)
                else:
                    kwargs[k] = v

            for k in list(kwargs):
                if k in children_set:
                    setattr(self, k, kwargs.pop(k))
                    n_children += 1

            if n_children != len(children):
                for k in children_set:
                    try:
                        getattr(self, k)
                    except AttributeError:
                        raise TypeError(f'{k!r} not given')

            self._attrs = kwargs

        return _init


class HasMetaMixin:
    """
    Base mixin class that allow sub-classes to tweak some aspect of their
    creation.

    Those methods are executed during the construction of the _meta attribute
    of the class.
    """
    _meta: 'Meta'
    __slots__ = ()

    @classmethod
    def _meta_class(cls):
        """
        Allow to override the class used to construct the _meta attribute.
        """
        return Meta

    @classmethod
    def _meta_args(cls, meta_obj):
        """
        Executed before creating the _meta attribute for the class.

        Receives an instance of the Meta object declared in the class body and
        returns a dictionary with attributes passed as keyword arguments to the
        Meta constructor.
        """
        kwargs = {}
        for arg in META_ARGUMENTS:
            try:
                kwargs[arg] = getattr(meta_obj, arg)
            except AttributeError:
                pass

        extra = {}
        for attr in dir(meta_obj):
            if not attr.startswith('_') and attr not in kwargs:
                extra[attr] = getattr(meta_obj, attr)
        if extra:
            kwargs['extra'] = extra
        return kwargs

    @classmethod
    def _meta_finalize(cls):
        """
        Executed after the class is created and populated with the _meta
        attribute.

        The default implementation is a no-op, but can be overriden by
        subclasses.
        """

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        """
        Return a dictionary of constructors mapping S-Expr heads to their
        corresponding constructor function.
        """
        return {}


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


# Utility functions
#
META_ARGUMENTS = tuple(inspect.getfullargspec(Meta.__init__).kwonlyargs)


def is_ast_type(cls):
    """
    Return True if type is as subclass of Node or Leaf.
    """
    return isinstance(cls, type) and issubclass(cls, NodeOrLeaf)


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


def get_slots(ns):
    annotations = ns.get('__annotations__', {})
    return tuple(k for k, v in annotations.items() if is_ast_type(v))
