from dataclasses import dataclass

import pytest
from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.models.ec import ShortWeierstrassEllipticCurve
from tx_engine import Context, Script

from src.zkscript.elliptic_curves.ec_operations_fq_projective import EllipticCurveFqProjective
from src.zkscript.script_types.stack_elements import (
    StackEllipticCurvePointProjective,
    StackFiniteFieldElement,
    StackNumber,
)
from src.zkscript.script_types.unlocking_keys.msm_with_fixed_bases_projective import (
    MsmWithFixedBasesProjectiveUnlockingKey,
)
from src.zkscript.script_types.unlocking_keys.unrolled_projective_ec_multiplication import (
    EllipticCurveFqProjectiveUnrolledUnlockingKey,
)
from src.zkscript.util.utility_scripts import nums_to_script
from tests.elliptic_curves.util import (
    save_scripts,
)
from tests.elliptic_curves.util_projective_ec import (
    add,
    double,
    generate_multi_addition_tests,
    msm,
    multiply,
    negate,
    proj_to_list,
    to_aff,
    to_proj,
)


@dataclass
class Secp256k1:
    modulus = 115792089237316195423570985008687907853269984665640564039457584007908834671663
    order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    base_field = PrimeField(modulus)
    scalar_field = PrimeField(order)
    curve = ShortWeierstrassEllipticCurve(a=base_field(0), b=base_field(7))
    degree = 1
    point_at_infinity = [base_field.zero(), base_field.identity(), base_field.zero()]
    generator = curve(
        x=base_field(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798),
        y=base_field(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8),
        infinity=False,
    )
    test_script = EllipticCurveFqProjective(q=modulus, curve_a=0, curve_b=7)
    # Define filename for saving scripts
    filename = "curve_projective"
    # Test data
    P = double(
        to_proj(
            curve(
                x=base_field(41215615274060316946324649613818309412392301453105041246304560830716313169400),
                y=base_field(74117305601093926817905542912257614464261406761524109253393548124815807467650),
                infinity=False,
            ),
            base_field,
        ),
        curve,
        base_field,
    )
    Q = double(
        to_proj(
            curve(
                x=base_field(75022427023119710175388682918928560109160388746708368835324539025120909485774),
                y=base_field(70716735503538187278140999937647087780607401911659658020223121861184446029572),
                infinity=False,
            ),
            base_field,
        ),
        curve,
        base_field,
    )
    a = 64046112301879843941239178948101222343000413030798872646069227448863068996094
    test_data = {
        "test_addition": [
            {"P": P, "Q": Q},
            {"P": double(P, curve, base_field), "Q": Q},
        ],
        "test_doubling": [
            {"P": P},
            {"P": add(P, Q, base_field)},
        ],
        "test_multiplication_unrolled": [
            {"P": P, "a": a, "expected": multiply(P, a, curve, base_field), "max_multiplier": order},
            {"P": P, "a": 0, "expected": point_at_infinity, "max_multiplier": order},
            {
                "P": P,
                "a": order // 4,
                "expected": multiply(P, order // 4, curve, base_field),
                "max_multiplier": order // 2,
            },
        ],
        "test_to_affine": [
            {"P": P, "expected": to_aff(P, curve, base_field)},
            {"P": Q, "expected": to_aff(Q, curve, base_field)},
        ],
        "test_addition_unknown_points": [
            {"P": P, "Q": Q, "expected": add(Q, P, base_field)},
            {"P": P, "Q": point_at_infinity, "expected": P},
            {"P": point_at_infinity, "Q": Q, "expected": Q},
            {"P": P, "Q": negate(P), "expected": point_at_infinity},
            {
                "P": P,
                "Q": [base_field(2) * P[0], base_field(2) * -P[1], base_field(2) * P[2]],
                "expected": point_at_infinity,
            },
        ],
        "test_multi_addition": [
            *generate_multi_addition_tests([P, Q, P, Q], base_field),
            *generate_multi_addition_tests([P, Q, P, point_at_infinity], base_field),
            *generate_multi_addition_tests([point_at_infinity, P, Q, Q], base_field),
            *generate_multi_addition_tests([P, negate(P), P, negate(P)], base_field),
        ],
        "test_msm_with_fixed_bases": [
            {
                "scalars": [
                    91480703662782754180582857755469238521183816015595091307545684157518834179962,
                    47070595863165885427430233112660476768577559097282104975413125241877698242896,
                    9224493153332625135218701509907469141303400067447258343326975920405791097566,
                    31206083188178209172482180095895746394525486465923231870455125188479567353247,
                ],
                "bases": [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                "expected": msm(
                    [
                        91480703662782754180582857755469238521183816015595091307545684157518834179962,
                        47070595863165885427430233112660476768577559097282104975413125241877698242896,
                        9224493153332625135218701509907469141303400067447258343326975920405791097566,
                        31206083188178209172482180095895746394525486465923231870455125188479567353247,
                    ],
                    [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                    curve,
                    base_field,
                ),
            },
            {
                "scalars": [
                    0,
                    47070595863165885427430233112660476768577559097282104975413125241877698242896,
                    9224493153332625135218701509907469141303400067447258343326975920405791097566,
                    31206083188178209172482180095895746394525486465923231870455125188479567353247,
                ],
                "bases": [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                "expected": msm(
                    [
                        0,
                        47070595863165885427430233112660476768577559097282104975413125241877698242896,
                        9224493153332625135218701509907469141303400067447258343326975920405791097566,
                        31206083188178209172482180095895746394525486465923231870455125188479567353247,
                    ],
                    [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                    curve,
                    base_field,
                ),
            },
            {
                "scalars": [
                    91480703662782754180582857755469238521183816015595091307545684157518834179962,
                    0,
                    0,
                    31206083188178209172482180095895746394525486465923231870455125188479567353247,
                ],
                "bases": [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                "expected": msm(
                    [
                        91480703662782754180582857755469238521183816015595091307545684157518834179962,
                        0,
                        0,
                        31206083188178209172482180095895746394525486465923231870455125188479567353247,
                    ],
                    [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                    curve,
                    base_field,
                ),
            },
            {
                "scalars": [
                    0,
                    0,
                    0,
                    0,
                ],
                "bases": [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                "expected": msm(
                    [
                        0,
                        0,
                        0,
                        0,
                    ],
                    [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                    curve,
                    base_field,
                ),
            },
        ],
    }


@dataclass
class Secp256r1:
    modulus = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
    order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
    base_field = PrimeField(modulus)
    scalar_field = PrimeField(order)
    curve = ShortWeierstrassEllipticCurve(
        a=base_field(0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC),
        b=base_field(0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B),
    )
    degree = 1
    point_at_infinity = [base_field.zero(), base_field.identity(), base_field.zero()]
    generator = curve(
        x=base_field(0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296),
        y=base_field(0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5),
        infinity=False,
    )
    test_script = EllipticCurveFqProjective(
        q=modulus,
        curve_a=0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC,
        curve_b=0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B,
    )
    # Define filename for saving scripts
    filename = "secp256r1_projective"
    # Test data
    P = double(
        to_proj(
            curve(
                x=base_field(11990862373011617163317646558408705408882310560667899835694339942976011369232),
                y=base_field(80247255150202856195005696069978490751513498800937223995637125987523375481630),
                infinity=False,
            ),
            base_field,
        ),
        curve,
        base_field,
    )
    Q = double(
        to_proj(
            curve(
                x=base_field(64260480261783363550587538316957846447400713742342025589747159311266528268825),
                y=base_field(68194036500363828464317082173162010818073467174652382578837906057865410662381),
                infinity=False,
            ),
            base_field,
        ),
        curve,
        base_field,
    )
    a = 104614095137500434070196828944928516815982260532830080798264081596642730786155
    test_data = {
        "test_addition": [
            {"P": P, "Q": Q},
            {"P": double(P, curve, base_field), "Q": Q},
        ],
        "test_doubling": [
            {"P": P},
            {"P": add(P, Q, base_field)},
        ],
        "test_multiplication_unrolled": [
            {"P": P, "a": a, "expected": multiply(P, a, curve, base_field), "max_multiplier": order},
            {"P": P, "a": 0, "expected": point_at_infinity, "max_multiplier": order},
            {
                "P": P,
                "a": order // 4,
                "expected": multiply(P, order // 4, curve, base_field),
                "max_multiplier": order // 2,
            },
        ],
        "test_to_affine": [
            {"P": P, "expected": to_aff(P, curve, base_field)},
            {"P": Q, "expected": to_aff(Q, curve, base_field)},
        ],
        "test_addition_unknown_points": [
            {"P": P, "Q": Q, "expected": add(Q, P, base_field)},
            {"P": P, "Q": point_at_infinity, "expected": P},
            {"P": point_at_infinity, "Q": Q, "expected": Q},
            {"P": P, "Q": negate(P), "expected": point_at_infinity},
            {
                "P": P,
                "Q": [base_field(2) * P[0], base_field(2) * -P[1], base_field(2) * P[2]],
                "expected": point_at_infinity,
            },
        ],
        "test_multi_addition": [
            *generate_multi_addition_tests([P, Q, P, Q], base_field),
            *generate_multi_addition_tests([P, Q, P, point_at_infinity], base_field),
            *generate_multi_addition_tests([point_at_infinity, P, Q, Q], base_field),
            *generate_multi_addition_tests([P, negate(P), P, negate(P)], base_field),
        ],
        "test_msm_with_fixed_bases": [
            {
                "scalars": [
                    91480703662782754180582857755469238521183816015595091307545684157518834179962,
                    47070595863165885427430233112660476768577559097282104975413125241877698242896,
                    9224493153332625135218701509907469141303400067447258343326975920405791097566,
                    31206083188178209172482180095895746394525486465923231870455125188479567353247,
                ],
                "bases": [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                "expected": msm(
                    [
                        91480703662782754180582857755469238521183816015595091307545684157518834179962,
                        47070595863165885427430233112660476768577559097282104975413125241877698242896,
                        9224493153332625135218701509907469141303400067447258343326975920405791097566,
                        31206083188178209172482180095895746394525486465923231870455125188479567353247,
                    ],
                    [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                    curve,
                    base_field,
                ),
            },
            {
                "scalars": [
                    0,
                    47070595863165885427430233112660476768577559097282104975413125241877698242896,
                    9224493153332625135218701509907469141303400067447258343326975920405791097566,
                    31206083188178209172482180095895746394525486465923231870455125188479567353247,
                ],
                "bases": [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                "expected": msm(
                    [
                        0,
                        47070595863165885427430233112660476768577559097282104975413125241877698242896,
                        9224493153332625135218701509907469141303400067447258343326975920405791097566,
                        31206083188178209172482180095895746394525486465923231870455125188479567353247,
                    ],
                    [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                    curve,
                    base_field,
                ),
            },
            {
                "scalars": [
                    91480703662782754180582857755469238521183816015595091307545684157518834179962,
                    0,
                    0,
                    31206083188178209172482180095895746394525486465923231870455125188479567353247,
                ],
                "bases": [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                "expected": msm(
                    [
                        91480703662782754180582857755469238521183816015595091307545684157518834179962,
                        0,
                        0,
                        31206083188178209172482180095895746394525486465923231870455125188479567353247,
                    ],
                    [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                    curve,
                    base_field,
                ),
            },
            {
                "scalars": [
                    0,
                    0,
                    0,
                    0,
                ],
                "bases": [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                "expected": msm(
                    [
                        0,
                        0,
                        0,
                        0,
                    ],
                    [P, Q, double(P, curve, base_field), double(Q, curve, base_field)],
                    curve,
                    base_field,
                ),
            },
        ],
    }


def generate_test_cases(test_name):
    configurations = [Secp256k1, Secp256r1]
    # Parse and return config and the test_data for each config
    out = []

    for config in configurations:
        if test_name in config.test_data:
            for test_data in config.test_data[test_name]:
                match test_name:
                    case "test_addition":
                        out.append(
                            (
                                config,
                                test_data["P"],
                                test_data["Q"],
                            )
                        )
                    case "test_doubling":
                        out.append(
                            (
                                config,
                                test_data["P"],
                            )
                        )
                    case "test_multiplication_unrolled":
                        out.append(
                            (config, test_data["P"], test_data["a"], test_data["expected"], test_data["max_multiplier"])
                        )
                    case "test_to_affine":
                        out.append((config, test_data["P"], test_data["expected"]))
                    case "test_addition_unknown_points":
                        out.append((config, test_data["P"], test_data["Q"], test_data["expected"]))
                    case "test_multi_addition":
                        out.append(
                            (config, test_data["points"], test_data["expected"], test_data["n_points_on_altstack"])
                        )
                    case "test_msm_with_fixed_bases":
                        out.append((config, test_data["scalars"], test_data["bases"], test_data["expected"]))
    return out


@pytest.mark.parametrize("additional_elements", [[], [10, 11]])
@pytest.mark.parametrize("negate_p", [True, False])
@pytest.mark.parametrize("negate_q", [True, False])
@pytest.mark.parametrize(
    ("config", "P", "Q"),
    generate_test_cases("test_addition"),
)
def test_addition(config, additional_elements, negate_p, negate_q, P, Q, save_to_json_folder):
    is_with_additiona_elements = additional_elements != []
    match (negate_p, negate_q):
        case (True, True):
            expected = add(negate(P), negate(Q), config.base_field)
        case (True, False):
            expected = add(negate(P), Q, config.base_field)
        case (False, True):
            expected = add(P, negate(Q), config.base_field)
        case (False, False):
            expected = add(P, Q, config.base_field)
    expected = proj_to_list(expected)

    unlock = nums_to_script([config.modulus])
    unlock += nums_to_script(proj_to_list(P))
    unlock += nums_to_script(additional_elements)
    unlock += nums_to_script(proj_to_list(Q))

    lock = config.test_script.point_algebraic_addition(
        take_modulo=True,
        check_constant=True,
        clean_constant=True,
        positive_modulo=True,
        modulus=StackNumber(-1, False),
        P=StackEllipticCurvePointProjective(
            StackFiniteFieldElement(5 + 2 * is_with_additiona_elements, False, 1),
            StackFiniteFieldElement(4 + 2 * is_with_additiona_elements, negate_p, 1),
            StackFiniteFieldElement(3 + 2 * is_with_additiona_elements, False, 1),
        ),
        Q=StackEllipticCurvePointProjective(
            StackFiniteFieldElement(2, False, 1),
            StackFiniteFieldElement(1, negate_q, 1),
            StackFiniteFieldElement(0, False, 1),
        ),
        rolling_options=3,
    )
    for el in [*additional_elements, *expected][::-1]:
        lock += nums_to_script([el])
        lock += Script.parse_string("OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point addition")


@pytest.mark.parametrize("additional_elements", [[], [10, 11]])
@pytest.mark.parametrize("negate_p", [True, False])
@pytest.mark.parametrize(
    ("config", "P"),
    generate_test_cases("test_doubling"),
)
def test_doubling(config, additional_elements, negate_p, P, save_to_json_folder):
    is_with_additiona_elements = additional_elements != []
    expected = (
        double(negate(P), config.curve, config.base_field) if negate_p else double(P, config.curve, config.base_field)
    )
    expected = proj_to_list(expected)

    unlock = nums_to_script([config.modulus])
    unlock += nums_to_script(proj_to_list(P))
    unlock += nums_to_script(additional_elements)
    lock = config.test_script.point_algebraic_doubling(
        take_modulo=True,
        check_constant=True,
        clean_constant=True,
        positive_modulo=True,
        modulus=StackNumber(-1, False),
        P=StackEllipticCurvePointProjective(
            StackFiniteFieldElement(2 + 2 * is_with_additiona_elements, False, 1),
            StackFiniteFieldElement(1 + 2 * is_with_additiona_elements, negate_p, 1),
            StackFiniteFieldElement(0 + 2 * is_with_additiona_elements, False, 1),
        ),
        rolling_option=True,
    )

    for el in [*additional_elements, *expected][::-1]:
        lock += nums_to_script([el])
        lock += Script.parse_string("OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point doubling")


@pytest.mark.parametrize(
    ("config", "P", "a", "expected", "max_multiplier"), generate_test_cases("test_multiplication_unrolled")
)
def test_multiplication_unrolled(config, P, a, expected, max_multiplier, save_to_json_folder):  # noqa: N803
    unlocking_key = EllipticCurveFqProjectiveUnrolledUnlockingKey(P=proj_to_list(P), a=a, max_multiplier=max_multiplier)

    unlock = unlocking_key.to_unlocking_script(config.test_script, load_modulus=True, load_P=True)

    lock = config.test_script.unrolled_multiplication(
        max_multiplier=max_multiplier,
        check_constant=True,
        clean_constant=True,
        positive_modulo=True,
    )
    if expected != config.point_at_infinity:
        for el in proj_to_list(expected)[::-1]:
            lock += nums_to_script([el])
            lock += Script.parse_string("OP_EQUALVERIFY")
    else:
        lock += Script.parse_string("0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY")
    for el in proj_to_list(P)[::-1]:
        lock += nums_to_script([el])
        lock += Script.parse_string("OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "unrolled multiplication")


@pytest.mark.parametrize(("config", "P", "Q", "expected"), generate_test_cases("test_addition_unknown_points"))
def test_addition_unknown_points(config, P, Q, expected, save_to_json_folder):
    unlock = nums_to_script([config.modulus])
    unlock += (
        nums_to_script(proj_to_list(P)) if config.point_at_infinity != P else Script.parse_string("0x00 0x00 0x00")
    )
    unlock += (
        nums_to_script(proj_to_list(Q)) if config.point_at_infinity != Q else Script.parse_string("0x00 0x00 0x00")
    )
    lock = config.test_script.point_addition_with_unknown_points(
        take_modulo=True, check_constant=True, clean_constant=True, positive_modulo=True
    )
    if expected == config.point_at_infinity:
        lock += Script.parse_string("0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY")
    else:
        for el in expected[::-1]:
            lock += nums_to_script(el.to_list())
            lock += Script.parse_string("OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point addition with unknown points")


@pytest.mark.parametrize("additional_elements", [[], [10, 11]])
@pytest.mark.parametrize(
    ("config", "P", "expected"),
    generate_test_cases("test_to_affine"),
)
def test_to_affine(config, additional_elements, P, expected, save_to_json_folder):
    is_with_additiona_elements = additional_elements != []

    unlock = nums_to_script([config.modulus])
    unlock += nums_to_script(P[2].invert().to_list())
    unlock += nums_to_script(proj_to_list(P))
    unlock += nums_to_script(additional_elements)

    lock = config.test_script.to_affine(
        take_modulo=True,
        check_constant=True,
        clean_constant=True,
        positive_modulo=True,
        z_inverse=StackFiniteFieldElement(3 + 2 * is_with_additiona_elements, False, 1),
        P=StackEllipticCurvePointProjective(
            StackFiniteFieldElement(2 + 2 * is_with_additiona_elements, False, 1),
            StackFiniteFieldElement(1 + 2 * is_with_additiona_elements, False, 1),
            StackFiniteFieldElement(0 + 2 * is_with_additiona_elements, False, 1),
        ),
        rolling_options=3,
    )

    for el in [*additional_elements, *expected.to_list()][::-1]:
        lock += nums_to_script([el])
        lock += Script.parse_string("OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "to affine")


@pytest.mark.parametrize(
    ("config", "points", "expected", "n_points_on_altstack"), generate_test_cases("test_multi_addition")
)
def test_multi_addition(config, points, expected, n_points_on_altstack, save_to_json_folder):
    unlock = nums_to_script([config.modulus])

    # Prepare unlocking script
    n_points = len(points)
    n_points_on_stack = n_points - n_points_on_altstack

    for i, point in enumerate(points):
        if point != config.point_at_infinity:
            unlock += nums_to_script(proj_to_list(point))
        else:
            unlock += Script.parse_string("0x00 0x00 0x00")
        if i >= n_points - n_points_on_altstack:
            unlock += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK")

    lock = config.test_script.multi_addition(
        n_points_on_stack=n_points_on_stack,
        n_points_on_altstack=n_points_on_altstack,
        take_modulo=True,
        check_constant=True,
        clean_constant=True,
        positive_modulo=True,
    )
    context = Context(script=unlock + lock)
    if expected != config.point_at_infinity:
        for el in proj_to_list(expected)[::-1]:
            lock += nums_to_script([el])
            lock += Script.parse_string("OP_EQUALVERIFY")
    else:
        lock += Script.parse_string("0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "multi addition")


@pytest.mark.parametrize(("config", "scalars", "bases", "expected"), generate_test_cases("test_msm_with_fixed_bases"))
def test_msm_with_fixed_bases(config, scalars, bases, expected, save_to_json_folder):
    unlocking_key = MsmWithFixedBasesProjectiveUnlockingKey.from_data(
        scalars=scalars, max_multipliers=[config.order] * len(bases)
    )

    unlock = unlocking_key.to_unlocking_script(config.test_script)
    lock = config.test_script.msm_with_fixed_bases(
        bases=[proj_to_list(base) for base in bases],
        max_multipliers=[config.order] * len(bases),
        take_modulo=True,
        check_constant=True,
        clean_constant=True,
        positive_modulo=True,
    )
    if expected != config.point_at_infinity:
        for el in proj_to_list(expected)[::-1]:
            lock += nums_to_script([el])
            lock += Script.parse_string("OP_EQUALVERIFY")
    else:
        lock += Script.parse_string("0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "msm with fixed bases")
