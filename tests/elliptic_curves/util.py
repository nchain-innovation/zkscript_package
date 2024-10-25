import json
from itertools import product
from pathlib import Path
from typing import Dict, List, Union

from tx_engine import Script

from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import boolean_list_to_bitmask
from src.zkscript.util.utility_scripts import nums_to_script


def generate_verify_from_list(elements: List[int]) -> Script:
    """Generate verification script for the list `elements`.

    Args:
        elements (List[int]): The list of elements for which to generate the verification script.
    """
    out = Script()
    for ix, el in enumerate(elements[::-1]):
        out += nums_to_script([el])
        if ix != len(elements) - 1:
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out += Script.parse_string("OP_EQUAL")
    return out


def generate_verify_point(P, degree: int) -> Script:  # noqa: N803
    """Generate verification script for P.

    Args:
        P: The point for which to generate the verification script.
        degree (int): The extension degree of the curve E for which P belongs to E. Each coordinate
        of P is made of `degree` elements.
    """
    out = Script()
    if not P.is_infinity():
        out += generate_verify_from_list(P.to_list())
    else:
        out += Script.parse_string(
            "0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY " * (degree - 1) + "0x00 OP_EQUALVERIFY 0x00 OP_EQUAL"
        )
    return out


def generate_extended_list(elements: List[List[int]], positions_elements: List[int], filler: int = 1) -> List[int]:
    """Take a list of element a fills it with the filler element.

    Args:
        elements (List[List[int]]): the list of elements (each being a list itself) to be extended.
        positions_elements (List[int]): the positions that the elements should take in the extended list.
        filler (int = 1): the filler element.

    Example:
        >>> generate_extended_list([[1],[2],[3]],[3,1,0],10)
        [1, 10, 2, 3]

        >>> generate_extended_list([[1],[2],[3]],[3,2,0],10)
        [1, 2, 10, 3]

        >>> generate_extended_list([[1],[2],[3]],[3,2,1],10)
        [1, 2, 3, 10]

        >>> generate_extended_list([[1,2],[3],[4]],[4,2,1],10)
        [1, 2, 3, 4, 10]

        >>> generate_extended_list([[1,2],[3],[4]],[5,2,1],10)
        [1, 2, 10, 3, 4, 10]

        >>> generate_extended_list([[1],[2],[3]],[10,4,2],15)
        [1, 15, 15, 15, 15, 15, 2, 15, 3, 15, 15]
    """
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


