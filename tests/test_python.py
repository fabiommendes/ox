import pytest
from hypothesis import given

# from ox.target.python import List, Tuple, Set, Dict,
from ox.ast import Tree
from ox.hypothesis import py_value
from ox.target.python import (
    Expr,
    Stmt,
    Atom,
    BinOp,
    Name,
    GetAttr,
    Call,
    Return,
    S,
    And,
    Or,
    Ternary,
    Function,
    Block,
)
from ox.target.python import to_expr, py, unwrap

src = lambda x: unwrap(x).source()


class TestMetaClass:
    """
    Check if class hierarchies are correct and metaclasses initialized everything
    nicely
    """

    def test_mro(self):
        assert Atom._meta.root is Expr
        assert Return._meta.root is Stmt

    def test_expr_root(self):
        roles = Expr._meta.wrapper_roles
        sexpr = Expr._meta.sexpr_symbol_map
        assert {"getattr", "fcall"}.issubset(roles.keys())
        assert {"+", "-", "*", "/"}.issubset(sexpr.keys())

    def test_stmt_root(self):
        sexpr = Stmt._meta.sexpr_symbol_map
        assert {"return"}.issubset(sexpr.keys())


class TestExprAstNodeConstruction:
    def test_equality(self):
        # Leaves
        assert to_expr(1) == Atom(1)
        assert Name("x") == Name("x")
        assert Name("x") != Name("y")
        assert Name("x").parent is None

    def test_repr(self):
        # Leaves
        assert repr(Atom(1)) == "Atom(1)"
        assert repr(Name("x")) == "Name('x')"

        # Operators
        assert (
            repr(BinOp("+", Name("x"), Name("y")))
            == "BinOp(Op.ADD, Name('x'), Name('y'))"
        )

    def test_source(self):
        # Leaves
        assert Atom(1).source() == "1"
        assert Name("x").source() == "x"

        # Containers and comprehensions

        # Operators
        assert BinOp("+", Name("x"), Atom(1)).source() == "x + 1"
        assert (
            BinOp(
                "*", BinOp("+", Name("x"), Atom(1)), BinOp("*", Name("y"), Atom(2))
            ).source()
            == "(x + 1) * y * 2"
        )
        assert And(Name("x"), Name("y")).source() == "x and y"
        assert Or(Name("x"), Name("y")).source() == "x or y"

        # Getters
        assert GetAttr(Name("x"), "y").source() == "x.y"
        assert GetAttr(Atom(42), "y").source() == "(42).y"

        # Function call and others
        assert (
            Call.from_args(Name("fn"), Name("x"), y=Atom(42)).source() == "fn(x, y=42)"
        )
        assert (
            Ternary(Name("cond"), Name("x"), Name("y")).source() == "x if cond else y"
        )

    def test_binary_operators(self):
        expr = BinOp("+", Name("x"), Name("y"))
        assert expr.tag == expr.op == expr.operators.ADD
        assert expr.lhs == Name("x")
        assert expr.rhs == Name("y")
        assert expr.source() == "x + y"
        assert len(expr.children) == 2
        assert expr.children == [Name("x"), Name("y")]
        assert expr == BinOp("+", Name("x"), Name("y"))

    def test_getattr_constructor(self):
        e = GetAttr(Name("x"), "foo")
        assert e.expr == Name("x")
        assert e.attrs == {"attr": "foo"}
        assert e.attr == "foo"
        assert e.source() == "x.foo"

    def test_fcall_constructor(self):
        e = Call.from_args(Name("foo"), Atom("bar"), kw=Atom(42))
        assert e.expr == Name("foo")
        assert e.source() == "foo('bar', kw=42)"

    # def _test_container_nodes(self):
    #     assert expr([1, 2]) == List([Atom(1), Atom(2)])
    #     assert expr((1, 2)) == Tuple([Atom(1), Atom(2)])
    #     assert expr({1, 2}) == Set([Atom(1), Atom(2)])
    #     assert expr({1: 2}) == Dict([(Atom(1), Atom(2))])


class TestStmtNodesConstruction:
    def test_fn_def(self):
        fn = Function(Name("fn"), Tree("args", [Name("x")]), Block([Return(Name("x"))]))
        assert fn.source() == "def fn(x):\n    return x\n"


class TestSExprConstructors:
    def test_create_function(self):
        e = S("def", Name("fn"), [Name("x")], [S("return", Name("x"))])
        assert e.source() == "def fn(x):\n    return x\n"


class TestWrapperObject:
    def test_expr_operators(self):
        a = py(1)
        assert repr(a) == "py(1)"
        assert str(a + 1) == "py['1 + 1']"
        assert str(a + 2) == "py['1 + 2']"
        assert str(a + a + a) == "py['1 + 1 + 1']"
        assert str(a.foo) == "py['(1).foo']"
        # assert str(+a) == "py['+1']"
        # assert str(a(1)) == "py['(1)(1)']"
        # assert str(a[1]) == "py['(1)[1]']"

    def test_expr_reversed_operators(self):
        a = py(1)
        assert str(2 + a) == "py['2 + 1']"

    def test_wrapped_expressions(self):
        x = py.x
        y = py.y
        fn = py.fn
        src = lambda x: unwrap(x).source()
        assert src(x.foo) == "x.foo"
        assert src(fn(x)) == "fn(x)"
        assert src((x + y).method()) == "(x + y).method()"

    def test_function_creation(self):
        fn = unwrap(py("def", py.func, [py.x], [py("return", (2 * py.x) + 1)]))
        assert fn.source() == "def func(x):\n    return 2 * x + 1\n"
        assert fn.name.value == "func"
        assert isinstance(fn.args, Tree)
        assert fn.args.children[0] == Name("x")


