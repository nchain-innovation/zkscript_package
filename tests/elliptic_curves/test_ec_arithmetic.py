from dataclasses import dataclass

import pytest
from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.fields.quadratic_extension import quadratic_extension_from_base_field_and_non_residue
from elliptic_curves.models.curve import Curve
from elliptic_curves.models.ec import elliptic_curve_from_curve
from tx_engine import Context, Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.elliptic_curves.ec_operations_fq2 import EllipticCurveFq2
from src.zkscript.elliptic_curves.ec_operations_fq_unrolled import EllipticCurveFqUnrolled
from src.zkscript.fields.fq2 import Fq2 as Fq2ScriptModel
from src.zkscript.util.utility_scripts import nums_to_script
from tests.elliptic_curves.util import generate_unlock, generate_verify, save_scripts


@dataclass
class Secp256k1:
    modulus = 115792089237316195423570985008687907853269984665640564039457584007908834671663
    order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    Fq_k1 = base_field_from_modulus(q=modulus)
    Fr_k1 = base_field_from_modulus(q=order)
    secp256k1, _ = elliptic_curve_from_curve(curve=Curve(a=Fq_k1(0), b=Fq_k1(7)))
    degree = 1
    point_at_infinity = secp256k1.point_at_infinity()
    generator = secp256k1(
        x=Fq_k1(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798),
        y=Fq_k1(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8),
    )
    test_script = EllipticCurveFq(q=modulus, curve_a=0)
    test_script_unrolled = EllipticCurveFqUnrolled(q=modulus, ec_over_fq=test_script)
    # Define filename for saving scripts
    filename = "secp256k1"
    # Test data
    P = secp256k1(
        x=Fq_k1(41215615274060316946324649613818309412392301453105041246304560830716313169400),
        y=Fq_k1(74117305601093926817905542912257614464261406761524109253393548124815807467650),
    )
    Q = secp256k1(
        x=Fq_k1(75022427023119710175388682918928560109160388746708368835324539025120909485774),
        y=Fq_k1(70716735503538187278140999937647087780607401911659658020223121861184446029572),
    )
    a = 64046112301879843941239178948101222343000413030798872646069227448863068996094
    test_data = {
        "test_addition": [{"P": P, "Q": Q, "expected": P + Q}],
        "test_doubling": [{"P": P, "expected": P + P}],
        "test_addition_unknown_points": [
            # {"P": P, "Q": Q, "expected": P + Q},
            {"P": P, "Q": -P, "expected": point_at_infinity},
            {"P": P, "Q": point_at_infinity, "expected": P},
            {"P": point_at_infinity, "Q": Q, "expected": Q},
        ],
        "test_multiplication_unrolled": [{"P": P, "a": a, "expected": P.multiply(a)}],
    }


@dataclass
class Secp256r1:
    modulus = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
    order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
    Fq_r1 = base_field_from_modulus(q=modulus)
    Fr_r1 = base_field_from_modulus(q=order)
    secp256r1, _ = elliptic_curve_from_curve(
        curve=Curve(
            a=Fq_r1(0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC),
            b=Fq_r1(0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B),
        )
    )
    degree = 1
    point_at_infinity = secp256r1.point_at_infinity()
    generator = secp256r1(
        x=Fq_r1(0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296),
        y=Fq_r1(0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5),
    )
    test_script = EllipticCurveFq(q=modulus, curve_a=0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC)
    test_script_unrolled = EllipticCurveFqUnrolled(q=modulus, ec_over_fq=test_script)
    # Define filename for saving scripts
    filename = "secp256r1"
    # Test data
    P = secp256r1(
        x=Fq_r1(11990862373011617163317646558408705408882310560667899835694339942976011369232),
        y=Fq_r1(80247255150202856195005696069978490751513498800937223995637125987523375481630),
    )
    Q = secp256r1(
        x=Fq_r1(64260480261783363550587538316957846447400713742342025589747159311266528268825),
        y=Fq_r1(68194036500363828464317082173162010818073467174652382578837906057865410662381),
    )
    a = 104614095137500434070196828944928516815982260532830080798264081596642730786155
    test_data = {
        "test_addition": [{"P": P, "Q": Q, "expected": P + Q}],
        "test_doubling": [{"P": P, "expected": P + P}],
        "test_addition_unknown_points": [
            # {"P": P, "Q": Q, "expected": P + Q},
            {"P": P, "Q": -P, "expected": point_at_infinity},
            {"P": P, "Q": point_at_infinity, "expected": P},
            {"P": point_at_infinity, "Q": Q, "expected": Q},
        ],
        "test_multiplication_unrolled": [{"P": P, "a": a, "expected": P.multiply(a)}],
    }


