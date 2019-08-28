from .base import Node


class Stmt(Node):
    """
    Base class for AST nodes that represent statements.
    """

    is_expr = False
    is_stmt = True

    class Meta:
        abstract = True
        root = True