from .algorithms import visit_node, transform_list, transform_dict


class Node:
    """
    Base class for all syntax nodes.
    """

    def transform(self, fn):
        """
        Apply function to all nodes on tree.

        The function should return the transformed node or None. If it return
        None, it will remove the node from any list, tuple, set or dict
        container.
        """
        node_type = self.base_class
        new_args = []
        changed = False

        for arg in self.arguments:
            if isinstance(arg, node_type):
                new = fn(arg)
            elif isinstance(arg, (list, tuple, set)):
                new = transform_list(fn, arg, node_type)
            elif isinstance(arg, dict):
                new = transform_dict(fn, arg, node_type)
            else:
                new = arg

            new_args.append(new)
            changed = (new is not arg) or changed

        return type(self)(*new_args) if changed else self

    def filter(self, predicate):
        """
        Return all sub-nodes that obey the predicate. If predicate is a list
        or class, filter all nodes within the given class.
        """
        if isinstance(predicate, (list, tuple)):
            classes = tuple(predicate)
            predicate = lambda x: isinstance(x, classes)
        elif isinstance(predicate, type):
            cls = predicate
            predicate = lambda x: isinstance(x, cls)
        return filter(predicate, self.descendants())

    def visit(self, fn, acc=None):
        """
        Call fn(node, acc) on every element in the tree.

        If acc is not given, it will be initialized as an empty dictionary.
        """
        node_type = self.base_class
        acc = {} if acc is None else acc
        visit_node(self, fn, acc, node_type)
        return acc
