from typing import MutableSequence, Iterable, TypeVar

T = TypeVar('T')


class ChildrenBase(MutableSequence):
    """
    Expose attributes of an object as a sequence.
    """
    __slots__ = ('_ast',)
    _n_children = NotImplemented
    _attrs = NotImplemented

    def __init__(self, ast):
        self._ast = ast

    def __getitem__(self, i: int) -> T:
        return getattr(self._ast, self._attrs[i])

    def __setitem__(self, i: int, o: T) -> None:
        attr = self._attrs[i]
        return setattr(self._ast, attr, o)

    def __delitem__(self, i: int) -> None:
        raise size_error()

    def __len__(self) -> int:
        return self._n_children

    def __iter__(self) -> Iterable[T]:
        ast = self._ast
        get = getattr
        for attr in self._attrs:
            yield get(ast, attr)

    def __repr__(self):
        return str(list(self))

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            lhs = self._ast
            rhs = other._ast
            for attr in self._attrs:
                if getattr(lhs, attr) != getattr(rhs, attr):
                    return False
            return True
        elif isinstance(other, list):
            return len(self) == len(other) and all(x == y for x, y in zip(self, other))
        return NotImplemented

    def insert(self, index: int, obj: T) -> None:
        raise size_error()


def make_children_class(meta, base=ChildrenBase):
    """
    Create an specialized children class for the given meta object.
    """

    class Children(base):
        __slots__ = ()
        _meta = meta
        _attrs = tuple(meta.children())
        _n_children = len(_attrs)

    return Children


#
# Utilities
#
def size_error():
    return ValueError('cannot change the size of children list!')
