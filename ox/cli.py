def parser_interact(lexer, parser, *args):
    """
    Keep asking a new expression and prints the resulting parse tree.
    """
    while True:
        expr = input("expr: ")
        if expr:
            try:
                tokens = list(lexer(expr))
                print("tokens:", tokens)

                ast = parser(tokens)
                print("ast:", ast)
            except Exception as ex:
                print("error:", ex, "\n")
                continue

            if args:
                value = ast
                for func in args:
                    value = func(value)
                print("final:", value)
            print()
        else:
            break


def lexer_interact(lexer):
    """
    Keep asking a new expressions from lexer and prints the token stream.
    """

    while True:
        expr = input("expr: ")
        if expr:
            print(list(lexer(expr)))
        else:
            break


def main():
    raise SystemExit("Cli is not yet implemented")
