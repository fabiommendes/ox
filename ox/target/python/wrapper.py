from .expr_ast import Name, Expr, PyAtom, Atom
from .stmt_ast import Stmt
from .utils import is_python_name
from ...ast.wrapper import Wrapper, unwrap, wrap as _wrap

wrap = lambda x: _wrap(x, Py)


class Py(Wrapper, roots=(Expr, Stmt)):
    """
    Wrapper object
    """

    def __repr__(self):
        ref = unwrap(self)
        if isinstance(ref, Atom):
            return f"py({ref.value!r})"
        return f"py[{ref.source()!r}]"


class PyMagic:
    """
    Base class for the magic py object.
    """

    def __call__(self, *args, **kwargs):
        args = tuple(map(unwrap, args))
        kwargs = {k: unwrap(v) for k, v in kwargs.items()}
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


def S(head, *args, parse=False, **kwargs):
    """
    Create a Python AST node using the S-Expression syntax.
    """
    # Single values
    if not args and not kwargs:
        if isinstance(head, str):
            if parse:
                raise NotImplementedError
            return Atom(head)
        elif isinstance(head, PyAtom):
            return Atom(head)

    # S-Expr constructors
    try:
        constructor = sexpr_map[head]
        return constructor(*args, **kwargs)
    except KeyError as exc:
        if callable(head):
            return head(*args, **kwargs)
        raise ValueError(f"invalid S-Expr head: {head!r}") from exc


expr_meta = Expr._meta
stmt_meta = Stmt._meta
sexpr_map = {**expr_meta.sexpr_symbol_map, **stmt_meta.sexpr_symbol_map}
py = PyMagic()
