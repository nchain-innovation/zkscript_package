import json
from itertools import product
from pathlib import Path
from typing import Union

from tx_engine import Script

from src.zkscript.script_types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import boolean_list_to_bitmask
from src.zkscript.util.utility_scripts import nums_to_script


def generate_verify_from_list(elements: list[int]) -> Script:
    """Generate verification script for the list `elements`.

    Args:
        elements (list[int]): The list of elements for which to generate the verification script.
    """
    out = Script()
    for ix, el in enumerate(elements[::-1]):
        out += nums_to_script([el])
        if ix != len(elements) - 1:
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out += Script.parse_string("OP_EQUAL")
    return out


def generate_verify_point(P, degree: int) -> Script:
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


def modify_verify_modulo_check(old_verification_script):
    """Modify the verification script to take the positive modulo of the results before checking the equalities.

    Args:
        old_verification_script: the original verification script
    """

    op_equalverify_with_modulo = "OP_SWAP OP_DEPTH OP_1SUB OP_PICK OP_TUCK OP_ADD OP_SWAP OP_MOD OP_EQUALVERIFY"
    op_equal_with_modulo = op_equalverify_with_modulo.replace("OP_EQUALVERIFY", "OP_EQUAL")
    return Script.parse_string(
        str(old_verification_script)
        .replace("OP_EQUALVERIFY", op_equalverify_with_modulo)
        .replace("OP_EQUAL", op_equal_with_modulo)
    )