@dataclass
class Secp256k1Extension:
    modulus = Secp256k1.modulus
    order = Secp256k1.order
    Fq_k1 = Secp256k1.Fq_k1
    NON_RESIDUE_K1 = Fq_k1(3)
    Fq2_k1 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq_k1, non_residue=NON_RESIDUE_K1)
    Fr_k1 = Secp256k1.Fr_k1
    secp256k1ext, _ = elliptic_curve_from_curve(curve=Curve(a=Fq2_k1.zero(), b=Fq2_k1(Fq_k1(7), Fq_k1.zero())))
    generator = secp256k1ext(
        x=Fq2_k1(Fq_k1(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798), Fq_k1.zero()),
        y=Fq2_k1(Fq_k1(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8), Fq_k1.zero()),
    )
    degree = 2
    point_at_infinity = secp256k1ext.point_at_infinity()
    test_script = EllipticCurveFq2(
        q=modulus, curve_a=[0, 0], fq2=Fq2ScriptModel(q=modulus, non_residue=NON_RESIDUE_K1.to_list()[0])
    )
    # Define filename for saving scripts
    filename = "secp256k1_extension"
    # Test data
    P = secp256k1ext(
        x=Fq2_k1(Fq_k1(94095614298307368546814548474253270428029709253177010004762002524804913895755), Fq_k1.zero()),
        y=Fq2_k1(Fq_k1(89185879682398848498440952890745529774620859762156036354282049377491887931647), Fq_k1.zero()),
    )
    Q = secp256k1ext(
        x=Fq2_k1(Fq_k1(8990164901158448935493903050084808313444829307709037715141411306530244885211), Fq_k1.zero()),
        y=Fq2_k1(Fq_k1(23965057585496331673584477237659815348801473852880524662243981309175446085731), Fq_k1.zero()),
    )
    test_data = {
        "test_addition": [{"P": P, "Q": Q, "expected": P + Q}],
        "test_doubling": [{"P": P, "expected": P + P}],
        "test_negation": [{"P": P, "expected": -P}, {"P": point_at_infinity, "expected": -point_at_infinity}],
    }


@dataclass
class Secp256r1Extension:
    modulus = Secp256r1.modulus
    order = Secp256r1.order
    Fq_r1 = Secp256r1.Fq_r1
    NON_RESIDUE_R1 = Fq_r1(3)
    Fq2_r1 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq_r1, non_residue=NON_RESIDUE_R1)
    Fr_r1 = Secp256r1.Fr_r1
    secp256r1ext, _ = elliptic_curve_from_curve(
        curve=Curve(
            a=Fq2_r1(Fq_r1(0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC), Fq_r1.zero()),
            b=Fq2_r1(Fq_r1(0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B), Fq_r1.zero()),
        )
    )
    generator = secp256r1ext(
        x=Fq2_r1(Fq_r1(0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296), Fq_r1.zero()),
        y=Fq2_r1(Fq_r1(0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5), Fq_r1.zero()),
    )
    degree = 2
    point_at_infinity = secp256r1ext.point_at_infinity()
    test_script = EllipticCurveFq2(
        q=modulus,
        curve_a=[0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC, 0],
        fq2=Fq2ScriptModel(q=modulus, non_residue=NON_RESIDUE_R1.to_list()[0]),
    )
    # Define filename for saving scripts
    filename = "secp256r1_extension"
    # Test data
    P = secp256r1ext(
        x=Fq2_r1(Fq_r1(76087740444190817290444644797556573089541616229078847927560711689283487831468), Fq_r1.zero()),
        y=Fq2_r1(Fq_r1(32475108468112430759583481824287526908923893331159908098629651711008277175075), Fq_r1.zero()),
    )
    Q = secp256r1ext(
        x=Fq2_r1(Fq_r1(19506571565678743920976889829202594248997307381203809914252094040594564960028), Fq_r1.zero()),
        y=Fq2_r1(Fq_r1(92067975979439830169715993237718936276517713925749869689989196918696315341149), Fq_r1.zero()),
    )
    test_data = {
        "test_addition": [{"P": P, "Q": Q, "expected": P + Q}],
        "test_doubling": [{"P": P, "expected": P + P}],
        "test_negation": [{"P": P, "expected": -P}, {"P": point_at_infinity, "expected": -point_at_infinity}],
    }


