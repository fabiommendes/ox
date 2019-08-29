from ox.ast import Expr, ExprNode, AtomMixin
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
        sexpr_symbol = '+'


class Sub(ExprNode, Calc):
    lhs: Calc
    rhs: Calc

    class Meta:
        sexpr_symbol = '-'


class Div(ExprNode, Calc):
    lhs: Calc
    rhs: Calc

    class Meta:
        sexpr_symbol = '/'


class Mul(ExprNode, Calc):
    lhs: Calc
    rhs: Calc

    class Meta:
        sexpr_symbol = '*'


class Number(AtomMixin, Calc):
    class Meta:
        types = (float, int)


expr = Calc._meta.coerce


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
