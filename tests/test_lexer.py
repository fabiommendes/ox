import pytest

from ox import lexer, UnexpectedCharacters

values = lambda xs: list(map(lambda x: x.value, xs))
lexemes = lambda xs: list(map(lambda x: str(x), xs))


@pytest.fixture(scope='session')
def calc():
    return lexer(
        INT={r"\d+": int},
        FLOAT={r"\d+\.\d+": float},
        SUM=r"[+-]",
        MUL=r"[*\/]",
        CTRL=r"[()]",
        WS=r"\s+",
        ignore='WS',
    )


class TestLexer:
    def test_calc_lexer(self, calc):
        lex = lambda src, fn: fn(calc(src))
        assert lex("(20 + 1) * 2", lexemes) == ["(", "20", "+", "1", ")", "*", "2"]
        assert lex("(20 + 1) * 2", values) == ["(", 20, "+", 1, ")", "*", 2]

    def test_calc_lexer_emits_error_on_bad_source(self, calc):
        with pytest.raises(UnexpectedCharacters):
            for tk in calc('20 ^ 2'):
                print(tk)
