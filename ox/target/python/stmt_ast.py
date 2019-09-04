from functools import partial

from ox.ast import Tree
from ox.ast.utils import intersperse
from ox.target.python.operators import Inplace as InplaceOpEnum
from sidekick import curry, alias
from .expr_ast import (
    Expr,
    Name,
    Void,
    ArgDef,
    Starred,
    Tuple,
    to_expr,
    Atom,
    As,
    to_expr_or_name,
)
from .utils import Cmd as CmdEnum
from ... import ast
from ...ast import Stmt as StmtBase

__all__ = [
    "Stmt",
    "StmtLeaf",
    "StmtNode",
    "to_stmt",
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


to_stmt = Stmt._meta.coerce
register_stmt = curry(2, to_stmt.register)
register_stmt(Expr, lambda x: ExprStmt(x))
register_stmt(tuple, lambda x: Block(x))
register_stmt(list, lambda x: Block(x))


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

    value: CmdEnum

    @classmethod
    def Break(cls, **kwargs):
        """
        Create Cmd instance representing a "break" statement.
        """
        return cls(CmdEnum.BREAK, **kwargs)

    @classmethod
    def Continue(cls, **kwargs):
        """
        Create Cmd instance representing a "continue" statement.
        """
        return cls(CmdEnum.CONTINUE, **kwargs)

    @classmethod
    def Pass(cls, **kwargs):
        """
        Create Cmd instance representing a "pass" statement.
        """
        return cls(CmdEnum.PASS, **kwargs)

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        return {
            "break": cls.Break,
            "continue": cls.Continue,
            CmdEnum.BREAK: cls.Break,
            CmdEnum.CONTINUE: cls.Continue,
        }

    def tokens(self, ctx):
        yield self.value.value


class Block(ast.BlockMixin, Stmt):
    """
    Python block of statements.
    """

    class Meta:
        separators = (":", "")

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        return {"do": lambda *args: cls(map(to_stmt, args))}

    def __init__(self, children=(), **kwargs):
        super().__init__(map(to_stmt, children), **kwargs)


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
        if self.args.children:
            yield from intersperse(
                ", ", map(lambda x: x.tokens(ctx), self.args.children)
            )
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


class Assign(StmtNode):
    """
    Assignment statement. (e.g., <lhs> = <rhs>)
    """

    lhs: Expr
    rhs: Expr

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        e = to_expr
        return {"=": lambda x, y: cls(e(x), e(y))}

    def tokens(self, ctx):
        yield ctx.start_line()
        yield from self.lhs.tokens(ctx)
        yield " = "
        yield from self.rhs.tokens(ctx)


class Inplace(StmtNode):
    """
    Complex assignment statement with inplace operator (e.g., x += 1)
    """

    tag: InplaceOpEnum
    lhs: Expr
    rhs: Expr
    op = alias("tag")

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        e = to_expr
        fn = lambda op, x, y: cls(op, e(x), e(y))
        sexprs = {op: partial(fn, op) for op in InplaceOpEnum}
        sexprs.update({op.value: partial(fn, op) for op in InplaceOpEnum})
        return sexprs

    def tokens(self, ctx):
        yield ctx.start_line()
        yield from self.lhs.tokens(ctx)
        yield f" {self.tag.value} "
        yield from self.rhs.tokens(ctx)


class ExprStmt(StmtNode):
    """
    Statement formed by a single expression.
    """

    expr: Expr

    def tokens(self, ctx):
        yield ctx.start_line()
        yield from self.expr.tokens(ctx)


class If(ast.BodyElseMixin, Stmt):
    """
    A if block.
    """

    cond: Expr
    body: Block
    other: Stmt

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        e = to_expr
        s = to_stmt
        return {"if": lambda cond, *args: cls(e(cond), *map(s, args))}

    def __init__(self, cond, block, other=None, **kwargs):
        other = Block([]) if other is None else other
        super().__init__(cond, block, other, **kwargs)

    def tokens(self, ctx, _command="if "):
        yield ctx.start_line() + _command
        yield from self.cond.tokens(ctx)
        if isinstance(self.other, If):
            yield from self.body.tokens_as_block(ctx)
            yield from self.other.tokens(ctx, "elif ")
        else:
            yield from super().tokens(ctx)


class While(ast.BodyElseMixin, Stmt):
    """
    While block.
    """

    cond: Expr
    body: Block
    other: Block

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        e = to_expr
        s = to_stmt
        return {"while": lambda cond, *args: cls(e(cond), *map(s, args))}

    def __init__(self, expr, block=None, other=None, **kwargs):
        block = Block([]) if block is None else block
        other = Block([]) if other is None else other
        super().__init__(expr, block, other, **kwargs)

    def tokens(self, ctx):
        yield ctx.start_line() + "while "
        yield from self.cond.tokens(ctx)
        yield from super().tokens(ctx)


class ImportFrom(StmtNode):
    """
    Import statement (from <mod> import <expr>)
    """

    mod: Expr
    expr: Expr
    level: int

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        def to_import(x):
            if isinstance(x, dict) and len(x) == 1:
                k, v = next(iter(x.items()))
                return As(to_expr_or_name(k), to_expr_or_name(v))
            elif isinstance(x, dict):
                return Tuple([to_import({k: v}) for k, v in x.items()])
            else:
                return to_expr(x)

        def import_from(mod, *args):
            args = [to_import(x) for x in args]
            args = args[0] if len(args) == 1 else args
            return cls(to_expr(mod), args)

        return {"import from": import_from}

    def __init__(self, mod, expr=None, level=0, **kwargs):
        expr = Atom(...) if expr is None else expr
        super().__init__(mod, expr, level, **kwargs)

    def tokens(self, ctx):
        yield ctx.start_line()
        yield "from "
        yield from self.mod.tokens(ctx)
        yield " import "
        yield from self.expr.tokens(ctx)