class TestUtilities:
    def test_free_vars(self):
        assert unwrap(py.x).free_vars() == {"x"}
        assert unwrap(py.x + py.y + 2).free_vars() == {"x", "y"}


@pytest.mark.hypothesis
class _TestHypothesis:
    @given(py_value())
    def test_representation_of_atoms(self, value):
        assert repr(value) == to_expr(value).source()


# class TestExprHelpers:
#     def test_var_helper(self):
#         assert var.x == Name(Symbol('x'))
#
#     def test_construct_expression_from_operators(self):
#         # x + y
#         expr = BinOp(Op.ADD, Name(Symbol('x')), Name(Symbol('y')))
#         assert var.x + var.y == expr
#
#         # f(x)
#         expr = Call(Name(Symbol('f')), [Name(Symbol('x'))], {})
#         assert var.f(var.x) == expr
#
#     def test_construct_expression_with_atom(self):
#         expr = BinOp(Op.ADD, Name(Symbol('x')), Atom(1))
#         assert var.x + 1 == expr
#
#         expr = BinOp(Op.ADD, Atom(1), Name(Symbol('x')))
#         assert 1 + var.x == expr
#
#     def test_expr_function_correctly_convert_sequence_types(self):
#         assert as_expr([1, 2]) == List([Atom(1), Atom(2)])
#         assert as_expr((1, 2)) == Tuple([Atom(1), Atom(2)])
#         assert as_expr({1, 2}) == Set([Atom(1), Atom(2)])
#         assert as_expr({1: 2}) == Dict([(Atom(1), Atom(2))])
#
#     def test_create_attr_access_node(self):
#         assert attr(var.x, 'foo') == GetAttr(var.x, symb.foo)
#
#     def test_create_correct_signature(self):
#         assert str(signature('x', y=1)) == '(x, /, y=Atom(1))'
#
#     def test_create_lambda_expression(self):
#         assert lambd('x')[var.x + 1] == Lambda([symb.x], var.x + 1)
#         assert lambd(var.x)[var.x + 1] == Lambda([symb.x], var.x + 1)
#         assert lambd(x=1)[var.x + 1] == FullLambda(signature(x=1), var.x + 1)
#
#
# class TestStatementHelpers:
#     def test_blocks(self):
#         assert while(0, body=[pass]).source() == 'while 0:\n    pass'
#
#     def test_if_nesting(self):
#         assert if(0, pass).source() == 'if 0:\n    pass'
#         assert if(0, pass, pass).source() == \
#                'if 0:\n    pass\nelse:\n    pass'
#
#         # Simple if with bracket notation
#         assert if(0)[pass].source() == 'if 0:\n    pass'
#
#         # If/else with bracket notation
#         expr = \
#             if(0)[
#                 var.f(),
#                 var.g(),
#             ].else[
#                 var.h(),
#             ]
#         assert expr.source() == (
#             'if 0:\n'
#             '    f()\n'
#             '    g()\n'
#             'else:\n'
#             '    h()'
#         )
#
#         # A single elif without an else
#         expr = \
#             if(0)[
#                 10,
#             ].elif(1)[
#                 11,
#             ]
#         assert expr == if(0, 10, if(1, 11, []))
#         assert expr.source() == (
#             'if 0:\n'
#             '    10\n'
#             'elif 1:\n'
#             '    11'
#         )
#
#         # Multiple elifs without an else
#         expr = \
#             if(0)[
#                 10,
#             ].elif(1)[
#                 11,
#             ].elif(2)[
#                 12,
#             ].elif(3)[
#                 13,
#             ]
#         # assert expr == if(0, pass,
#         #                    if(1, pass, if(2, pass, if(3, pass, []))))
#         assert expr.source() == (
#             'if 0:\n'
#             '    10\n'
#             'elif 1:\n'
#             '    11\n'
#             'elif 2:\n'
#             '    12\n'
#             'elif 3:\n'
#             '    13'
#         )
#
#         # A single elif with an else
#         expr = \
#             if(0)[
#                 pass,
#             ].elif(1)[
#                 pass,
#             ].else[
#                 pass,
#             ]
#         assert expr == if(0, pass, if(1, pass, pass))
#         assert expr.source() == (
#             'if 0:\n'
#             '    pass\n'
#             'elif 1:\n'
#             '    pass\n'
#             'else:\n'
#             '    pass'
#         )
#
#         # Multiple elifs
#         expr = \
#             if(0)[
#                 pass,
#             ].elif(1)[
#                 pass,
#             ].elif(2)[
#                 pass,
#             ].elif(3)[
#                 pass,
#             ].else[
#                 pass,
#             ]
#         # assert expr == if(0, pass,
#         #                   if(1, pass, if(2, pass, if(3, pass, pass))))
#         assert expr.source() == (
#             'if 0:\n'
#             '    pass\n'
#             'elif 1:\n'
#             '    pass\n'
#             'elif 2:\n'
#             '    pass\n'
#             'elif 3:\n'
#             '    pass\n'
#             'else:\n'
#             '    pass'
#         )
#
#
# class TestExprPrinters:
#     def test_source_examples(self):
#         src = expr_source
#         assert src(var.x + 1) == 'x + 1'
#
#         # Precedence
#         assert src((var.x + 1) * 2) == '(x + 1) * 2'
#         assert src(2 * (var.x + 1)) == '2 * (x + 1)'
#         assert src(2 * (-var.x)) == '2 * (-x)'
#
#         # Associativity
#         assert src((var.x + 1) + 2) == '(x + 1) + 2'
#
#         # Function calls
#         assert src(var.f(var.x)) == "f(x)"
#         assert src(var.f(42)) == "f(42)"
#         assert src(var.f(var.x, opt='bar')) == "f(x, opt='bar')"
#         assert src(var.f(opt='bar')) == "f(opt='bar')"
