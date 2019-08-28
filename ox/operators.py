import enum
from typing import Union


class Op(enum.Enum):
    """
    Abstract enum that serves to base class for all enums that list operators.
    """
    _str_to_op: dict
    __precedence_mapping: dict
    _right_associative_set: set

    @classmethod
    def from_name(cls, symb: Union[str, "Op"]) -> "Op":
        """
        Return an Op constant from string.
        """
        if isinstance(symb, cls):
            return symb

        try:
            cache = cls.__dict__['_str_to_op']
        except KeyError:
            cls._str_to_op = cache = {}

        try:
            return cache[symb]
        except KeyError:
            pass

        for op in cls:
            if op.value == symb:
                cache[symb] = op
                return op
        else:
            raise ValueError(f"invalid operator: {symb}")

    def __repr__(self):
        return "Op." + self.name


class BinaryOp(Op):
    """
    Abstract base class for binary operators enumerations.

    Binary operator enums can be inspected for precedence and associativity.
    """

    __precedence_mapping: dict
    __right_associative_set: set

    @classmethod
    def precedence_mapping(cls) -> dict:
        """
        Return the mapping of precedence for all operators defined in this
        enumeration.
        """
        raise NotImplementedError("must be implemented as classmethod in subclass")

    @classmethod
    def right_associative_set(cls) -> set:
        """
        Return the set of all right associative operators. Other operators are
        considered to be left-associative.
        """
        raise NotImplementedError("must be implemented as classmethod in subclass")

    @property
    def precedence_level(self):
        """
        Precedence level of operator. Higher values indicate higher precedence
        """
        try:
            cache = self.__precedence_mapping
        except AttributeError:
            type(self).__precedence_mapping = cache = self.precedence_mapping()
        return cache[self]

    @property
    def right_associative(self):
        """
        True if operator is right-associative.
        """
        try:
            cache = self.__right_associative_set
        except AttributeError:
            type(self).__right_associative_set = cache = self.right_associative_set()
        return self in cache

    @property
    def left_associative(self):
        """
        True if operator is left-associative.
        """
        return not self.right_associative
