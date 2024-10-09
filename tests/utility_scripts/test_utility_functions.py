import pytest
from tx_engine import Script

from src.zkscript.util.utility_functions import optimise_script


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
    ],
)
def test_optimise_script(script, expected):
    optimised_script = optimise_script(Script().parse_string(" ".join(script)))

    assert optimised_script.to_string().split() == expected
