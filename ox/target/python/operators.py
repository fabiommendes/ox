import operator as op

from ... import operators as base


class BinaryOp(base.BinaryOp):
    """
    Binary operator
    """

    # By inverse order of precedence

    # Tests
    # We omit the ternary if statement (x if cond else y), which has the lowest
    # precedence, and the boolean negation (not x), which has the highest
    # precedence of short-circuit operators
    OR_ = "or"
    AND_ = "and"

    # Bitwise
    OR = "|"
    XOR = "^"
    AND = "&"
    RSHIFT = ">>"
    LSHIFT = "<<"

    # Arithmetic
    # (Unary ops have a precedence between exponentiation and multiplication)
    ADD = "+"
    SUB = "-"
    MUL = "*"
    TRUEDIV = "/"
    MATMUL = "@"
    MOD = "%"
    FLOORDIV = "//"
    POW = "**"

    @classmethod
    def precedence_mapping(cls):
        return {
            cls.OR_: 1,
            cls.AND_: 2,
            # Bitwise
            cls.OR: 4,
            cls.XOR: 5,
            cls.AND: 6,
            cls.RSHIFT: 7,
            cls.LSHIFT: 7,
            # Plus ops
            cls.ADD: 8,
            cls.SUB: 8,
            # Mul ops
            cls.MUL: 9,
            cls.TRUEDIV: 9,
            cls.MATMUL: 9,
            cls.MOD: 9,
            cls.FLOORDIV: 9,
            # Power
            cls.POW: 10,
        }

    @classmethod
    def function_mapping(cls):
        return {
            cls.OR_: lambda x, y: x or y,
            cls.AND_: lambda x, y: x and y,
            # Bitwise
            cls.OR: lambda x, y: x | y,
            cls.XOR: op.xor,
            cls.AND: lambda x, y: x & y,
            cls.RSHIFT: op.rshift,
            cls.LSHIFT: op.lshift,
            # Plus ops
            cls.ADD: op.add,
            cls.SUB: op.sub,
            # Mul ops
            cls.MUL: op.mul,
            cls.TRUEDIV: op.truediv,
            cls.MATMUL: op.matmul,
            cls.MOD: op.mod,
            cls.FLOORDIV: op.floordiv,
            # Power
            cls.POW: op.pow,
        }

    @classmethod
    def right_associative_set(cls):
        return {cls.POW, cls.OR_, cls.AND_}


class ComparisonOp(base.BinaryOp):
    """
    Comparison operators.
    """

    EQ = "=="
    NE = "!="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="
    IS = "is"
    IS_NOT = "is not"
    IN = "in"
    NOT_IN = "not in"

    @property
    def precedence_level(self):
        return 3

    @classmethod
    def function_mapping(cls):
        return {
            cls.EQ: op.eq,
            cls.NE: op.ne,
            cls.GT: op.gt,
            cls.GE: op.ge,
            cls.LT: op.lt,
            cls.LE: op.le,
            cls.IS: op.is_,
            cls.IS_NOT: op.is_not,
            cls.IN: lambda x, y: x in y,
            cls.NOT_IN: lambda x, y: x not in y,
        }


class UnaryOp(base.Op):
    """
    Unary operators.
    """

    NOT_ = "not"
    POS = "+"
    NEG = "-"
    NOT = "~"


class Inplace(base.Op):
    """
    Inplace operators.
    """

    IOR = "|="
    IXOR = "^="
    IAND = "&="
    IRSHIFT = ">>="
    ILSHIFT = "<<="
    IADD = "+="
    ISUB = "-="
    IMUL = "*="
    ITRUEDIV = "/="
    IMATMUL = "@="
    IMOD = "%="
    IFLOORDIV = "//="
    IPOW = "**="
