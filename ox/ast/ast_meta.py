from types import SimpleNamespace
from typing import Type

from sidekick import Node, Leaf
from .ast_meta_mixin import HasMetaMixin
from .children import make_children_class
from .meta_attr import is_ast_type
from ..logging import log


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


def get_slots(ns):
    annotations = ns.get('__annotations__', {})
    return tuple(k for k, v in annotations.items() if is_ast_type(v))
