===========================
Example: Brainfuck compiler
===========================

Brainfuck is an esoteric programming language created to be very easy to
compile, while being very hard to use. It is based on 8 characters which encode
simple instructions on a memory tape that store single byte elements.

.. _Brainfuck: https://en.wikipedia.org/wiki/Brainfuck

``'>'``:
    increment the data pointer (to point to the next cell to the right).
``'<'``:
    decrement the data pointer (to point to the next cell to the left).
``'+'``:
    increment (increase by one) the byte at the data pointer.
``'-'``:
    decrement (decrease by one) the byte at the data pointer.
``'.'``:
    output the byte at the data pointer.
``','``:
    accept one byte of input, storing its value in the byte at the data pointer.
``'['``:
    if the byte at the data pointer is zero, then instead of moving the instruction pointer forward to the next command, jump it forward to the command after the matching ] command.
``']'``:
    if the byte at the data pointer is nonzero, then instead of moving the instruction pointer forward to the next command, jump it back to the command after the matching [ command.

Any other character is ignored and treated as a comment.

The classic "Hello world" is complicated enough that people entertain with
coding golf challenges to implement the smallest "hello world" program. Let us
stick with something simpler:

    ++>+<[->+<]>

This Brainfuck program saves 2 at the first position and 1 at the second and sums
the two arguments, saving the result (3) on the second position. In Python this
would be the expression ``2 + 1``. If we want a low level translation to Python,
the corresponding program would be something like that:

.. code-block:: python

    # initialize tape (execute the  ++>+< part)
    tape = [2, 1]

    # Put cursor in the initial position
    idx = 0

    # Execute the loop (the [->+<] part)
    while tape[idx]:
        tape[idx] = (tape[idx] - 1) % 256  # -
        idx += 1                           # >
        tape[idx] = (tape[idx] + 1) % 256  # +
        idx -= 1                           # <

We want to generate this code automatically from Brainfuck source.

The grammar
-----------

In Brainfuck, we don't quite need a lexer and a sophisticated parser since all
instructions are a single character long. We will implement both the lexer and
the parser using ox infrastructure just to show the API. In order to make
things slightly more difficult, let us implement a few very simple optimizations
in our compiler.

.. code-block:: python

    import ox

    parser = ox.parser(r"""
    start : cmd*
    cmd   : /[+-]+/ -> change
          | /[<>]+/ -> move
          | "."     -> putchar
          | ","     -> getchar
          | "[" cmd* "]" -> loop
    %ignore /[^-+\[\]<>,.]+/
    """)

Our grammar recognizes sequences of repeated operations moving and incrementing
the data pointer. Those operations can be easily lumped together to emit a single
Python command in the final code.

Runtime and transformations
---------------------------

We want to emit Python code like the following:

.. code-block:: python

    # BRAINFUCK
    # ++>+<[->+<]>                      2 plus 1 is 3
    # ++++++++++ ++++++++++
    # ++++++++++ ++++++++++ ++++++++ .  add ascii 0 and print

    # PYTHON
    def main():
        tape = [0] * 30000
        ptr = 0

        tape[ptr] = (tape[ptr] + 2) % 256
        ptr += 1
        tape[ptr] = (tape[ptr] + 1) % 256
        ptr -= 1
        while tape[ptr]:
            tape[ptr] = (tape[ptr] - 1) % 256
            ptr += 1
            tape[ptr] = (tape[ptr] + 1) % 256
            ptr -= 1
        ptr += 1
        tape[ptr] = (tape[ptr] + 48) % 256
        print(chr(tape[ptr]), end='', flush=True)

    if __name__ == '__main__':
        main()


Python code emission
--------------------

>>> print(parser('++>+<').pretty())   # doctest: +NORMALIZE_WHITESPACE
start
  change        ++
  move          >
  change        +
  move          <
<BLANKLINE>

We can transform those fragments into Python code using a transformer.

.. code-block:: python

    from lark import InlineTransformer
    from ox.target.python import py, S

    ptr = py.ptr
    tape = py.tape


    class Transformer(InlineTransformer):
        def change(self, by):
            by = by.count('+') - by.count('-')
            if by > 0:
                return S('=', tape[ptr], (tape[ptr] + by) % 256)
            elif by < 0:
                return S('=', tape[ptr], (tape[ptr] - (-by)) % 256)
            else:
                return S(...)

        def move(self, by):
            by = by.count('>') - by.count('<')
            if by > 0:
                return S('+=', ptr, by)
            elif by < 0:
                return S('-=', ptr, abs(by))
            else:
                return S(...)

        def putchar(self):
            return S(py.putchar(tape[ptr]))

        def getchar(self):
            return S.let(tape[ptr], py.getchar())

        def loop(self, *cmds):
            return S('while', tape[ptr], [
                *cmds,
            ])

        def start(self, *cmds):
            if len(cmds) == 1:
                return cmds[0]
            return S('do', *cmds)

    def parse(st):
        tree = parser(st)
        return Transformer().transform(tree)


Now we can test parsing some very simple code,

>>> parse('>>>')
Inplace(Op.IADD, Name('ptr'), Atom(3))

Perhaps it is more clear to print the corresponding source code.

>>> print(parse('>>>').source())
ptr += 3

Move, print, get input and other instructions can be similarly
analyzed

>>> print(parse('+++.').source())
tape[ptr] = (tape[ptr] + 3) % 256
putchar(tape[ptr])

>>> print(parse(',').source())
tape[ptr] = getchar()

The loop instruction creates a while block with its contents.
Likewise, we can create elements

>>> print(parse('[+>-<]').source())  # doctest: +NORMALIZE_WHITESPACE
while tape[ptr]:
    tape[ptr] = (tape[ptr] + 1) % 256
    ptr += 1
    tape[ptr] = (tape[ptr] - 1) % 256
    ptr -= 1
<BLANKLINE>

# TODO: discuss!

Finally, the ``program()`` function wraps it all: it creates the necessary
import statements, the code to initialize the tape and appends the instructions
collected from the other functions:

.. code-block:: python

    def program(body):
        return S('do',
            S('import from', py.getch, {'getche': 'getchar'}),
            S('def', py.main, [], [
                S.let(tape=py([0]) * 30000),
                S.let(ptr=0),
                *body,
            ]),
            S('if', py.__name__ == '__main__', [
                py.main(),
                S.let(x=42),
                S('del', py.x),
            ])
        )


We can test it with an empty body:

>>> print(program([]).source())
from getch import getche as getchar
def main():
    tape = [0] * 30000
    ptr = 0
<BLANKLINE>
if False:
    main()
    x = 42
    del x
<BLANKLINE>


Parsing
-------

With this, we can build our parser:

.. code-block:: python

    ...

After putting all this together, we feed our simple example to the parser:

>>> print(parse('++>+<[->+<]> 2 plus 1 is 3').source())
tape[ptr] = (tape[ptr] + 2) % 256
ptr += 1
tape[ptr] = (tape[ptr] + 1) % 256
ptr -= 1
while tape[ptr]:
    tape[ptr] = (tape[ptr] - 1) % 256
    ptr += 1
    tape[ptr] = (tape[ptr] + 1) % 256
    ptr -= 1
<BLANKLINE>
ptr += 1

That looks nice :)

