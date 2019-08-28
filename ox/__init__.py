"""
A simple compiler of compilers generator based on Lark-parser.
"""
from .exceptions import *
from .lexer import lexer, tokenize
from .logging import log
from .parser import parser, parse

__version__ = "2.0.0b0"
__author__ = "Fábio Macêdo Mendes"
__email__ = "fabiomacedomendes@gmail.com"
