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
        if "Meta" in ns:
            ns = dict(ns)
            del ns["Meta"]
        set_class_slots(bases, ns)
        return super().__new__(mcs, name, bases, ns)

    def __init__(cls, name, bases, ns):
        super().__init__(name, bases, ns)

        # Create _meta object
        cls: Type[HasMetaMixin]
        meta_ns = ns.get("Meta", SimpleNamespace)()
        meta_class = cls._meta_class()
        meta_args = cls._meta_args(meta_ns)
        cls._meta = meta_class(cls, **meta_args)
        cls._meta.init()
        cls._init = cls._make_init_method()
        if issubclass(cls, Node):
            cls._children_class = make_children_class(cls._meta)
        cls.tag = tag_descriptor(cls)
        cls._meta_finalize()
        log.info(
            f"Class created: {cls._meta.fullname}, root: "
            f"{cls._meta.root_meta.fullname}"
        )

    def _make_init_method(cls):
        """
        Create _init(*args, **kwargs) method for class.
        """

        if cls._meta.abstract:
            return make_abstract_init_method(cls)
        elif issubclass(cls, Leaf):
            return make_leaf_init_method(cls)
        else:
            return make_node_init_method(cls)


#
# Auxiliary functions
#
def set_class_slots(bases, ns):
    slots = ns.pop("__slots__", ...)

    # We can set slots to None to set the correct value
    if slots is False:
        return

    # Users can set __slots__ manually. Probably we should check if the choice
    # minimally consistent in the future.
    if slots is not ...:
        ns["__slots__"] = slots
        return

    # Compute required slots from annotations
    annotations = ns.get("__annotations__", None)
    if annotations is None:
        for base in bases:
            annotations = base.__dict__.get("__annotations__", None)
            if annotations is not None:
                break
        else:
            annotations = {}

    slots = tuple(k for k, v in annotations.items() if is_ast_type(v))
    if "tag" in annotations:
        slots = ("_tag", *slots)
    ns["__slots__"] = slots


def make_abstract_init_method(cls):
    """
    Init method for abstract classes. It immediately raises a TypeError on
    invokation.
    """

    msg = f"cannot create instance of abstract class {cls.__name__}"

    def abstract_init(*args, **kwargs):
        raise TypeError(msg)

    return abstract_init


def make_leaf_init_method(cls):
    """
    Generic method for Leaf types.
    """
    return Leaf.__init__


def make_node_init_method(cls):
    """
    Generic method for Node types.
    """
    meta = cls._meta
    fn = _sexpr_init_method if meta.has_tag_field else _node_init_method
    return fn(meta.children_fields, meta.attr_fields, {})


def _sexpr_init_method(children, attrs, defaults):
    node_init = _node_init_method(children, attrs, defaults)

    def sexpr_init(self, tag, *args, **kwargs):
        self._tag = tag
        node_init(self, *args, **kwargs)

    return sexpr_init


def _node_init_method(children, attrs, defaults):
    n_children = len(children)
    n_attrs = len(attrs)
    n_args_max = n_children + n_attrs
    n_args_min = n_args_max - len(defaults)

    # TODO: init method should be created by dynamic code evaluation like
    # namedtuples. This is somewhat fragile, but it can significantly boost
    # performance of the constructor
    def node_init(self, *args, parent=None, **kwargs):
        if len(args) > n_args_max:
            raise TypeError(f"expected at most {n_args_max} positional arguments.")
        elif len(args) < n_args_min:
            raise TypeError(f"expected at least {n_args_min} positional arguments.")

        self._children = self._children_class(self)
        self._parent = parent

        # Init children nodes
        args_iter = iter(args)
        for attr, child in zip(children, args_iter):
            if child.parent is None:
                child._parent = self
                setattr(self, attr, child)
            else:
                raise ValueError(f"node already has parent: {child.parent!r}")

        # Init attributes
        attrs_iter = iter(attrs)
        for attr, value in zip(attrs_iter, args_iter):
            kwargs[attr] = value
        self._attrs = kwargs

    return node_init


def tag_descriptor(cls):
    """
    A descriptor object for the tag field. It is set to None if object
    is a Node and define a tag attribute.
    """
    fields = cls._meta.fields
    if issubclass(cls, Leaf):
        return property(type)
    elif fields and fields[0] == "tag":
        return property(lambda x: x._tag)
    else:
        return property(type)
