from dataclasses import dataclass

import pytest
from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.fields.quadratic_extension import QuadraticExtension
from elliptic_curves.models.ec import ShortWeierstrassEllipticCurve
from tx_engine import Context, Script

from src.zkscript.elliptic_curves.ec_operations_fq2_projective import EllipticCurveFq2Projective
from src.zkscript.fields.fq2 import Fq2 as Fq2Script
from src.zkscript.script_types.stack_elements import (
    StackEllipticCurvePoint,
    StackEllipticCurvePointProjective,
    StackFiniteFieldElement,
)
from src.zkscript.util.utility_scripts import nums_to_script
from tests.elliptic_curves.util import save_scripts
from tests.elliptic_curves.util_projective_ec import add_fq2, double_fq2, negate_fq2, proj_point_to_script_fq2


@dataclass
class Secp256r1Extension:
    modulus = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
    f_q = PrimeField(modulus)

    non_residue = f_q(3)
    f_q2 = QuadraticExtension(base_field=f_q, non_residue=non_residue)
    curve = ShortWeierstrassEllipticCurve(
        a=f_q2(f_q(0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC), f_q(0)),
        b=f_q2(f_q(0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B), f_q.zero()),
    )

    degree = 2
    point_at_infinity = [f_q2.zero(), f_q2.identity(), f_q2.zero()]

    test_script = EllipticCurveFq2Projective(
        q=modulus,
        curve_a=[0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC, 0],
        curve_b=[0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B, 0],
        fq2=Fq2Script(q=modulus, non_residue=non_residue.to_int()),
    )

    # Define filename for saving scripts
    filename = "secp256k1_extension_projective"
    # Test data
    P = [
        f_q2(
            f_q(0x9D764123F35983906F6D4835B1843F8B842355BD1744B7CB1A28CFE182FB45F3),
            f_q(0xD739D84ADA8F5C667F71179D87A811E3C81C13A373F2F147758E038B0AA4D173),
        ),
        f_q2(
            f_q(0xB76CF9D7E1FB44B9D229A7C1412AC648F1DFDAB223DE92E42E02C7E5057E390F),
            f_q(0x2AC60E3EBC7F1E8EF6DB6D07009F6FAF10C7F3AA71FAEE13FE273DF57C174F9F),
        ),
        f_q2(
            f_q(1),
            f_q(0),
        ),
    ]
    Q = [
        f_q2(
            f_q(0x6C3AC0A83056E2E5DD4C1883D69F9BD64A2ACB655D843F7B7695EFA2392E30F4),
            f_q(0xBAA280A48466BB5BBD73ED70054947C4A929BF2529E20489E99490CFFE1E4EA6),
        ),
        f_q2(
            f_q(0xFEA7280CF96F9012ED154141E753047EEBD3D810469BAADA62CC43CE26B63858),
            f_q(0x9C26432B2554E32601E74658E881AAE4A6285106CE5E943467FE30E7396446EB),
        ),
        f_q2(
            f_q(1),
            f_q(0),
        ),
    ]

    test_data = {
        "test_doubling": [
            {"P": P},
            {"P": Q},
            {"P": double_fq2(P, curve, f_q, f_q2)},
        ],
        "test_mixed_addition": [
            {"P": P, "Q": Q[:2]},
            {"P": Q, "Q": P[:2]},
            {"P": double_fq2(Q, curve, f_q, f_q2), "Q": Q[:2]},
            {"P": double_fq2(P, curve, f_q, f_q2), "Q": P[:2]},
        ],
    }