In order to really test our parser, we can feed a complicated Brainfuck code
such as the Rot13 encoder from the Wikipedia example:

    -,+[                         Read first character and start outer character reading loop
        -[                       Skip forward if character is 0
            >>++++[>++++++++<-]  Set up divisor (32) for division loop
                                   (MEMORY LAYOUT: dividend copy remainder divisor quotient zero zero)
            <+<-[                Set up dividend (x minus 1) and enter division loop
                >+>+>-[>>>]      Increase copy and remainder / reduce divisor / Normal case: skip forward
                <[[>+<-]>>+>]    Special case: move remainder back to divisor and increase quotient
                <<<<<-           Decrement dividend
            ]                    End division loop
        ]>>>[-]+                 End skip loop; zero former divisor and reuse space for a flag
        >--[-[<->+++[-]]]<[         Zero that flag unless quotient was 2 or 3; zero quotient; check flag
            ++++++++++++<[       If flag then set up divisor (13) for second division loop
                                   (MEMORY LAYOUT: zero copy dividend divisor remainder quotient zero zero)
                >-[>+>>]         Reduce divisor; Normal case: increase remainder
                >[+[<+>-]>+>>]   Special case: increase remainder / move it back to divisor / increase quotient
                <<<<<-           Decrease dividend
            ]                    End division loop
            >>[<+>-]             Add remainder back to divisor to get a useful 13
            >[                   Skip forward if quotient was 0
                -[               Decrement quotient and skip forward if quotient was 1
                    -<<[-]>>     Zero quotient and divisor if quotient was 2
                ]<<[<<->>-]>>    Zero divisor and subtract 13 from copy if quotient was 1
            ]<<[<<+>>-]          Zero divisor and add 13 to copy if quotient was 0
        ]                        End outer skip loop (jump to here if ((character minus 1)/32) was not 2 or 3)
        <[-]                     Clear remainder from first division if second division was skipped
        <.[-]                    Output ROT13ed character from copy and clear it
        <-,+                     Read next character
    ]                            End character reading loop

.. _Wikipedia: https://en.wikipedia.org/wiki/Brainfuck#ROT13