def generate_test(
    modulus: int,
    P,  # noqa: N803
    Q,  # noqa: N803
    positions: Dict[str, int],
    negations: Dict[str, bool],
    rolls: Dict[str, bool],
) -> Dict[str, Union[Script, StackEllipticCurvePoint, StackFiniteFieldElement]]:
    """Generate test case from modulus, P, Q, their positions and whether they should be negated and rolled.

    The function constructs the arguments we must supply to point_algebraic_addition and point_algebraic_doubling
    (gradient,P,Q,rolling_options, see src/zkscript/elliptic_curves) and the respective unlocking script for a fixed
    couple (±P,±Q) and fixed rolling options.

    Args:
        modulus (int): The characteristic of the field over which the elliptic curve E is defined.
        P: A point P on E.
        Q: A point Q on E.
        positions (Dict[str,int]): A dictionary where each key corresponds to one of the arguments
            of point_algebraic_addition/point_algebraic_doubling. The value corresponding to the key is
            the position that element should occupy in the stack.
        negations (Dict[str,bool]): A dictionary where each key corresponds to one of the arguments
            of point_algebraic_addition/point_algebraic_doubling. The value corresponding to the key decides
            whether the script should tackle the case ±P (±Q).
        rolls (Dict[str,bool]): A dictionary where each key corresponds to one of the arguments
            of point_algebraic_addition/point_algebraic_doubling. The value corresponding to the key decides
            whether the script should roll P (Q).
    """

    P_ = -P if negations["P"] else P
    Q_ = P_ if P == Q else (-Q if negations["Q"] else Q)

    gradient = P_.get_lambda(Q_)

    unlocking_script = (
        [[modulus], gradient.to_list(), P.to_list(), Q.to_list()]
        if P != Q
        else [[modulus], gradient.to_list(), P.to_list()]
    )
    unlocking_script = generate_extended_list(
        unlocking_script,
        [positions["modulus"], positions["gradient"], positions["P"]]
        if P == Q
        else [positions["modulus"], positions["gradient"], positions["P"], positions["Q"]],
        1,
    )  # Generate extended unlocking script

    tuple_to_match = (
        (rolls["gradient"], rolls["P"], rolls["P"]) if P == Q else (rolls["gradient"], rolls["P"], rolls["Q"])
    )
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
                positions["gradient"] - len(Q.to_list()),
                positions["P"] - len(Q.to_list()),
            ]
        case (False, True, False):
            expected = [[modulus], gradient.to_list(), Q.to_list()]
            positions_expected = [
                positions["modulus"] - len(P.to_list()),
                positions["gradient"] - len(P.to_list()),
                positions["Q"],
            ]
        case (False, True, True):
            expected = [[modulus], gradient.to_list()]
            positions_expected = (
                [positions["modulus"] - 2 * len(P.to_list()), positions["gradient"] - 2 * len(P.to_list())]
                if P != Q
                else [positions["modulus"] - len(P.to_list()), positions["gradient"] - len(P.to_list())]
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
            "gradient": StackFiniteFieldElement(positions["gradient"], False, len(gradient.to_list())),
            "P": StackEllipticCurvePoint(
                StackFiniteFieldElement(positions["P"], negations["P"], len(P.x.to_list())),
                StackFiniteFieldElement(
                    positions["P"] - len(P.x.to_list()),
                    negations["P"],
                    len(P.x.to_list()),
                ),
            ),
        }
        if P == Q
        else {
            "gradient": StackFiniteFieldElement(positions["gradient"], False, len(gradient.to_list())),
            "P": StackEllipticCurvePoint(
                StackFiniteFieldElement(positions["P"], negations["P"], len(P.x.to_list())),
                StackFiniteFieldElement(
                    positions["P"] - len(P.x.to_list()),
                    negations["P"],
                    len(P.x.to_list()),
                ),
            ),
            "Q": StackEllipticCurvePoint(
                StackFiniteFieldElement(positions["Q"], negations["Q"], len(Q.x.to_list())),
                StackFiniteFieldElement(
                    positions["Q"] - len(Q.x.to_list()),
                    negations["Q"],
                    len(Q.x.to_list()),
                ),
            ),
        },
        "rolling_options": boolean_list_to_bitmask(
            [rolls["gradient"], rolls["P"]] if P == Q else [rolls["gradient"], rolls["P"], rolls["Q"]]
        ),
    }


def generate_test_data(
    modulus: int,
    P,  # noqa: N803
    Q,  # noqa: N803
    positions: List[Dict[str, int]],
) -> List[Dict[str, Union[Script, StackFiniteFieldElement, StackEllipticCurvePoint]]]:
    """Generate test cases starting from modulus, P, Q and the positions modulus, gradient, P and Q should be in.

    The function constructs the arguments we must supply to point_algebraic_addition and point_algebraic_doubling
    (gradient,P,Q,rolling_options, see src/zkscript/elliptic_curves) and the respective unlocking script. The function
    iterates over all possible positions and generates test data for all possible combinations of ±P and ±Q. See
    generate_test for examples.

    Args:
        modulus (int): The characteristic of the field over which the elliptic curve E is defined.
        P: A point P on E.
        Q: A point Q on E.
        positions (List[Dict[str,int]): A list of dictionaries. The function iterates over the items
            in the list to generate different test data. Each element in the list is a dictionary, and each
            key in the dictionary corresponds to one of the arguments of point_algebraic_addition or
            point_algebraic_doubling. The value corresponding to the key is the position that element should
            occupy in the stack.
    """
    test_cases = []

    if P != Q:
        for is_p_negated, is_q_negated, is_p_rolled, is_q_rolled, is_gradient_rolled in product(
            [True, False], repeat=5
        ):
            for position in positions:
                negations = {"P": is_p_negated, "Q": is_q_negated}
                rolls = {"gradient": is_gradient_rolled, "P": is_p_rolled, "Q": is_q_rolled}
                test_cases.append(generate_test(modulus, P, Q, position, negations, rolls))
    else:
        for is_p_negated, is_p_rolled, is_gradient_rolled in product([True, False], repeat=3):
            for position in positions:
                negations = {"P": is_p_negated}
                rolls = {"gradient": is_gradient_rolled, "P": is_p_rolled}
                test_cases.append(generate_test(modulus, P, P, position, negations, rolls))

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
