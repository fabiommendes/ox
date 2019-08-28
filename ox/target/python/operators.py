from ... import operators as base


class BinaryOp(base.BinaryOp):
    """
    Represent an operator
    """

    # By inverse order of precedence

    # Tests
    # We omit the ternary if statement (x if cond else y), which has the lowest
    # precedence, and the boolean negation (not x), which has the highest
    # precedence of short-circuit operators
    OR_ = "or"
    AND_ = "and"

    # Comparisons
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
        op = cls
        return {
            op.OR_: 1,
            op.AND_: 2,
            # Comparisons
            op.EQ: 3,
            op.NE: 3,
            op.GT: 3,
            op.GE: 3,
            op.LT: 3,
            op.LE: 3,
            op.IS: 3,
            op.IS_NOT: 3,
            op.IN: 3,
            op.NOT_IN: 3,
            # Bitwise
            op.OR: 4,
            op.XOR: 5,
            op.AND: 6,
            op.RSHIFT: 7,
            op.LSHIFT: 7,
            # Plus ops
            op.ADD: 8,
            op.SUB: 8,
            # Mul ops
            op.MUL: 9,
            op.TRUEDIV: 9,
            op.MATMUL: 9,
            op.MOD: 9,
            op.FLOORDIV: 9,
            # Power
            op.POW: 10,
        }

    @classmethod
    def right_associative_set(cls):
        return {cls.POW, cls.OR_, cls.AND_}


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
