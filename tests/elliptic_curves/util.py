import json
from pathlib import Path

from tx_engine import Script

from src.zkscript.util.utility_classes import StackEllipticCurvePoint, StackNumber
from src.zkscript.util.utility_scripts import nums_to_script, pick, roll


def generate_verify_from_list(elements: list[int]) -> Script:
    out = Script()
    for ix, el in enumerate(elements[::-1]):
        out += nums_to_script([el])
        if ix != len(elements) - 1:
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out += Script.parse_string("OP_EQUAL")
    return out


def generate_verify_point(P, degree) -> Script:  # noqa: N803
    out = Script()
    if not P.is_infinity():
        out += generate_verify_from_list(P.to_list())
    else:
        out += Script.parse_string(
            "0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY " * (degree - 1) + "0x00 OP_EQUALVERIFY 0x00 OP_EQUAL"
        )
    return out


def generate_extended_list(elements: list[list[int]], positions_elements: list[int], filler: int = 1):
    """Take a list of element a fills it with the filler element."""
    if type(positions_elements) is dict:
        positions_elements = positions_elements.values()
    extended_list = []
    positions_elements = [*positions_elements, -1]

    for i in range(len(elements)):
        element_to_add = elements[i]
        extended_list = [*extended_list, *element_to_add]
        extended_list = [
            *extended_list,
            *[filler] * (positions_elements[i] - positions_elements[i + 1] - len(element_to_add)),
        ]

    return extended_list


def generate_test(modulus, P, Q, positions, negations, rolls):  # noqa: N803
    """Generate test case from modulus, lambda, P, Q, their positions and whether they should be negated and rolled."""
    unlocking_script = []
    expected = []

    P_ = -P if negations["P"] else P
    Q_ = (-Q if negations["Q"] else Q) if P != Q else P_

    gradient = P_.get_lambda(Q_)

    unlocking_script = (
        [[modulus], gradient.to_list(), P.to_list(), Q.to_list()]
        if P != Q
        else [[modulus], gradient.to_list(), P.to_list()]
    )
    unlocking_script = generate_extended_list(unlocking_script, positions, 1)  # Generate extended unlocking script

    tuple_to_match = (rolls["lambda"], rolls["P"], rolls["P"]) if P == Q else (rolls["lambda"], rolls["P"], rolls["Q"])
    match tuple_to_match:
        case (False, False, False):
            expected = (
                [[modulus], gradient.to_list(), P.to_list(), Q.to_list()]
                if P != Q
                else [[modulus], gradient.to_list(), P.to_list()]
            )
            positions_expected = positions.values()
        case (False, False, True):
            expected = [[modulus], gradient.to_list(), P.to_list()]
            positions_expected = [
                positions["modulus"] - len(Q.to_list()),
                positions["lambda"] - len(Q.to_list()),
                positions["P"] - len(Q.to_list()),
            ]
        case (False, True, False):
            expected = [[modulus], gradient.to_list(), Q.to_list()]
            positions_expected = [
                positions["modulus"] - len(P.to_list()),
                positions["lambda"] - len(P.to_list()),
                positions["Q"],
            ]
        case (False, True, True):
            expected = [[modulus], gradient.to_list()]
            positions_expected = (
                [positions["modulus"] - 2 * len(P.to_list()), positions["lambda"] - 2 * len(P.to_list())]
                if P != Q
                else [positions["modulus"] - len(P.to_list()), positions["lambda"] - len(P.to_list())]
            )
        case (True, False, False):
            expected = [[modulus], P.to_list(), Q.to_list()] if P != Q else [[modulus], P.to_list()]
            positions_expected = (
                [positions["modulus"] - len(gradient.to_list()), positions["P"]]
                if P == Q
                else [positions["modulus"] - len(gradient.to_list()), positions["P"], positions["Q"]]
            )
        case (True, False, True):
            expected = [[modulus], P.to_list()]
            positions_expected = [
                positions["modulus"] - len(gradient.to_list()) - len(Q.to_list()),
                positions["P"] - len(Q.to_list()),
            ]
        case (True, True, False):
            expected = [[modulus], Q.to_list()]
            positions_expected = [positions["modulus"] - len(gradient.to_list()) - len(P.to_list()), positions["Q"]]
        case (True, True, True):
            expected = [[modulus]]
            positions_expected = (
                [positions["modulus"] - len(gradient.to_list()) - len(P.to_list()) - len(Q.to_list())]
                if P != Q
                else [positions["modulus"] - len(gradient.to_list()) - len(P.to_list())]
            )
    expected = [*expected, (P_ + Q_).to_list()]
    positions_expected = [*[el + len(P.to_list()) for el in positions_expected], len(P.to_list()) - 1]
    expected = generate_extended_list(expected, positions_expected, 1)[1:]

    return {
        "unlocking_script": nums_to_script(unlocking_script),
        "expected": generate_verify_from_list(expected),
        "stack_elements": {
            "lambda": StackNumber(
                positions["lambda"], len(gradient.to_list()), False, roll if rolls["lambda"] else pick
            ),
            "P": StackEllipticCurvePoint(
                StackNumber(positions["P"], len(P.x.to_list()), negations["P"], roll if rolls["P"] else pick),
                StackNumber(
                    positions["P"] - len(P.x.to_list()),
                    len(P.x.to_list()),
                    negations["P"],
                    roll if rolls["P"] else pick,
                ),
            ),
        }
        if P == Q
        else {
            "lambda": StackNumber(
                positions["lambda"], len(gradient.to_list()), False, roll if rolls["lambda"] else pick
            ),
            "P": StackEllipticCurvePoint(
                StackNumber(positions["P"], len(P.x.to_list()), negations["P"], roll if rolls["P"] else pick),
                StackNumber(
                    positions["P"] - len(P.x.to_list()),
                    len(P.x.to_list()),
                    negations["P"],
                    roll if rolls["P"] else pick,
                ),
            ),
            "Q": StackEllipticCurvePoint(
                StackNumber(positions["Q"], len(Q.x.to_list()), negations["Q"], roll if rolls["Q"] else pick),
                StackNumber(
                    positions["Q"] - len(Q.x.to_list()),
                    len(Q.x.to_list()),
                    negations["Q"],
                    roll if rolls["Q"] else pick,
                ),
            ),
        },
    }


