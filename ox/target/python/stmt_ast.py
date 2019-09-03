from ox.ast import Tree
from ox.ast.utils import intersperse
from sidekick import curry
from .expr_ast import Expr, Name, Void, ArgDef, Starred, Tuple
from .utils import Loop as LoopAction
from ... import ast
from ...ast import Stmt as StmtBase

__all__ = [
    "Stmt",
    "StmtLeaf",
    "StmtNode",
    "stmt",
    "register_stmt",
    "Return",
    "Function",
    "Block",
    "Del",
]


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


class Cmd(StmtLeaf):
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


class Block(ast.BlockMixin, Stmt):
    """
    Python block of statements.
    """

    class Meta:
        separators = (":", "")


class Function(StmtNode):
    """
    A function definition.
    """

    name: Name
    args: Tree
    body: Block
    annotation: Expr

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        def to_arg(expr):
            if isinstance(expr, ArgDef):
                return expr
            elif isinstance(expr, (Name, Starred)):
                return ArgDef(expr)
            else:
                cls_name = type(expr).__name__
                raise TypeError(f"invalid argument type: {cls_name}")

        def function(name, args, body):
            fn = Function(Name(name), Tree("args", map(to_arg, args)), Block(body))
            return fn

        return {"def": function}

    def __init__(self, name: Name, args: Tree, body: Block, annotation=None, **kwargs):
        annotation = Void() if annotation is None else annotation
        super().__init__(name, args, body, annotation, **kwargs)

    def tokens(self, ctx):
        yield "def "
        yield from self.name.tokens(ctx)
        yield "("
        yield from intersperse(", ", map(lambda x: x.tokens(ctx), self.args.children))
        yield ")"
        if self.annotation:
            yield " -> "
            yield from self.annotation.tokens(ctx)
        yield from self.body.tokens_as_block(ctx)


class Del(StmtNode):
    """
    Del statement (e.g., del <value>).
    """

    expr: Expr

    class Meta:
        command = "del {expr}"
        sexpr_symbol = "del"

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        def del_statement(expr, *args, **kwargs):
            if args:
                expr = Tuple([expr, *args])
            return cls(expr, **kwargs)

        return {"del": del_statement}

    def tokens(self, ctx):
        if isinstance(self.expr, Tuple) and self.expr.children:
            yield ctx.start_line()
            yield "del "
            yield from self.expr.tokens(ctx, mode="expr-list")
        else:
            yield from super().tokens(ctx)