def generate_extended_list(elements: list[list[int]], positions_elements: list[int], filler: int = 1) -> list[int]:
    """Take a list of element a fills it with the filler element.

    Args:
        elements (list[list[int]]): the list of elements (each being a list itself) to be extended.
        positions_elements (list[int]): the positions that the elements should take in the extended list.
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
    P,
    Q,
    positions: dict[str, int],
    negations: dict[str, bool],
    rolls: dict[str, bool],
) -> dict[str, Union[Script, StackEllipticCurvePoint, StackFiniteFieldElement]]:
    """Generate test case from modulus, P, Q, their positions and whether they should be negated and rolled.

    The function constructs the arguments we must supply to point_algebraic_addition and point_algebraic_doubling
    (gradient,P,Q,rolling_options, see src/zkscript/elliptic_curves) and the respective unlocking script for a fixed
    couple (±P,±Q) and fixed rolling options.

    Args:
        modulus (int): The characteristic of the field over which the elliptic curve E is defined.
        P: A point P on E.
        Q: A point Q on E.
        positions (dict[str,int]): A dictionary where each key corresponds to one of the arguments
            of point_algebraic_addition/point_algebraic_doubling. The value corresponding to the key is
            the position that element should occupy in the stack.
        negations (dict[str,bool]): A dictionary where each key corresponds to one of the arguments
            of point_algebraic_addition/point_algebraic_doubling. The value corresponding to the key decides
            whether the script should tackle the case ±P (±Q).
        rolls (dict[str,bool]): A dictionary where each key corresponds to one of the arguments
            of point_algebraic_addition/point_algebraic_doubling. The value corresponding to the key decides
            whether the script should roll P (Q).
    """

    P_ = -P if negations["P"] else P
    Q_ = P_ if P == Q else (-Q if negations["Q"] else Q)
    is_gradient_before = positions["gradient"] > positions["P"]
    gradient = P_.gradient(Q_)
    if is_gradient_before:
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
    else:
        unlocking_script = (
            [[modulus], P.to_list(), Q.to_list(), gradient.to_list()]
            if P != Q
            else [
                [modulus],
                P.to_list(),
                gradient.to_list(),
            ]
        )
        unlocking_script = generate_extended_list(
            unlocking_script,
            [positions["modulus"], positions["P"], positions["gradient"]]
            if P == Q
            else [positions["modulus"], positions["P"], positions["Q"], positions["gradient"]],
            1,
        )  # Generate extended unlocking script

    tuple_to_match = (
        (rolls["gradient"], rolls["P"], rolls["P"], is_gradient_before)
        if P == Q
        else (rolls["gradient"], rolls["P"], rolls["Q"], is_gradient_before)
    )
    match tuple_to_match:
        case (False, False, False, True):
            expected = (
                [[modulus], gradient.to_list(), P.to_list(), Q.to_list()]
                if P != Q
                else [[modulus], gradient.to_list(), P.to_list()]
            )
            positions_expected = positions.values()
        case (False, False, True, True):
            expected = [[modulus], gradient.to_list(), P.to_list()]
            positions_expected = [
                positions["modulus"] - len(Q.to_list()),
                positions["gradient"] - len(Q.to_list()),
                positions["P"] - len(Q.to_list()),
            ]
        case (False, True, False, True):
            expected = [[modulus], gradient.to_list(), Q.to_list()]
            positions_expected = [
                positions["modulus"] - len(P.to_list()),
                positions["gradient"] - len(P.to_list()),
                positions["Q"],
            ]
        case (False, True, True, True):
            expected = [[modulus], gradient.to_list()]
            positions_expected = (
                [positions["modulus"] - 2 * len(P.to_list()), positions["gradient"] - 2 * len(P.to_list())]
                if P != Q
                else [positions["modulus"] - len(P.to_list()), positions["gradient"] - len(P.to_list())]
            )
        case (True, False, False, True):
            expected = [[modulus], P.to_list(), Q.to_list()] if P != Q else [[modulus], P.to_list()]
            positions_expected = (
                [positions["modulus"] - len(gradient.to_list()), positions["P"]]
                if P == Q
                else [positions["modulus"] - len(gradient.to_list()), positions["P"], positions["Q"]]
            )
        case (True, False, True, True):
            expected = [[modulus], P.to_list()]
            positions_expected = [
                positions["modulus"] - len(gradient.to_list()) - len(Q.to_list()),
                positions["P"] - len(Q.to_list()),
            ]
        case (True, True, False, True):
            expected = [[modulus], Q.to_list()]
            positions_expected = [positions["modulus"] - len(gradient.to_list()) - len(P.to_list()), positions["Q"]]
        case (True, True, True, True):
            expected = [[modulus]]
            positions_expected = (
                [positions["modulus"] - len(gradient.to_list()) - len(P.to_list()) - len(Q.to_list())]
                if P != Q
                else [positions["modulus"] - len(gradient.to_list()) - len(P.to_list())]
            )
        case (False, False, False, False):
            expected = (
                [[modulus], P.to_list(), Q.to_list(), gradient.to_list()]
                if P != Q
                else [[modulus], P.to_list(), gradient.to_list()]
            )
            positions_expected = (
                [positions["modulus"], positions["P"], positions["Q"], positions["gradient"]]
                if P != Q
                else [positions["modulus"], positions["P"], positions["gradient"]]
            )
        case (False, False, True, False):
            expected = [
                [modulus],
                P.to_list(),
                gradient.to_list(),
            ]
            positions_expected = [
                positions["modulus"] - len(Q.to_list()),
                positions["P"] - len(Q.to_list()),
                positions["gradient"],
            ]
        case (False, True, False, False):
            expected = [
                [modulus],
                Q.to_list(),
                gradient.to_list(),
            ]
            positions_expected = [
                positions["modulus"] - len(P.to_list()),
                positions["Q"],
                positions["gradient"],
            ]
        case (False, True, True, False):
            expected = [[modulus], gradient.to_list()]
            positions_expected = (
                [positions["modulus"] - 2 * len(P.to_list()), positions["gradient"]]
                if P != Q
                else [positions["modulus"] - len(P.to_list()), positions["gradient"]]
            )
        case (True, False, False, False):
            expected = [[modulus], P.to_list(), Q.to_list()] if P != Q else [[modulus], P.to_list()]
            positions_expected = (
                [positions["modulus"] - len(gradient.to_list()), positions["P"] - len(gradient.to_list())]
                if P == Q
                else [
                    positions["modulus"] - len(gradient.to_list()),
                    positions["P"] - len(gradient.to_list()),
                    positions["Q"] - len(gradient.to_list()),
                ]
            )
        case (True, False, True, False):
            expected = [[modulus], P.to_list()]
            positions_expected = [
                positions["modulus"] - len(gradient.to_list()) - len(Q.to_list()),
                positions["P"] - len(gradient.to_list()) - len(Q.to_list()),
            ]
        case (True, True, False, False):
            expected = [[modulus], Q.to_list()]
            positions_expected = [
                positions["modulus"] - len(gradient.to_list()) - len(P.to_list()),
                positions["Q"] - len(gradient.to_list()),
            ]
        case (True, True, True, False):
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
    P,
    Q,
    positions: list[dict[str, int]],
) -> list[dict[str, Union[Script, StackFiniteFieldElement, StackEllipticCurvePoint]]]:
    """Generate test cases starting from modulus, P, Q and the positions modulus, gradient, P and Q should be in.

    The function constructs the arguments we must supply to point_algebraic_addition and point_algebraic_doubling
    (gradient,P,Q,rolling_options, see src/zkscript/elliptic_curves) and the respective unlocking script. The function
    iterates over all possible positions and generates test data for all possible combinations of ±P and ±Q. See
    generate_test for examples.

    Args:
        modulus (int): The characteristic of the field over which the elliptic curve E is defined.
        P: A point P on E.
        Q: A point Q on E.
        positions (list[dict[str,int]): A list of dictionaries. The function iterates over the items
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


def generate_unlock(P, degree) -> Script:
    out = Script()
    if not P.is_infinity():
        out += nums_to_script(P.to_list())
    else:
        out += Script.parse_string("0x00 0x00 " * degree)
    return out


def double_fq2(point, curve, field, extension_field):
    """Compute `2*point` where `point` is a point on an EC in projective coordinates."""
    X = point[0]
    Y = point[1]
    Z = point[2]
    a = curve.a
    b = curve.b

    two = extension_field(field(2), field(0))
    three = extension_field(field(3), field(0))
    six = two * three
    eight = two * two * two

    A = a * X * X + six * b * X * Z - a * a * Z * Z
    B = two * a * X * Z + three * b * Z * Z
    C = three * X * X + a * Z * Z
    X1 = two * X * Y * (Y * Y - B) - two * A * Y * Z
    Y1 = A * C + (Y * Y + B) * (Y * Y - B)
    Z1 = eight * Y * Y * Y * Z

    return [Z1, Y1, X1]


def add_fq2(point_1, point_2, curve, field, extension_field):
    """Compute `point_1 + point_2` where the points are in projective coordinates."""
    X_1 = point_1[0]
    Y_1 = point_1[1]
    Z_1 = point_1[2]
    X_2 = point_2[0]
    Y_2 = point_2[1]
    Z_2 = point_2[2]

    a = curve.a
    b = curve.b

    three = extension_field(field(3), field(0))

    A = a * X_1 * X_2 + three * b * (X_1 * Z_2 + X_2 * Z_1) - a * a * Z_1 * Z_2
    B = a * (X_1 * Z_2 + X_2 * Z_1) + three * b * Z_1 * Z_2
    C = three * X_1 * X_2 + a * Z_1 * Z_2

    X_3 = (X_1 * Y_2 + X_2 * Y_1) * (Y_1 * Y_2 - B) - A * (Y_1 * Z_2 + Y_2 * Z_1)
    Y_3 = A * C + (Y_1 * Y_2 + B) * (Y_1 * Y_2 - B)
    Z_3 = (Y_1 * Y_2 + B) * (Y_1 * Z_2 + Y_2 * Z_1) + C * (X_1 * Y_2 + X_2 * Y_1)

    return [Z_3, Y_3, X_3]


def negate_fq2(point):
    """Compute `2*point` where `point` is a point on an EC in projective coordinates."""
    X = point[0]
    Y = point[1]
    Z = point[2]
    return [X, -Y, Z]


def proj_point_to_script_fq2(point):
    return [val for coord in [[i.x0.to_int(), i.x1.to_int()] for i in point] for val in coord]


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
