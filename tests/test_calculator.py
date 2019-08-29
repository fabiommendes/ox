import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path

import builtins
from mock import patch

path = Path(__file__).parent.parent / "examples" / "calculator.py"
spec = importlib.util.spec_from_file_location("calculator", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestCalculator:
    def test_eval_examples(self):
        assert mod.eval_expr("1 + 2") == 3.0
        assert mod.eval_expr("2 * 3") == 6.0
        assert mod.eval_expr("(1 + 2) * 3") == 9.0
        assert mod.eval_expr("2^3 + 1") == 9.0
        assert mod.eval_expr("1 + x", x=2) == 3.0

    def test_eval_with_environment(self):
        env = {}
        assert mod.eval_expr("1 + 2", env) == 3.0
        assert mod.eval_expr("x = 2", env) == 2.0
        assert env == {"x": 2.0}
        assert mod.eval_expr("1 + x", env) == 3.0

    def test_mainloop(self):
        inputs = "x = 1; y = 2; (x + y) * y; ; y".split("; ")
        out = io.StringIO()

        with self.input_from(inputs), redirect_stdout(out):
            mod.eval_loop()
        assert out.getvalue() == "1.0\n2.0\n6.0\n"

    def input_from(self, inputs):
        inputs = list(inputs)
        inputs.reverse()
        return patch.object(builtins, "input", lambda *args: inputs.pop())
