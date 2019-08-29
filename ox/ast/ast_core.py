from ox.ast import Node
from sidekick.tree import SExprBase
from .ast_base import AST, Leaf, Node


class Expr(AST):
    """
    Base class for AST nodes that represent expressions.

    Most programming languages distinguish between Expressions, syntactic
    constructs that represent values that can be freely composed, and Statements,
    which represent declarations, control flow and generally speaking cannot
    be included inside expressions.

    This class serves as a generic base class for expression nodes for any custom
    language.
    """

    is_expr = True

    class Meta:
        abstract = True

    #
    # Construction of sub-nodes
    #
    def attr(self, attr: str) -> "ExprNode":
        """
        Return an expression node representing ``obj.<attr>``.
        """
        raise NotImplementedError

    def index(self, value) -> "ExprNode":
        """
        Return an expression node representing ``obj[<value>]``.
        """
        raise NotImplementedError

    def call(*args, **kwargs):
        """
        Create expression that calls current value with the given
        positional and keyword arguments.
        """
        self, *args = args
        raise NotImplementedError

    def method(*args, **kwargs):
        """
        Return an expression node equivalent to a calling method with given
        arguments.
        """
        self, method, *args = args
        return self.attr(method).call(*args, **kwargs)

    #
    # Operators
    #
    def binary_op(self, op, other) -> "ExprNode":
        """
        Create a new expression node representing the action of the given
        binary operator acting on the current node.
        """
        raise NotImplementedError

    def unary_op(self, op) -> "ExprNode":
        """
        Creates new expression representing the result of the given unary
        operator acting on the current expression node.
        """
        raise NotImplementedError

    def comparison_op(self, op, other, *args) -> "ExprNode":
        """
        Create a new expression node representing ``self == other``.
        """
        raise NotImplementedError

    def free_vars(self, exclude=(), include=()):
        """
        Return all free variables from node.
        """
        vars = set(include)
        if self.is_leaf:
            return vars
        for child in self.children:
            xs = child.free_vars(exclude, include)
            xs.difference_update(exclude)
        return vars


class ExprLeaf(Leaf, Expr):
    """
    Base class for expression leaf types.
    """

    class Meta:
        abstract = True

    def _repr_as_child(self):
        return self._repr()


class ExprNode(Node, SExprBase, Expr):
    """
    Base class for expression node types.
    """

    class Meta:
        abstract = True

    __eq__ = SExprBase.__eq__

    def _repr(self, children=True):
        return Node._repr(self, children=children)

    def __repr__(self):
        args = []
        for attr in self._meta.annotations:
            args.append(repr(getattr(self, attr)))
        args = ", ".join(args)
        return f"{self.__class__.__name__}({args})"


class Stmt(Node):
    """
    Base class for AST nodes that represent statements.
    """

    is_expr = False
    is_stmt = True

    class Meta:
        abstract = True
        root = True
