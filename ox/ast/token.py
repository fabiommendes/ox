from sidekick import Leaf
from .utils import attr_property


# noinspection PyShadowingBuiltins
class Token(Leaf):
    """
    Leaf class used to represent tokens.
    """

    __slots__ = ("_type",)
    type = property(lambda self: self._type)
    start = attr_property("pos")
    end = attr_property("end_pos")

    @property
    def string(self):
        try:
            return self._attrs["string"]
        except KeyError:
            return str(self._value)

    @string.setter
    def string(self, value):
        self._attrs["string"] = str(value)

    @classmethod
    def from_lark_token(cls, tk):
        """
        Initialize node from Lark token.
        """
        new = cls(
            tk.value,
            type=tk.type,
            start=(tk.line, tk.column),
            end=(tk.end_line, tk.end_column),
        )
        string = str(tk)
        if string != tk.value:
            new.string = string
        return new

    def __init__(self, value, type="TOKEN", start=None, end=None, **attrs):
        if start is not None:
            attrs["start"] = start
        if end is not None:
            attrs["end"] = end
        super().__init__(value)
        self._attrs = attrs
        self._type = type

    def __str__(self):
        return self.string

    def __eq__(self, other):
        if isinstance(other, Token):
            return self._value == other._value and self.type == other.type
        return self._value.__eq__(other)

    def _repr_node(self):
        return f"{self.type}({self._value!r})"

    def _repr_attrs(self):
        return ", ".join(filter(None, [f"{self.type!r}", super()._repr_attrs()]))

    def _repr_as_child(self):
        if self.type == "TOKEN" and not self._attrs:
            return repr(self._value)
        return self._repr()

    def copy(self) -> "Token":
        new: Token = super().copy()
        new._type = self._type
        return new
