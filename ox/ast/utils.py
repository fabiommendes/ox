class NotImplementedDescriptor:
    """
    Simple descriptor that raises error when instance tries to access method
    or operator
    """

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        name = getattr(self, "name", "<unknown method>")
        cls = cls.__name__
        raise NotImplementedError(f"{cls} does not implement {name}")

    def __set_name__(self, owner, name):
        self.name = name


def wrap_tokens(it, sep="()", *, wrap=True):
    """
    Wrap iterable with two parenthesis tokens.

    Args:
        it:
            Iterator of token elements
        sep:
            A two element sequence with the left and right delimiters.
        wrap (bool):
            If False, simply yield the contents of it without wrapping it with
            delimiters.
    """
    left, right = sep
    if wrap:
        yield left
    yield from it
    if wrap:
        yield right