@dataclass
class Secp256k1Extension:
    modulus = 115792089237316195423570985008687907853269984665640564039457584007908834671663
    f_q = PrimeField(modulus)

    non_residue = f_q(3)
    f_q2 = QuadraticExtension(base_field=f_q, non_residue=non_residue)
    curve = ShortWeierstrassEllipticCurve(a=f_q2.zero(), b=f_q2(f_q(7), f_q.zero()))

    degree = 2
    point_at_infinity = [f_q2.zero(), f_q2.identity(), f_q2.zero()]

    test_script = EllipticCurveFq2Projective(
        q=modulus, curve_a=[0, 0], curve_b=[7, 0], fq2=Fq2Script(q=modulus, non_residue=non_residue.to_int())
    )

    # Define filename for saving scripts
    filename = "secp256k1_extension_projective"
    # Test data
    P = [
        f_q2(
            f_q(0xB981DA1FE0F34CA56B4C7A15F7A33946DCD3E60C7A12727068D8ED449D15F70E),
            f_q(0xFA2C34DA64A420D491AD1743D09445FAC971C28B03C203A7AF2768619391463C),
        ),
        f_q2(
            f_q(0xDAADB913FAFB7EEAC301D7F430AA98FC1EAA5CAED1FE66D3399074CCFAA78B32),
            f_q(0x93620E1F5AE7B6F2B46ACA13F339BBAAFDBBA268F6A61E7571B5EA5F25C662A7),
        ),
        f_q2(
            f_q(1),
            f_q(0),
        ),
    ]
    Q = [
        f_q2(
            f_q(0xFBD173BDFFC6C303177D831811800DAE3A7EDC335F420BE0FE3FC643E2019DDF),
            f_q(0xB2CD8B5AF66F524BBC351B2A3EA4687408644A9871C6C00973C47F2CEFD03FA9),
        ),
        f_q2(
            f_q(0xC61512666F8EC06B462C3002045D59525C63BCD0BFC4E2BB83BA19E1111CD2DE),
            f_q(0xC52748235BFD3380D1620DE3B2CD038BDDEBB98064902EA0303214E7B273C7D5),
        ),
        f_q2(
            f_q(1),
            f_q(0),
        ),
    ]

    test_data = {
        "test_doubling": [
            {"P": P},
            {"P": Q},
            {"P": double_fq2(P, curve, f_q, f_q2)},
        ],
        "test_mixed_addition": [
            {"P": P, "Q": Q[:2]},
            {"P": Q, "Q": P[:2]},
            {"P": double_fq2(Q, curve, f_q, f_q2), "Q": Q[:2]},
            {"P": double_fq2(P, curve, f_q, f_q2), "Q": P[:2]},
        ],
    }


@dataclass
class DummyCurve1:
    modulus = 5
    f_q = PrimeField(modulus)

    non_residue = f_q(2)
    f_q2 = QuadraticExtension(base_field=f_q, non_residue=non_residue)
    curve = ShortWeierstrassEllipticCurve(a=f_q2(f_q(4), f_q(2)), b=f_q2(f_q(1), f_q(3)))

    degree = 2
    point_at_infinity = [f_q2.zero(), f_q2.identity(), f_q2.zero()]

    test_script = EllipticCurveFq2Projective(
        q=modulus, curve_a=[4, 2], curve_b=[1, 3], fq2=Fq2Script(q=modulus, non_residue=non_residue.to_int())
    )

    # Define filename for saving scripts
    filename = "dummy_curve"
    # Test data
    P = [f_q2(f_q(3), f_q(4)), f_q2(f_q(1), f_q(3)), f_q2(f_q(1), f_q(0))]
    Q = [f_q2(f_q(4), f_q(1)), f_q2(f_q(2), f_q(0)), f_q2(f_q(1), f_q(0))]

    test_data = {
        "test_doubling": [
            {"P": P},
            {"P": Q},
            {"P": double_fq2(P, curve, f_q, f_q2)},
        ],
        "test_mixed_addition": [
            {"P": P, "Q": Q[:2]},
            {"P": Q, "Q": P[:2]},
            {"P": double_fq2(Q, curve, f_q, f_q2), "Q": Q[:2]},
            {"P": double_fq2(P, curve, f_q, f_q2), "Q": P[:2]},
        ],
    }


@dataclass
class DummyCurve2:
    modulus = 5
    f_q = PrimeField(modulus)

    non_residue = f_q(2)
    f_q2 = QuadraticExtension(base_field=f_q, non_residue=non_residue)
    curve = ShortWeierstrassEllipticCurve(a=f_q2(f_q(0), f_q(0)), b=f_q2(f_q(3), f_q(4)))
    degree = 2
    point_at_infinity = [f_q2.zero(), f_q2.identity(), f_q2.zero()]

    b = f_q2(f_q(3), f_q(4))

    test_script = EllipticCurveFq2Projective(
        q=modulus, curve_a=[0, 0], curve_b=[3, 4], fq2=Fq2Script(q=modulus, non_residue=non_residue.to_int())
    )

    # Define filename for saving scripts
    filename = "dummy_curve"
    # Test data
    P = [f_q2(f_q(4), f_q(4)), f_q2(f_q(3), f_q(4)), f_q2(f_q(1), f_q(0))]
    Q = [f_q2(f_q(3), f_q(1)), f_q2(f_q(1), f_q(4)), f_q2(f_q(1), f_q(0))]

    test_data = {
        "test_doubling": [
            {"P": P},
            {"P": Q},
            {"P": double_fq2(P, curve, f_q, f_q2)},
        ],
        "test_mixed_addition": [
            {"P": P, "Q": Q[:2]},
            {"P": Q, "Q": P[:2]},
            {"P": double_fq2(Q, curve, f_q, f_q2), "Q": Q[:2]},
            {"P": double_fq2(P, curve, f_q, f_q2), "Q": P[:2]},
        ],
    }


