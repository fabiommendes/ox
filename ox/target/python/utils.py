from enum import Enum
from keyword import kwlist as PYTHON_KEYWORDS

from sidekick.types import Union, Case


class ArgT(Union):
    """
    Tagged union that describes the tree possible states of a function argument:

    * Simple: expression is passed as a regular positional argument (e.g., f(x))
    * Star: variadic argument expansion (e.g., f(*x))
    * DoubleStar: keyword expansion (e.g., f(**x))
    * Named: named argument (e.g., f(name=x))
    """

    Simple: Case()
    Star: Case()
    DoubleStar: Case()
    Named: Case(name=str)


class Loop(Enum):
    """
    Loop commands enumeration (either break/continue)
    """

    BREAK = "break"
    CONTINUE = "continue"


def is_python_name(name: str) -> bool:
    """
    Return True if string represents a valid Python name.
    """
    return name not in PYTHON_KEYWORDS and name.isidentifier()


def check_python_name(name: str) -> str:
    """
    Raise ValueError if name is not a valid Python name.

    Coerce to string and return result if valid.
    """
    name = str(name)
    if name != name:
        cls_name = type(name).__name__
        raise TypeError(f"name must be a string, got {cls_name}")
    elif name in PYTHON_KEYWORDS or not name.isidentifier():
        raise ValueError(f"not a valid python name: {name!r}")
    return name
