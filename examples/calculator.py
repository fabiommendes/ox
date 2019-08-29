"""
Calculator example from README with some simple extensions.

Exercises for the reader:

1) Add support for simple mathematical functions like sin, cos, sqrt, etc.
2) Support integers as a separate type from floats.
3) Support complex numbers.
4) Implement comparisons and logical operators. Represent true as 1 and false as 0.
"""

import operator as op

import ox

#
# CONSTANTS AND HELPERS
#
binop = (lambda x, op, y: (op.value, x, y))
operations = {'+': op.add, '-': op.sub, '*': op.mul, '/': op.truediv, '^': op.pow}

#
# LEXER
#
lexer = ox.lexer(
    NUMBER={r'\d+(\.\d*)?': float},
    NAME=r'[a-z]+',
    PLUS=r'[+-]',
    MUL=r'[*\/]',
    OP=r'[()^=]',
    WS=r'\s+',
    ignore=['WS'],
)

#
# PARSER
#
parser = ox.parser(
    lexer,
    start={
        'expr | assign': None
    },
    assign={
        'NAME "=" expr': lambda lhs, rhs: {lhs.value: rhs},
    },
    expr={
        'expr PLUS term': binop,
        'term': None,
    },
    term={
        'term MUL pow': binop,
        'pow': None,
    },
    pow={
        r'atom /\^/ pow': binop,
        r'atom': None,
    },
    atom={
        'NUMBER | NAME': lambda x: x.value,
        '"(" expr ")"': None,
    }
)


#
# RUNTIME AND EVALUATOR
#
def eval_ast(node, env):
    """
    Run expression node in the given environment context.

    Args:
        node:
            A tuple, dict, int or string representing an expression.
        env:
            Mapping of variables to values.
    """
    if isinstance(node, tuple):
        head, *tail = node
        func = operations[head]
        args = (eval_ast(x, env) for x in tail)
        return func(*args)
    elif isinstance(node, str):
        return env[node]
    elif isinstance(node, dict):
        env.update(node)
        return next(iter(node.values()))
    else:
        return node


def eval_expr(src, env=None, **kwargs):
    """
    Similar to eval_ast, but receives expression as a string and variables as
    keyword arguments.
    """
    env = {} if env is None else env
    env.update(kwargs)
    return eval_ast(parser(src), env)


def eval_loop(**env):
    """
    Calculator interactive mainloop.
    """
    while True:
        expr = input('> ')
        if not expr:
            if input('quit? [y/N] ').lower() == 'y':
                break
            else:
                continue
        ast = parser(expr)
        print(eval_ast(ast, env))


if __name__ == '__main__':
    print('Starting Ox calculator')
    eval_loop()
