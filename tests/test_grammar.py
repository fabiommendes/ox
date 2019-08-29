import pytest
from lark import Lark

from ox.ast import Tree, Token
from sidekick.tree import Transform, TransformArgs


class TestGrammar:
    @pytest.fixture(scope="class")
    def grammar(self):
        def mk_tree(*args, **kwargs):
            return Tree(*args, leaf_class=Token.from_lark_token, **kwargs)

        return Lark(
            """
        !?expr : expr ("+" | "-") term  -> op
               | term
        
        !?term : term ("*" | "/") atom  -> op
               | atom 
        
        ?atom : NUMBER        -> number 
              | "(" expr ")"
        
        NUMBER : /\d+(\.\d+)?/
        %ignore /\s+/
        """,
            start="expr",
            tree_class=mk_tree,
        )

    def test_can_parse_expression(self, grammar):
        ast = grammar.parse("1 + 2")
        assert ast == (
            Tree(
                "op",
                [
                    Tree("number", [Token("1", type="NUMBER")]),
                    Token("+", type="PLUS", start=(1, 3), end=(1, 4)),
                    Tree("number", [Token("2", type="NUMBER")]),
                ],
            )
        )

    def test_tree_transformer(self, grammar):
        class Fn(Transform):
            leaf_class = Token
            node_class = Tree
            number = lambda _, lf: float(lf.children[0].value)

        ast = grammar.parse("1 + 2")
        fn = Fn()
        assert fn(ast) == (
            Tree(
                "op",
                [
                    Token(1.0),
                    Token("+", type="PLUS", start=(1, 3), end=(1, 4)),
                    Token(2.0),
                ],
            )
        )

    def test_tree_arg_transformer(self, grammar):
        class Test(TransformArgs):
            leaf_class = Token
            node_class = Tree

            number = lambda _, n: float(n)
            op = lambda _, lhs, op, rhs: Tree(op, [lhs, rhs])

        ast = grammar.parse("1 + 2")
        fn = Test()
        assert fn(ast) == Tree("+", [1.0, 2.0])
