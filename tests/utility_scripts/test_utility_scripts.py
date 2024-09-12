import pytest
from tx_engine import Context, Script

from src.zkscript.util.utility_scripts import nums_to_script, pick, roll


def generate_verify(z) -> Script:
    out = Script()
    for ix, el in enumerate(z[::-1]):
        out += nums_to_script([el])
        if ix != len(z) - 1:
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out += Script.parse_string("OP_EQUAL")

    return out


@pytest.mark.parametrize(
    ("position", "n_elements", "stack", "expected"),
    [
        (1, 1, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]),
        (2, 1, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 8, 9, 7]),
        (2, 2, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 9, 7, 8]),
        (3, 2, list(range(10)), [0, 1, 2, 3, 4, 5, 8, 9, 6, 7]),
        (5, 2, list(range(10)), [0, 1, 2, 3, 6, 7, 8, 9, 4, 5]),
        (5, 4, list(range(10)), [0, 1, 2, 3, 8, 9, 4, 5, 6, 7]),
        (
            10,
            3,
            list(range(20)),
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 18, 19, 9, 10, 11],
        ),
    ]
)
def test_roll(position, n_elements, stack, expected):
    unlock = nums_to_script(stack)

    lock = roll(position, n_elements)
    lock += generate_verify(expected)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0


@pytest.mark.parametrize(
    ("position", "n_elements", "stack", "expected"),
    [
        (0, 1, list(range(10)), [*list(range(10)), 9]),
        (1, 1, list(range(10)), [*list(range(10)), 8]),
        (1, 2, list(range(10)), [*list(range(10)), 8, 9]),
        (3, 2, list(range(10)), [*list(range(10)), 6, 7]),
        (3, 4, list(range(10)), [*list(range(10)), 6, 7, 8, 9]),
        (10, 3, list(range(20)), [*list(range(20)), 9, 10, 11]),
    ]
)
def test_pick(position, n_elements, stack, expected):
    unlock = nums_to_script(stack)

    lock = pick(position, n_elements)
    lock += generate_verify(expected)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0
