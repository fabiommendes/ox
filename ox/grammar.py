from typing import Union

from lark import Lark, Tree, Token
from pathlib import Path
from functools import lru_cache

OPTIONS = {"lark-expansions": {"start": "expansions"}}
DEFAULTS = {"parser": "lalr"}
SOURCE = {"lark-expansions": "lark"}
PATH = Path(__file__).parent / "grammars"


@lru_cache(8)
def load_grammar(name):
    """
    Load internal grammar.
    """
    base = SOURCE.get(name, name)
    options = {**DEFAULTS, **OPTIONS.get(name, {})}
    with open(PATH / (base + ".lark")) as fd:
        return Lark(fd, **options)


def source(expr: Union[Tree, Token], sep=" ") -> str:
    """
    Linearize concrete syntax tree back to string.

    This only work in grammars that preserve the full concrete grammar.
    """
    if isinstance(expr, Tree):
        return sep.join(source(x, sep=sep) for x in expr.children)
    else:
        return str(expr)
