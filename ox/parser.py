from functools import lru_cache
from typing import TypeVar

from lark import Lark, InlineTransformer
from sidekick import fn

from .grammar import load_grammar, source
from .lexer import Lexer

AST = TypeVar("AST")
LARK_GRAMMAR = load_grammar("lark-expansions")


#
# Parser types
#
class Parser(fn):
    """
    Base class for Parser objects.
    """

    # noinspection PyShadowingNames
    def __init__(self, parser, lexer=None):
        self._lexer = lexer
        super().__init__(parser)

    def lex(self, src):
        """
        Execute the lexer associated with parser.

        Some parser may not have a independent lexer or even have lexing
        dependent of parsing state.
        """
        if self._lexer is None:
            raise ValueError("parser does not have an associated lexer!")
        return self._lexer(src)


class LarkParser(Parser):
    """
    A Lark-powered parser.
    """

    grammar: Lark

    def __init__(self, grammar, **kwargs):
        self.grammar = Lark(grammar, **kwargs)
        super().__init__(self.grammar.parse, self.grammar.lex)


#
# API  functions
#
def parser(*args, **kwargs) -> Parser:
    """
    Create new parser for language.
    """
    arg, *args = args
    if isinstance(arg, str) or hasattr(arg, "read"):
        if args:
            raise ValueError("Lark grammar do not accept extra arguments.")
        return LarkParser(arg, **kwargs)

    # Arg is a lark lexer created with the lexer() function
    options = extract_lark_options(kwargs)
    options.setdefault("parser", "lalr")
    lexer: Lexer = arg
    rules, = args or (kwargs,)
    rule_map = {}
    grammar = "\n".join(["".join(grammar_rules(rules, rule_map)), lexer.grammar])

    if "start" not in rules:
        options.setdefault("start", next(iter(rules)))

    if "transformer" not in options:
        ns = {name: staticmethod(func) for name, func in rule_map.items()}
        transformer_cls = type("Transformer", (InlineTransformer,), ns)
        options.setdefault("transformer", transformer_cls())

    options.setdefault("lexer_callbacks", lexer.lexer_callbacks)
    return LarkParser(grammar, **options)


def parse(src, *args, **kwargs):
    """
    Parse string of source code with parser generated from arguments.

    This function is not as efficient as creating a parser using, but can be
    reasonably effective in most situations by using a lru_cache strategy for
    storing parsers.
    """
    parser_func = get_parser_from_args(args, tuple(kwargs.items()))
    return parser_func(src)


#
# Utilities
#
LARK_OPTIONS = {"parser", "lexer", "start"}


def extract_lark_options(kwargs):
    """Extract items from kwargs and return a dictionary of options for a lark
    grammar."""
    options = {}
    for opt in LARK_OPTIONS:
        try:
            options[opt] = kwargs.pop(opt)
        except KeyError:
            pass
    return options


@lru_cache(16)
def get_parser_from_args(args, kwargs):
    """
    Cached version of parser(), with a different signature.
    """
    return parser(*args, **dict(kwargs))


def grammar_rules(rules, rule_map):
    """
    Yield Lark grammar rules from dictionary of rules passed to parser().
    """
    rule_funcs = {v: k for k, v in rule_map.items()}
    for rule_name, rule_defs in rules.items():
        indent = " " * (len(rule_name) + 2)
        first = True
        yield "?"
        yield rule_name
        yield " : "

        for expansions, func in rule_defs.items():
            alias = None
            if func is not None:
                key = "fn_" + rule_name
                if func.__name__ not in rule_map and func.__name__.isidentifier():
                    key = func.__name__
                name = next_name(rule_map, key)
                rule_funcs[func] = name
                rule_map[name] = func
                alias = name

            for expansion in iter_expansions(expansions):
                if not first:
                    yield indent + "| "
                first = False
                yield expansion
                yield f" -> {alias}\n" if alias else "\n"
        yield "\n"


def next_name(container, key):
    """
    Given a container object and some key prefix, yield the next key with the
    given prefix that is not contained into container.
    """
    if key not in container:
        return key
    for i in range(1, 1000):
        test = f"{key}_{i}"
        if test not in container:
            return test
    raise ValueError(f"could not find a valid name with the {key} prefix")


def iter_expansions(expr):
    """
    Iterate over expansions in a lark rule of the form "expr1 | expr2 | ..."
    """
    if "|" not in expr:
        yield expr
        return

    tree = LARK_GRAMMAR.parse(expr)
    if tree.data != "expansions":
        yield expr
        return
    for child in tree.children:
        yield source(child)