def generate_test_cases(test_name):
    configurations = [Secp256k1, Secp256r1, Secp256k1Extension, Secp256r1Extension]
    # Parse and return config and the test_data for each config
    return [
        (config, test_data["P"], test_data["expected"])
        if "P" in test_data and "Q" not in test_data and "a" not in test_data
        else (config, test_data["P"], test_data["Q"], test_data["expected"])
        if "P" in test_data and "Q" in test_data and "a" not in test_data
        else (config, test_data["P"], test_data["a"], test_data["expected"])
        for config in configurations
        if test_name in config.test_data
        for test_data in config.test_data[test_name]
    ]


@pytest.mark.parametrize(("config", "P", "Q", "expected"), generate_test_cases("test_addition"))
def test_addition(config, P, Q, expected, save_to_json_folder):
    lam = P.get_lambda(Q)

    unlock = nums_to_script([config.modulus])
    unlock += nums_to_script(lam.to_list())
    unlock += generate_unlock(P, degree=config.degree)
    unlock += generate_unlock(Q, degree=config.degree)

    lock = config.test_script.point_addition(take_modulo=True, check_constant=True, clean_constant=True)
    lock += generate_verify(expected, degree=config.degree)

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert len(context.get_stack()) == 1
    assert len(context.get_altstack()) == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point addition")


@pytest.mark.parametrize(("config", "P", "expected"), generate_test_cases("test_doubling"))
def test_doubling(config, P, expected, save_to_json_folder):
    lam = P.get_lambda(P)

    unlock = nums_to_script([config.modulus])
    unlock += nums_to_script(lam.to_list())
    unlock += generate_unlock(P, degree=config.degree)

    lock = config.test_script.point_doubling(take_modulo=True, check_constant=True, clean_constant=True)
    lock += generate_verify(expected, degree=config.degree)

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert len(context.get_stack()) == 1
    assert len(context.get_altstack()) == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point doubling")


@pytest.mark.parametrize(("config", "P", "Q", "expected"), generate_test_cases("test_addition_unknown_points"))
def test_addition_unknown_points(config, P, Q, expected, save_to_json_folder):
    unlock = nums_to_script([config.modulus])

    # if config.point_at_infinity not in {P, Q, expected}:
    #     lam = P.get_lambda(Q)
    #     unlock += nums_to_script(lam.to_list())

    unlock += generate_unlock(P, degree=config.degree)
    unlock += generate_unlock(Q, degree=config.degree)

    lock = config.test_script.point_addition_with_unknown_points(
        take_modulo=True, check_constant=True, clean_constant=True
    )
    lock += generate_verify(expected, degree=config.degree)

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert len(context.get_stack()) == 1
    assert len(context.get_altstack()) == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point addition with unknown points")


@pytest.mark.parametrize(("config", "P", "a", "expected"), generate_test_cases("test_multiplication_unrolled"))
def test_multiplication_unrolled(config, P, a, expected, save_to_json_folder):
    exp_a = [int(bin(a)[j]) for j in range(2, len(bin(a)))][::-1]

    unlock = config.test_script_unrolled.unrolled_multiplication_input(
        P=P.to_list(),
        a=a,
        lambdas=[[s.to_list() for s in el] for el in P.get_lambdas(exp_a)],
        max_multiplier=config.order,
        load_modulus=True,
    )

    lock = config.test_script_unrolled.unrolled_multiplication(
        max_multiplier=config.order, modulo_threshold=1, check_constant=True, clean_constant=True
    )
    lock += generate_verify(expected, degree=config.degree) + Script.parse_string("OP_VERIFY")
    lock += generate_verify(P, degree=config.degree)

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert len(context.get_stack()) == 1
    assert len(context.get_altstack()) == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "unrolled multiplication")


@pytest.mark.parametrize(("config", "P", "expected"), generate_test_cases("test_negation"))
def test_negation(config, P, expected, save_to_json_folder):
    unlock = nums_to_script([config.modulus])
    unlock += generate_unlock(P, degree=config.degree)

    lock = config.test_script.point_negation(take_modulo=True, check_constant=True, is_constant_reused=False)
    lock += generate_verify(expected, degree=config.degree)

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert len(context.get_stack()) == 2
    assert len(context.get_altstack()) == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point negation")
