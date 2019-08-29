from sidekick import SExpr, Node as NodeBase, Leaf as LeafBase
from sidekick.tree.node_base import NodeOrLeaf
from .children import ChildrenBase
from .meta_attr import Meta
from ox.ast.ast_meta import ASTMeta
from ox.ast.ast_meta_mixin import HasMetaMixin
from .print_context import PrintContext
from .token import Token


class Tree(SExpr):
    """
    Generic AST type not directly associated with a standalone syntactic
    construct. Leaf nodes are tokens.

    Tree nodes can be used as generic SExpr types or as parts of specialized
    ASTs that do not need to specify any custom behavior.
    """
    __slots__ = ()
    _meta: Meta
    _leaf_class = Token


class AST(HasMetaMixin, NodeOrLeaf, metaclass=ASTMeta):
    """
    Base class for Node and Leaf syntax tree classes.
    """

    __slots__ = ()
    __annotations__ = {}

    # Attributes
    precedence_level = 0
    assumptions = None
    execution_context = None
    is_stmt = False
    is_expr = False

    class Meta:
        abstract = True
        root = True
        print_context_class = PrintContext

    def __init__(self, *args, **kwargs):
        self._init(*args, **kwargs)

    def _init(self, *args, **kwargs):
        msg = 'the init method should been created dynamically by metaclass constructor'
        raise RuntimeError(msg)

    #
    # API methods
    #
    def source(self, context=None):
        """
        Return source code representation for node.
        """
        if context is None:
            context = self.print_context()
        return "".join(self.tokens(context))

    def tokens(self, context):
        """
        Return an iterator over tokens for the output source code.

        Tokens can be joined together to construct the source code
        representation of element.

        Subclasses should override tokens_for_context instead of this method.
        """
        raise NotImplementedError("tokens() method must be implemented in subclass")

    def print_context(self, **kwargs):
        """
        Starts a new print context.
        """
        return self._meta.print_context_class(**kwargs)


class Node(AST, NodeBase):
    """
    Base class for structured AST types.

    Subclasses of this class have always a fixed number of children that are
    also exposed as attributes.
    """
    __slots__ = ()
    __annotations__ = {}
    _leaf_class = Token
    _children_class = ChildrenBase
    children = property(lambda self: self._children)

    class Meta:
        abstract = True

    def copy(self):
        meta = self._meta
        new = object.__new__(type(self))
        new._parent = None
        new._attrs = self._attrs.copy()
        if meta.tag_attribute:
            setattr(new, meta.tag_attribute, getattr(self, meta.tag_attribute))
        for attr in meta.children_attributes:
            setattr(new, attr, getattr(self, attr))
        return new


class Leaf(AST, LeafBase):
    """
    Base class for all Leaf nodes.
    """

    __slots__ = ()
    __annotations__ = {}

    class Meta:
        abstract = True
