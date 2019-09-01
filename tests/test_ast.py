import pytest
from hypothesis import given
from hypothesis import strategies as st

from ox.ast import Expr, ExprNode, AtomMixin
from sidekick.hypothesis.tree import kwargs
from sidekick.tree import Leaf, Node, SExprBase


#
# Basic class hierarchy for a simple calculator.
#
class Calc(Expr):
    class Meta:
        abstract = True
        root = True


class Add(ExprNode, Calc):
    lhs: Calc
    rhs: Calc

    class Meta:
        sexpr_symbol = "+"


class Sub(ExprNode, Calc):
    lhs: Calc
    rhs: Calc

    class Meta:
        sexpr_symbol = "-"


class Div(ExprNode, Calc):
    lhs: Calc
    rhs: Calc

    class Meta:
        sexpr_symbol = "/"


class Mul(ExprNode, Calc):
    lhs: Calc
    rhs: Calc

    class Meta:
        sexpr_symbol = "*"


class Number(AtomMixin, Calc):
    class Meta:
        types = (float, int)


expr = Calc._meta.coerce


def build_attrs(node, attrs):
    node.attrs.update(attrs)
    return node


def numbers(attr=False, **extra):
    ns = st.one_of(st.floats(**extra), st.integers()).map(Number)

    if attr:
        return ns
    args = kwargs(allow_private=False, exclude=("lhs", "rhs", *dir(Calc)))
    return st.builds(build_attrs, ns, args)


def exprs(depth=5, **kwargs):
    tt = st.one_of(st.just(Add), st.just(Sub), st.just(Mul), st.just(Div))
    if depth == 1:
        arg = numbers(**kwargs)
    else:
        arg = st.one_of(numbers(**kwargs), exprs(depth=depth - 1, **kwargs))
    return st.builds(lambda f, lhs, rhs: f(lhs, rhs), tt, arg, arg)


# ==============================================================================
# Tests
# ==============================================================================


class TestCalcLanguageAST:
    def test_class_hierarchy(self):
        assert not issubclass(Calc, Leaf)
        assert not issubclass(Calc, Node)

        assert issubclass(Add, Node)
        assert issubclass(Add, SExprBase)
        assert not issubclass(Add, Leaf)

        assert issubclass(Number, Leaf)
        assert not issubclass(Number, Node)

    def test_classes_have_slots_set(self):
        n = Number(42)
        e = Add(n, Number(0))
        m = Mul(e, Number(1))
        for ex in [n, e, m]:
            with pytest.raises(AttributeError):
                ex.__dict__

    def test_cannot_create_abstract_nodes(self):
        print(Calc._init)
        with pytest.raises(TypeError):
            print(Calc())

        with pytest.raises(TypeError):
            print(Calc("arg"))

        with pytest.raises(TypeError):
            print(Calc("arg", ["children"]))

    def test_class_metas(self):
        assert Add._meta.root is Calc
        assert not Add._meta.is_root
        assert Number._meta.root is Calc
        assert not Number._meta.is_root

    def test_creates_valid_metadata(self):
        meta = Calc._meta
        assert meta.abstract
        assert meta.root
        assert meta.subclasses == {Add, Sub, Mul, Div, Number}
        assert meta.leaf_subclasses == {Number}
        assert meta.node_subclasses == {Add, Sub, Mul, Div}

    def test_create_node_instances(self):
        num = Number(42)
        assert num.value == 42
        assert isinstance(num, Calc)
        assert num.attrs == {}

        add = Add(Number(40), Number(2))
        assert "lhs" not in add.attrs
        assert "rhs" not in add.attrs
        assert add.lhs == Number(40)
        assert add.rhs == Number(2)
        assert add.lhs.parent is add

    def test_node_set_parent_child_relations(self):
        a = Number(40)
        b = Number(2)
        e = Add(a, b)
        assert e.lhs is a
        assert e.rhs is b
        assert a.parent is e
        assert b.parent is e
        assert a in e.children
        assert b in e.children

    def test_has_a_single_coerce_function_per_root(self):
        assert Add._meta.coerce is Calc._meta.coerce
        assert Number._meta.coerce is Calc._meta.coerce

    def test_coerce_instances(self):
        assert expr(Number(42)) == Number(42)
        assert expr(42) == Number(42)


@pytest.mark.slow
class TestASTInvariants:
    @given(exprs(attr=True, allow_nan=False))
    def test_ast_copy(self, e):
        cp = e.copy()
        assert cp == e
        assert type(cp) is type(e)
        assert e.attrs == cp.attrs

        if isinstance(e, Number):
            assert e.value == cp.value
        else:
            assert e.lhs == cp.lhs
            assert e.rhs == cp.rhs
