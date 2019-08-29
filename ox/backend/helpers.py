from copy import copy


class LetMagic:
    """
    DSL for assignment and sequencing.

    Let(a=expr_1, b=expr_2, ...) -> variable bindings
    Let(stmt1, stmt2, ...)       -> sequencing
    Let[tt](a=expr_1, b=expr_2)  -> assignment with types
    Let[tt](stmt1, stmt2, ...)   -> associate type with all arguments
    """

    def __init__(
        self, to_expr, to_name, mk_assign, mk_inplace, mk_block, to_stmt, mk_type=None
    ):
        self._to_expr = to_expr
        self._to_name = to_name
        self._to_stmt = to_stmt
        self._mk_assign = mk_assign
        self._mk_inplace = mk_inplace
        self._mk_block = mk_block
        self._mk_type = mk_type or (lambda x: x)
        self._type = None

    def __call__(self, *args, **kwargs):
        binds = [*map(self._to_stmt, args), *map(self._from_pair, kwargs.items())]
        return self._mk_block(binds) if len(binds) != 1 else binds[0]

    def __getitem__(self, cls):
        new = copy(self)
        new._type = self._mk_type(cls)
        return new

    def _from_pair(self, pair):
        name, value = pair
        name = self._to_name(name)
        value = self._to_expr(value)
        return self._mk_assign(name, value)