def generate_test_cases(test_name):
    configurations = [Secp256k1Extension, DummyCurve1, DummyCurve2, Secp256r1Extension]
    # Parse and return config and the test_data for each config
    out = []

    for config in configurations:
        if test_name in config.test_data:
            for test_data in config.test_data[test_name]:
                match test_name:
                    case "test_mixed_addition":
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
    return out


@pytest.mark.parametrize("additional_elements", [[], [1], [1, 2]])
@pytest.mark.parametrize("negate_p", [False, True])
@pytest.mark.parametrize("rolling_option", [True, False])
@pytest.mark.parametrize(
    ("config", "P"),
    generate_test_cases("test_doubling"),
)
def test_doubling(config, additional_elements, negate_p, P, rolling_option, save_to_json_folder):
    nums_of_additional_elements = len(additional_elements)
    expected = (
        double_fq2(negate_fq2(P), config.curve, config.f_q, config.f_q2)
        if negate_p
        else double_fq2(P, config.curve, config.f_q, config.f_q2)
    )

    script_P = proj_point_to_script_fq2(P)
    script_expected = proj_point_to_script_fq2(expected)
    unlock = nums_to_script([config.modulus])
    unlock += nums_to_script(script_P)
    unlock += nums_to_script(additional_elements)
    lock = config.test_script.point_algebraic_doubling(
        take_modulo=True,
        check_constant=True,
        clean_constant=True,
        positive_modulo=True,
        P=StackEllipticCurvePointProjective(
            StackFiniteFieldElement(5 + nums_of_additional_elements, False, 2),
            StackFiniteFieldElement(3 + nums_of_additional_elements, negate_p, 2),
            StackFiniteFieldElement(1 + nums_of_additional_elements, False, 2),
        ),
        rolling_option=rolling_option,
    )

    remaining_elements = (
        [*additional_elements, *script_expected]
        if rolling_option
        else [*script_P, *additional_elements, *script_expected]
    )
    for el in remaining_elements[::-1]:
        lock += nums_to_script([el])
        lock += Script.parse_string("OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point doubling")


@pytest.mark.parametrize("additional_elements", [[], [1], [1, 2]])
@pytest.mark.parametrize("negate_p", [False, True])
@pytest.mark.parametrize("negate_q", [False, True])
@pytest.mark.parametrize("rolling_option", [True, False])
@pytest.mark.parametrize(
    ("config", "P", "Q"),
    generate_test_cases("test_mixed_addition"),
)
def test_mixed_addition(config, additional_elements, negate_p, negate_q, P, Q, rolling_option, save_to_json_folder):
    nums_of_additional_elements = len(additional_elements)

    Q_proj = [Q[0], Q[1], config.f_q2(config.f_q(1), config.f_q(0))]

    expected = add_fq2(
        P if not negate_p else negate_fq2(P),
        Q_proj if not negate_q else negate_fq2(Q_proj),
    )

    script_P = proj_point_to_script_fq2(P)
    script_Q = proj_point_to_script_fq2(Q)
    script_expected = proj_point_to_script_fq2(expected)

    unlock = nums_to_script([config.modulus])
    unlock += nums_to_script(script_Q)
    unlock += nums_to_script(script_P)
    unlock += nums_to_script(additional_elements)

    lock = config.test_script.point_algebraic_mixed_addition(
        take_modulo=True,
        check_constant=True,
        clean_constant=True,
        positive_modulo=True,
        P=StackEllipticCurvePointProjective(
            StackFiniteFieldElement(5 + nums_of_additional_elements, False, 2),
            StackFiniteFieldElement(3 + nums_of_additional_elements, negate_p, 2),
            StackFiniteFieldElement(1 + nums_of_additional_elements, False, 2),
        ),
        Q=StackEllipticCurvePoint(
            StackFiniteFieldElement(9 + nums_of_additional_elements, False, 2),
            StackFiniteFieldElement(7 + nums_of_additional_elements, negate_q, 2),
        ),
        rolling_option=rolling_option,
    )

    remaining_elements = (
        [*additional_elements, *script_expected]
        if rolling_option
        else [*script_Q, *script_P, *additional_elements, *script_expected]
    )

    for el in remaining_elements[::-1]:
        lock += nums_to_script([el])
        lock += Script.parse_string("OP_EQUALVERIFY")
    lock += Script.parse_string("OP_1")

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point mixed addition")
