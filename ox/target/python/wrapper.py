import itertools

from .expr_ast import Name, Expr, PyAtom, Atom
from .operators import Inplace as InplaceOpEnum
from .stmt_ast import Stmt, Cmd, Block, Assign, Inplace
from .utils import is_python_name
from ...ast.wrapper import Wrapper, unwrap, unwrap_nested, wrap as _wrap

wrap = lambda x: _wrap(x, Py)


class Py(Wrapper, roots=(Expr, Stmt)):
    """
    Wrapper object
    """

    def __repr__(self):
        ref = unwrap(self)
        if isinstance(ref, Atom):
            return f"py({ref.value!r})"
        src = ref.source().strip("\n")
        if "\n" in src:
            it = map(repr, src.split("\n"))
            it = itertools.chain([next(it), *("   " + x for x in it)])
            src = ",\n".join(it)
            return f"py[{src}]"
        return f"py[{src!r}]"


class PyMagic:
    """
    Base class for the magic py object.
    """

    def __call__(self, *args, **kwargs):
        args = tuple(map(unwrap_nested, args))
        kwargs = {k: unwrap_nested(v) for k, v in kwargs.items()}
        return wrap(S(*args, **kwargs))

    def __getattr__(self, item):
        return wrap(Name(item))

    def __getitem__(self, item):
        if isinstance(item, str):
            if is_python_name(item):
                return wrap(Name(item))
            else:
                return self(item, parse=True)
        cls = type(item).__name__
        raise TypeError(f"invalid index type: {cls}")


class SMagic:
    def __call__(*args, parse=False, **kwargs):
        """
        Create a Python AST node using the S-Expression syntax.
        """
        self, head, *args = args

        # Single values
        if not args and not kwargs and not parse:
            return self._wrap_simple(head)
        elif parse:
            raise NotImplementedError(head)

        # S-Expr constructors
        args = map(unwrap_nested, args)
        kwargs = {k: unwrap_nested(v) for k, v in kwargs.items()}
        try:
            constructor = sexpr_map[head]
            return constructor(*args, **kwargs)
        except KeyError as exc:
            if callable(head):
                return head(*args, **kwargs)
            raise ValueError(f"invalid S-Expr head: {head!r}") from exc

    def _wrap_simple(self, obj):
        if isinstance(obj, PyAtom):
            return Atom(obj)
        elif isinstance(obj, (list, tuple, dict, set)):
            return to_expr(obj)
        elif isinstance(obj, Wrapper):
            return self(unwrap(obj))
        elif isinstance(obj, (Expr, Stmt)):
            return obj

    @staticmethod
    def let(*args, **kwargs):
        if len(args) == 1:
            kwargs = {**args[0], **kwargs}
        elif len(args) == 2:
            lhs, rhs = args
            return Assign(to_expr(lhs), to_expr(rhs))
        elif len(args) == 2:
            lhs, op, rhs = args
            if op == "=":
                return S.let(lhs, rhs)
            op = InplaceOpEnum.from_name(op)
            return Inplace(op, to_expr(lhs), to_expr(rhs))
        elif len(args) != 0:
            raise TypeError("accept at most 3 positional arguments.")

        if len(kwargs) == 0:
            return Cmd.Pass()
        elif len(kwargs) == 1:
            k, v = next(iter(kwargs.items()))
            return S.let(Name(k), v)
        else:
            return Block([S.let(Name(k), v) for k, v in kwargs.items()])


expr_meta = Expr._meta
stmt_meta = Stmt._meta
sexpr_map = {**expr_meta.sexpr_symbol_map, **stmt_meta.sexpr_symbol_map}
to_expr = expr_meta.coerce
to_stmt = stmt_meta.coerce
py = PyMagic()
S = SMagic()
