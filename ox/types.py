import re
from collections.abc import MutableSequence
from typing import Pattern


class SymbolMeta(type):
    def __init__(cls, name, bases, ns):
        super().__init__(name, bases, ns)
        if "regex" in ns and isinstance(ns["regex"], (bytes, str)):
            cls.regex = re.compile(ns["regex"])


class Symbol(metaclass=SymbolMeta):
    """
    Symbols are unique representation of names.
    """

    __slots__ = ("value",)
    value: str
    regex: Pattern = re.compile(".+")

    def __init__(self, name: str, unsafe=False):
        name = str(name)
        if not unsafe and self.regex and not self.regex.fullmatch(name):
            raise ValueError(f"invalid symbol name: {name}")
        self.value = name

    def __repr__(self):
        return "Symbol(%r)" % self.value

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, Symbol):
            return self.value is other.value
        elif isinstance(other, str):
            return self.value == other
        return NotImplemented

    def __hash__(self):
        value = hash(self.value)
        return -1 if value == -1 else -value


class S(MutableSequence):
    """
    Represent an S-expression.
    """

    __slots__ = ("head", "tail")

    @property
    def parts(self):
        return self.head, self.tail

    def __init__(self, head, *args):
        self.head = head
        self.tail = list(args)

    def __setitem__(self, index, value):
        if index == 0:
            self.head = value
        elif index > 0:
            self.tail[index - 1] = value
        else:
            self.tail[index] = value

    def __delitem__(self, index):
        if index == 0:
            raise ValueError("cannot delete head of S-expression")
        del self.tail[index]

    def __getitem__(self, index):
        if index == 0:
            return self.head
        elif index > 0:
            return self.tail[index - 1]
        else:
            return self.tail[index]

    def __len__(self):
        return len(self.tail) + 1

    def __iter__(self):
        yield self.head
        yield from self.tail

    def __repr__(self):
        name = type(self).__name__
        data = ", ".join(map(repr, self.tail))
        return f"{name}({self.head!r}, {data})"

    def insert(self, index, value):
        if index == 0:
            raise ValueError("cannot insert at head position")
        self.tail.index(index, value)
