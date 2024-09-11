from dataclasses import dataclass

import pytest
from tx_engine import Context

from src.zkscript.util.utility_scripts import nums_to_script, pick, roll
from tests.utility_scripts.util import generate_verify, save_scripts


@dataclass
class Roll:
    test_script = roll
    # Define filename for saving scripts
    filename = "roll"

    test_data = [
        {"position": 1, "n_elements": 1, "stack": list(range(10)), "expected": [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]},
        {"position": 2, "n_elements": 1, "stack": list(range(10)), "expected": [0, 1, 2, 3, 4, 5, 6, 8, 9, 7]},
        {"position": 2, "n_elements": 2, "stack": list(range(10)), "expected": [0, 1, 2, 3, 4, 5, 6, 9, 7, 8]},
        {"position": 3, "n_elements": 2, "stack": list(range(10)), "expected": [0, 1, 2, 3, 4, 5, 8, 9, 6, 7]},
        {"position": 5, "n_elements": 2, "stack": list(range(10)), "expected": [0, 1, 2, 3, 6, 7, 8, 9, 4, 5]},
        {
            "position": 10,
            "n_elements": 3,
            "stack": list(range(20)),
            "expected": [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 18, 19, 9, 10, 11],
        },
    ]


@dataclass
class Pick:
    test_script = pick
    # Define filename for saving scripts
    filename = "pick"

    test_data = [
        {"position": 0, "n_elements": 1, "stack": list(range(10)), "expected": [*list(range(10)), 9]},
        {"position": 1, "n_elements": 1, "stack": list(range(10)), "expected": [*list(range(10)), 8]},
        {"position": 1, "n_elements": 2, "stack": list(range(10)), "expected": [*list(range(10)), 8, 9]},
        {"position": 3, "n_elements": 2, "stack": list(range(10)), "expected": [*list(range(10)), 6, 7]},
        {"position": 10, "n_elements": 3, "stack": list(range(20)), "expected": [*list(range(20)), 9, 10, 11]},
    ]


def generate_test_cases():
    configurations = [Pick, Roll]
    return [
        (config, test_data["position"], test_data["n_elements"], test_data["stack"], test_data["expected"])
        for config in configurations
        for test_data in config.test_data
    ]


def verify_script(lock, unlock):
    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0


@pytest.mark.parametrize(("config", "position", "n_elements", "stack", "expected"), generate_test_cases())
def test_pick_and_roll(config, position, n_elements, stack, expected, save_to_json_folder):
    unlock = nums_to_script(stack)

    lock = config.test_script(position, n_elements)
    lock += generate_verify(expected)

    verify_script(lock, unlock)

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "pick_and_roll")
