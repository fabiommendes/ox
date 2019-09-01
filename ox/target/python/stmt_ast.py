from sidekick import curry
from .expr_ast import Expr
from .utils import Loop as LoopAction
from ... import ast
from ...ast import Stmt as StmtBase

__all__ = ["Stmt", "StmtLeaf", "StmtNode", "stmt", "register_stmt", "Return"]


class Stmt(StmtBase):
    """
    Base class for Python AST nodes that represent statements.
    """

    class Meta:
        root = True
        abstract = True


class StmtLeaf(ast.StmtLeaf, Stmt):
    """
    Base class for Python Expression leaf nodes.
    """

    class Meta:
        abstract = True


class StmtNode(ast.StmtNode, Stmt):
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

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        return {"return": cls}


class Loop(StmtLeaf):
    """
    A return statement (return <expr>)
    """

    value: LoopAction

    @classmethod
    def Break(cls, **kwargs):
        """
        Create Loop instance representing a "break" statement.
        """
        return cls(LoopAction.BREAK, **kwargs)

    @classmethod
    def Continue(cls, **kwargs):
        """
        Create Loop instance representing a "continue" statement.
        """
        return cls(LoopAction.CONTINUE, **kwargs)

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        return {
            "break": cls.Break,
            "continue": cls.Continue,
            LoopAction.BREAK: cls.Break,
            LoopAction.CONTINUE: cls.Continue,
        }

    def tokens(self, ctx):
        yield self.value.value
