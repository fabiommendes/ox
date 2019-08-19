import re

import sidekick as sk
from lark import Lark, Token, Visitor, UnexpectedToken
from typing import Callable, Any

from .grammar import load_grammar

LARK_GRAMMAR = load_grammar("lark")
TOKEN, = [x for x in LARK_GRAMMAR.terminals if x.name == "TOKEN"]
TOKEN = TOKEN.pattern.to_regexp()
TOKEN_EXT = re.compile(r"(?P<skip>_)?(?P<name>" + TOKEN + r"?)(?P<priority>_\d+_)?")


class Lexer:
    """
    Base lexer class and interface.
    """

    grammar: str
    lexer_callbacks: dict

    def __init__(self, lex_func):
        self._func = lex_func

    def __call__(self, src, fn=None):
        tks = self._func(src)
        return list(tks) if fn else tks


def lexer(grammar=None, *args, ignore=None, **kwargs) -> Lexer:
    """
    Create a lexer function from token declarations.
    """

    # Validate input
    functions = {k.upper(): v for k, v in kwargs.items() if k.islower()}
    rules = {k: v for k, v in kwargs.items() if k.isupper()}
    bad = {k for k in kwargs if k not in rules and not k.islower()}
    if args:
        extra, = args
        rules.update(rules)
    if any(bad):
        raise TypeError(f"invalid arguments: {bad}")
    if grammar and rules:
        raise ValueError(
            "cannot specify rules by keyword and grammar string simultaneously"
        )
    if isinstance(ignore, str):
        ignore = ignore.split(',')

    # Create a Lark grammar for the given lexing rules
    if grammar:
        return lexer_from_grammar(grammar, functions)
    else:
        lex_rules = [Lex.from_arg(k, v, ignore).check_valid() for k, v in rules.items()]
        grammar = [rule.encode_lark() for rule in lex_rules]
        ignore = [rule.name for rule in lex_rules if rule.ignore]
        if ignore:
            ignore_declaration = "\n".join(f"%ignore {name}" for name in ignore)
            grammar.append(f"\n{ignore_declaration}")
        grammar_source = "\n".join(grammar)
        tokens = [lex.name for lex in lex_rules]

        for rule in lex_rules:
            if rule.transform:
                functions.setdefault(rule.name, rule.transform)
        return lexer_from_grammar(grammar_source, functions, token_names=tokens)


def tokenize(expr, **kwargs):
    """
    Tokenize expression using the given list of rules.

    If you want to run the lexer more than once, it is probably better to
    call lexer() prior passing the input expression.

    Args:
        expr (str):
            The input string.
        which:
            Select the lexer strategy.
    """
    return list(lexer(**kwargs)(expr))


#
# Utility types
#
class Lex:
    @classmethod
    def from_arg(cls, name, arg, ignore=None) -> "Lex":
        """
        Create lex rule from argument.
        """
        m = TOKEN_EXT.fullmatch(name)
        if m is None:
            raise ValueError(f"invalid token name: {name!r}")
        matches = m.groupdict()
        priority = matches["priority"]
        priority = priority and int(priority.strip("_"))
        skip = bool(matches["skip"])
        name = matches["name"]
        ignore = False if ignore is None else name in ignore

        if isinstance(arg, Lex):
            arg.name = name
            arg.ignore = arg.ignore and ignore
            return arg
        elif isinstance(arg, str):
            pattern = arg
            fn = None
        elif isinstance(arg, (tuple, list)):
            pattern, fn = arg
        elif isinstance(arg, dict):
            pattern, fn = arg.popitem()
            if arg:
                raise ValueError("cannot declare more than one pattern at once!")
        else:
            raise TypeError(f"invalid argument for Lex: {arg}")

        return Lex(pattern, name=name, priority=priority, ignore=ignore, transform=fn)

    def __init__(
        self,
        pattern,
        *,
        name=None,
        transform=None,
        priority=None,
        ignore=False,
        skip=False,
    ):
        self.pattern = pattern
        self.name = name
        self.transform = transform
        self.priority = priority
        self.ignore = ignore
        self.skip = skip

    def check_valid(self):
        """
        Raise ValueError if not valid.
        """
        name = self.name
        if name is None:
            raise ValueError("Name must be specified")
        if not name.isidentifier() or not name.isupper():
            raise ValueError(f"Invalid token name: {name!r}")
        return self

    def encode_lark(self) -> str:
        """
        Encode rule as a Lark token declaration.
        """
        parts = [self.name]
        if self.priority is not None:
            parts.append(".{}".format(self.priority))
        parts.append(" : ")
        parts.extend(["/", self.pattern, "/"])
        return "".join(parts)


class TokenVisitor(Visitor):
    """
    Collect token names in the .tokens attribute.
    """

    def __init__(self):
        super().__init__()
        self.tokens = []

    def rule(self, tree):
        raise ValueError("cannot declare rules in Lexer")

    def token(self, tree):
        token = tree[0]
        self.tokens.append(token.value)


#
# Utility functions
#
def lexer_from_grammar(grammar: str, functions, token_names=None) -> Lexer:
    """
    Create lexer from an incomplete Lark grammar.
    """

    if token_names is None:
        token_names = get_tokens(grammar)
    token_names = " | ".join(token_names)
    full_grammar = "start : tk*\ntk : {}\n\n{}".format(token_names, grammar)

    def lex(src):
        return lex_function(src)

    callbacks = {name: token_callback(fn) for name, fn in functions.items()}
    try:
        lark = Lark(full_grammar, parser="lalr", lexer_callbacks=callbacks)
    except UnexpectedToken as exc:
        print("Error creating grammar:")
        print(full_grammar)
        print()
        raise ValueError(f"invalid token declarations: {exc}")
    lex_function = lark.lex
    lex.grammar = grammar
    lex.lexer_callbacks = callbacks
    return sk.fn(lex)


def get_tokens(grammar):
    ast = LARK_GRAMMAR.parse(grammar)
    visitor = TokenVisitor()
    visitor.visit(ast)
    return visitor.tokens


def token_callback(fn: Callable[[str], Any]) -> Callable[[Token], Token]:
    def callback(tk: Token):
        tk.value = fn(tk.value)
        return tk

    return callback
