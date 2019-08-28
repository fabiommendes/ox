from hypothesis import strategies as st

py_atom = lambda: st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(),
    st.complex_numbers(),
    st.characters(),
    st.binary(),
)


def py_value():
    atom = py_atom()
    return st.one_of(
        atom,
        st.lists(atom),
        st.tuples(atom),
        st.sets(atom),
        st.dictionaries(atom, atom),
    )
