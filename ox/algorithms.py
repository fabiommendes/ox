import operator as op
from types import MappingProxyType
from typing import Sequence, Mapping, Container

PYTHON_PRECEDENCE_RULES = MappingProxyType(
    {
        # Short circuit
        "or": 1,
        "and": 2,
        # comparisons
        op.eq: 3,
        op.ne: 3,
        op.gt: 3,
        op.ge: 3,
        op.lt: 3,
        op.le: 3,
        op.is_: 3,
        op.is_not: 3,  # ('in' and 'not in' are not available as functions)
        "==": 3,
        "!=": 3,
        ">": 3,
        ">=": 3,
        "<": 3,
        "<=": 3,
        "in": 3,
        "not in": 3,
        "is": 3,
        "is not": 3,
        # bitwise
        op.or_: 4,
        "|": 4,
        op.xor: 5,
        "^": 5,
        op.and_: 6,
        "&": 6,
        op.rshift: 7,
        op.lshift: 7,
        ">>": 7,
        "<<": 7,
        # arithmetic ops
        op.add: 8,
        op.sub: 8,
        "+": 8,
        "-": 8,
        op.mul: 9,
        op.truediv: 9,
        op.matmul: 9,
        op.mod: 9,
        op.floordiv: 9,
        "*": 9,
        "/": 9,
        "@": 9,
        "%": 9,
        "//": 9,
        # power
        op.pow: 10,
        "**": 10,
    }
)
PYTHON_RIGHT_ASSOCIATIVE = frozenset({op.pow, "**"})
NOT_GIVEN = object()

__all__ = ["reduce_op_chain"]


def reduce_op_chain(
    chain: Sequence,
    precedence: Mapping = None,
    right_assoc: Container = None,
    expr=lambda *args: args,
):
    """
    Reduce operator chain to a single expression.

    Args:
        chain:
            A sequence of [value, op, value, ..., op, value] elements.
        precedence:
            A mapping from operator to their corresponding precedence value.
            Operators with higher precedence will be joined before operators
            with lower precedence. If no precedence is given, it uses default
            Python precedence rules assuming operators are either strings or
            functions of the operator module.
        right_assoc:
            The set of right associative operators. Uses Python rules if precedence
            is also not given.
        expr (callable):
            Function that construct outgoing expressions. Each node is constructed
            by calling expr(op, lhs, rhs).

    Examples:
        >>> reduce_op_chain([1, '*', 2, '+', 3])
        ('+', ('*', 1, 2), 3)
    """
    n = len(chain)
    if n % 2 == 0 or n == 1:
        msg = (
            "chain must alternate between value and operator, ending with an operator."
        )
        raise ValueError(msg)
    if precedence is None and right_assoc is None:
        precedence = PYTHON_PRECEDENCE_RULES
        right_assoc = PYTHON_RIGHT_ASSOCIATIVE
    if right_assoc is None:
        right_assoc = frozenset()

    chain = list(chain)
    values = chain[::2]
    ops = chain[1::2]
    precedences = [
        (precedence[op_], i if op_ in right_assoc else -i) for i, op_ in enumerate(ops)
    ]

    while ops:
        idx, _ = max_item(precedences)
        precedences.pop(idx)
        lhs = values[idx]
        rhs = values.pop(idx + 1)
        values[idx] = expr(ops.pop(idx), lhs, rhs)

    return values[0]


def max_item(seq, *, key=None, default=NOT_GIVEN):
    """
    Return the pair of (position, value) for the maximum value of sequence.
    """

    stream = iter(seq)
    if default is not NOT_GIVEN:
        idx = None
        best = default
    else:
        try:
            idx = 0
            best = next(stream)
        except StopIteration:
            raise ValueError("cannot find maximum value of empty sequence")

    if key is None:
        for i, x in enumerate(stream, 1):
            if x > best or idx is None and x == best:
                idx = i
                best = x
    else:
        best_key = key(best)
        for i, x in enumerate(stream, 1):
            new_key = key(x)
            if new_key > best_key or idx is None and new_key == best_key:
                idx = i
                best = x
                best_key = new_key
    return idx, best


def min_item(seq, *, key=None, default=NOT_GIVEN):
    """
    Return the pair of (position, value) for the minimum value of sequence.
    """

    stream = iter(seq)
    if default is not NOT_GIVEN:
        idx = None
        best = default
    else:
        try:
            idx = 0
            best = next(stream)
        except StopIteration:
            raise ValueError("cannot find maximum value of empty sequence")

    if key is None:
        for i, x in enumerate(stream, 1):
            if x < best or idx is None and x == best:
                idx = i
                best = x
    else:
        best_key = key(best)
        for i, x in enumerate(stream, 1):
            new_key = key(x)
            if new_key < best_key or idx is None and new_key == best_key:
                idx = i
                best = x
                best_key = new_key
    return idx, best
