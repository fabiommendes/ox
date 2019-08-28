from functools import lru_cache


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


def wrap_tokens(it, wrap=True):
    """
    Wrap iterable with two parenthesis tokens.

    Args:
        it:
            Iterator of token elements
        wrap (bool):
            If False, simply yield the contents of it without wrapping it with
            delimiters.
    """
    if wrap is True:
        yield '('
        yield from it
        yield ')'
    elif wrap:
        left, right = wrap
        yield left
        yield from it
        yield right
    else:
        yield from it


def from_template(command, ctx):
    """
    Render template in given context. Return an interator over all tokens

    Args:
        command:
            String template.
        ctx:
            A mapping from names to token iterables. Each iterator yield a sequence
            of tokens used to construct the given string argument.
    """
    renderer = get_renderer(command)
    return renderer(ctx)


@lru_cache(256)
def get_renderer(template):
    def renderer(ctx):
        data = {k: ''.join(v) for k, v in ctx.items()}
        return template.format(**data)

    return renderer


def attr_property(name, default=None, readonly=False):
    """
    Expose an attribute as a property.
    """

    @property
    def prop(self):
        print('name', self.attrs)
        return self.attrs.get(name, default)

    if readonly:
        return prop

    @prop.setter
    def prop(self, value):
        self.attr[name] = value

    return prop
