META_ARGUMENTS = []


class HasMetaMixin:
    """
    Base mixin class that allow sub-classes to tweak some aspect of their
    creation.

    Those methods are executed during the construction of the _meta attribute
    of the class.
    """
    _meta: 'Meta'
    __slots__ = ()

    @classmethod
    def _meta_class(cls):
        """
        Allow to override the class used to construct the _meta attribute.
        """
        from .meta_attr import Meta
        return Meta

    @classmethod
    def _meta_args(cls, meta_obj):
        """
        Executed before creating the _meta attribute for the class.

        Receives an instance of the Meta object declared in the class body and
        returns a dictionary with attributes passed as keyword arguments to the
        Meta constructor.
        """
        kwargs = {}
        for arg in META_ARGUMENTS:
            try:
                kwargs[arg] = getattr(meta_obj, arg)
            except AttributeError:
                pass

        extra = {}
        for attr in dir(meta_obj):
            if not attr.startswith('_') and attr not in kwargs:
                extra[attr] = getattr(meta_obj, attr)
        if extra:
            kwargs['extra'] = extra
        return kwargs

    @classmethod
    def _meta_finalize(cls):
        """
        Executed after the class is created and populated with the _meta
        attribute.

        The default implementation is a no-op, but can be overriden by
        subclasses.
        """

    @classmethod
    def _meta_sexpr_symbol_map(cls) -> dict:
        """
        Return a dictionary of constructors mapping S-Expr heads to their
        corresponding constructor function.
        """
        return {}
