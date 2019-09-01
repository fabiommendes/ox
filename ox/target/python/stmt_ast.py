from sidekick import curry
from .expr_ast import Expr
from ... import ast
from ...ast import Stmt as StmtBase

__all__ = ["Stmt", "StmtLeaf", "StmtNode", "stmt", "register_stmt", "Return"]


class Stmt(StmtBase):
    """
    Base class for Python AST nodes that represent statements.
    """


class StmtLeaf(Stmt, ast.StmtLeaf):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        abstract = True


class StmtNode(Stmt, ast.StmtNode):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        abstract = True


stmt = Stmt._meta.coerce
register_stmt = curry(2, stmt.register)


# ==============================================================================
# NODES
# ==============================================================================
class Return(ast.StmtExprMixin, StmtNode):
    """
    A return statement (return <expr>)
    """

    expr: Expr

    class Meta:
        command = "return {expr}"
        sexpr_symbol = "return"