def generate_tests(modulus, P, Q, positions: list[dict[str, int]]):  # noqa: N803
    """Generate test cases starting from modulus, P, Q, and the positions in which the gradient, P and Q must be."""
    test_cases = []

    if P != Q:
        for is_p_negated in [True, False]:
            for is_q_negated in [True, False]:
                for is_p_rolled in [True, False]:
                    for is_q_rolled in [True, False]:
                        for is_lambda_rolled in [True, False]:
                            for position in positions:
                                negations = {"P": is_p_negated, "Q": is_q_negated}
                                rolls = {"lambda": is_lambda_rolled, "P": is_p_rolled, "Q": is_q_rolled}
                                test_cases.append(generate_test(modulus, P, Q, position, negations, rolls))
    else:
        for is_p_negated in [True, False]:
            for is_p_rolled in [True, False]:
                for is_lambda_rolled in [True, False]:
                    for position in positions:
                        negations = {"P": is_p_negated}
                        rolls = {"lambda": is_lambda_rolled, "P": is_p_rolled}
                        test_cases.append(generate_test(modulus, P, Q, position, negations, rolls))

    return test_cases


def generate_unlock(P, degree) -> Script:  # noqa: N803
    out = Script()
    if not P.is_infinity():
        out += nums_to_script(P.to_list())
    else:
        out += Script.parse_string("0x00 0x00 " * degree)
    return out


def save_scripts(lock, unlock, save_to_json_folder, filename, test_name):
    if save_to_json_folder:
        output_dir = Path("data") / save_to_json_folder / "elliptic_curves"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_file = output_dir / f"{filename}.json"

        data = {}

        if json_file.exists():
            with json_file.open("r") as f:
                data = json.load(f)

        data[test_name] = {"lock": lock, "unlock": unlock}

        with json_file.open("w") as f:
            json.dump(data, f, indent=4)
