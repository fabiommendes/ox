import operator


def infix_operator_node(op, paren=True):
    """
    Returns an emitter for the given infix operator.
    """

    def emit(node, ctx):
        lhs, rhs = node.value
        if paren:
            yield "("
        ctx.emit_expr(lhs, ctx)
        yield op
        ctx.emit_expr(lhs, ctx)
        if paren:
            yield ")"

    return emit


def block(
    node, file, ctx, statements=operator.attrgetter("value"), open=None, close=None
):
    """
    Emits code for an AST node that represents a list of statements.

    Args:
        node:
            The ast node representing the block.
        file:
            The file object used to emit code.
        ctx:
            Emission context.
        statements:
            A function that receives a node and return a list of statements.
            The default behavior is to fetch the list from the .value attribute
            of the node.
        open, close:
            The open/close tokens for the block. (e.g., "{", "}" for C-family
            languages).
    """
    if open:
        yield open
    yield ctx.new_line

    ctx.indent += 1
    for stm in statements(node):
        ctx.emit_stm(stm, file, ctx)
        yield ctx.new_line
    ctx.indent -= 1

    if close:
        yield close
    yield ctx.new_line


def fcall(node, file, ctx, open="(", close=")", sep=", "):
    """
    C-style function call from a node that has (func_name, args) elements.

    Can control the opening/closing bracket and argument separator.
    """

    func_name, args = node.value
    yield func_name
    array(args, file, ctx, items=lambda x: x, open=open, close=close, sep=sep)


def array(
    node, file, ctx, items=operator.attrgetter("value"), open="{", close="}", sep=", "
):
    """
    C-style array declaration. You can control the the opening/closing bracket
    and item separator and adapt it to other languages and linear data
    structures.
    """

    write = file.write
    emit = ctx.emit_expr

    data = items(node)
    yield open

    if len(data) == 1:
        item, = data
        emit(item)
    elif len(data) > 1:
        for item in items[:-1]:
            emit(item)
            yield sep
        emit(items[-1])
    yield close


def assign(node, file, ctx, operator=" = ", end=";"):
    """
    Emits a C-style assignment command from a node that has a (lhs, rhs) in
    its .value attribute.

    Can control the assignment operator (=) and the line end (;).
    """

    lhs, rhs = node.value
    if isinstance(lhs, str):
        yield lhs
    else:
        yield from ctx.emit_expr(lhs)

    yield operator
    yield from ctx.emit_expr(rhs)

    if end:
        yield end
