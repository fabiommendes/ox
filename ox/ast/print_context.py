class PrintContext:
    """
    Stores information about the current printing job.
    """

    def __init__(self, indent=0, indentation_string="    "):
        self.indent_level = indent
        self.indentation = indentation_string

    def indent(self, n=1):
        """
        Increase indentation level by n (1, if not given).
        """
        self.indent_level += n

    def dedent(self, n=1):
        """
        Decrease indentation level by n (1, if not given).
        """
        if self.indent_level < n:
            raise ValueError("cannot dedent bellow zero")
        self.indent_level -= n

    def start_line(self):
        """
        Return the indentation string for the current level.
        """
        return self.indentation * self.indent_level