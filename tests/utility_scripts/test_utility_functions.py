import pytest
from tx_engine import Script

from src.zkscript.util.utility_functions import bitmask_to_boolean_list, boolean_list_to_bitmask, optimise_script


@pytest.mark.parametrize(
    ("script", "expected"),
    [
        (["OP_TOALTSTACK", "OP_FROMALTSTACK"] * 10000, []),
        (["OP_TOALTSTACK"], ["OP_TOALTSTACK"]),
        (["OP_ROT", "OP_ROT", "OP_ROT"] * 10000, []),
        (["OP_ROT", "OP_ROT"], ["OP_ROT", "OP_ROT"]),
        (
            ["OP_0", "OP_TOALTSTACK", "OP_FROMALTSTACK", "OP_1", "OP_ROT", "OP_ROT", "OP_ROT", "OP_2"],
            ["OP_0", "OP_1", "OP_2"],
        ),
        (
            ["OP_0", "OP_TOALTSTACK", "OP_1", "OP_ROT", "OP_ROT", "OP_2"],
            ["OP_0", "OP_TOALTSTACK", "OP_1", "OP_ROT", "OP_ROT", "OP_2"],
        ),
        (["OP_TOALTSTACK"] * 10000 + ["OP_FROMALTSTACK"] * 10000, []),
        ([], []),
        (["OP_0", "OP_EQUAL", "OP_NOT", "OP_1"], ["OP_0NOTEQUAL", "OP_1"]),
        (["OP_1", "OP_SWAP", "OP_TUCK"], ["OP_1", "OP_OVER"]),
    ],
)
def test_optimise_script(script, expected):
    optimised_script = optimise_script(Script().parse_string(" ".join(script)))

    assert optimised_script.to_string().split() == expected


@pytest.mark.parametrize(
    ("function", "inputs", "expected"),
    [
        (boolean_list_to_bitmask, {"boolean_list": [True, False, True]}, 5),
        (boolean_list_to_bitmask, {"boolean_list": [False, False, True]}, 4),
        (boolean_list_to_bitmask, {"boolean_list": [True, False, False]}, 1),
        (bitmask_to_boolean_list, {"bitmask": 1, "list_length": 1}, [True]),
        (bitmask_to_boolean_list, {"bitmask": 5, "list_length": 3}, [True, False, True]),
        (bitmask_to_boolean_list, {"bitmask": 4, "list_length": 3}, [False, False, True]),
        (bitmask_to_boolean_list, {"bitmask": 1, "list_length": 3}, [True, False, False]),
    ],
)
def test_bitmask_to_boolean_list_and_reverse(function, inputs, expected):
    assert function(**inputs) == expected
