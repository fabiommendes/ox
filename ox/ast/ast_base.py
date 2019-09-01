from sidekick import Maybe
from sidekick import SExpr, Node as NodeBase, Leaf as LeafBase
from sidekick.tree.node_base import NodeOrLeaf
from .ast_meta import ASTMeta
from .ast_meta_mixin import HasMetaMixin
from .children import ChildrenBase
from .meta_attr import Meta
from .print_context import PrintContext
from .token import Token
from .utils import wrap_tokens, from_template


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

    # Queries
    is_stmt = False
    is_expr = False
    has_static_value = False

    class Meta:
        abstract = True
        root = True
        print_context_class = PrintContext

    def __init__(self, *args, **kwargs):
        self._init(*args, **kwargs)

    def _init(self, *args, **kwargs):
        msg = "the init method should been created dynamically by metaclass constructor"
        raise RuntimeError(msg)

    #
    # API methods
    #
    def static_value(self) -> Maybe:
        """
        Return the statically defined expression value.

        It returns a Maybe type:
            Nothing -> value cannot be known statically
            Just(value) -> value is known
        """
        return Maybe.Nothing

    def source(self, context=None):
        """
        Return source code representation for node.
        """
        if context is None:
            context = self.print_context()
        return "".join(self.tokens(context))

    def child_tokens(self, child, role, context):
        """
        Yield tokens for the given element as a child in the given role.
        """
        wrap = self.wrap_child_tokens(child, role)
        if wrap:
            yield from wrap_tokens(child.tokens(context), wrap)
        else:
            yield from child.tokens(context)

    def wrap_child_tokens(self, child, role):
        """
        Return a pair of parenthesis or other enclosing brackets.

        Must return True, False or a pair of enclosing tokens.
        """
        return False

    def tokens(self, context):
        """
        Return an iterator over tokens for the output source code.

        Tokens can be joined together to construct the source code
        representation of element.

        Subclasses should override tokens_for_context instead of this method.
        """
        if self._meta.command:
            ctx = {
                f: self.child_tokens(getattr(self, f), f, context)
                for f in self._meta.children_fields
            }
            return from_template(self._meta.command, ctx)
        raise NotImplementedError("tokens() method must be implemented in subclass")

    def print_context(self, **kwargs):
        """
        Starts a new print context.
        """
        return self._meta.print_context_class(**kwargs)

    def simplify(self):
        """
        Recursively simplify expression, when possible.
        """
        return self.copy()

    def from_static_children(self, *children):
        """
        Create new AST node from statically known values for children.
        """
        raise NotImplementedError


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

    def _simplify_or_copy(self, recur):
        """Common implementation for both methods"""

        meta = self._meta
        new = object.__new__(type(self))
        new._parent = None
        new._attrs = self._attrs.copy()
        new._children = new._children_class(new)
        if meta.has_tag_field:
            new._tag = self._tag
        for attr in meta.children_fields:
            setattr(new, attr, recur(getattr(self, attr)))
        return new

    def copy(self):
        return self._simplify_or_copy(lambda x: x.copy())

    def simplify(self):
        args = []
        for child in self.children:
            value = child.static_value()
            if value.is_just:
                args.append(value.value)
            else:
                break
        else:
            return self.from_static_children(*args)
        return self._simplify_or_copy(lambda x: x.simplify())


class Leaf(AST, LeafBase):
    """
    Base class for all Leaf nodes.
    """

    __slots__ = ()
    __annotations__ = {}

    class Meta:
        abstract = True
