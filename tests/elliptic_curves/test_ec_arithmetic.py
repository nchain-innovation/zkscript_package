from dataclasses import dataclass

import pytest
from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.fields.quadratic_extension import QuadraticExtension
from elliptic_curves.models.ec import ShortWeierstrassEllipticCurve
from elliptic_curves.util.zkscript import (
    multi_addition_gradients,
    multi_scalar_multiplication_with_fixed_bases_gradients,
    unrolled_multiplication_gradients,
)
from tx_engine import Context, Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.elliptic_curves.ec_operations_fq2 import EllipticCurveFq2
from src.zkscript.fields.fq2 import Fq2 as Fq2Script
from src.zkscript.types.unlocking_keys.msm_with_fixed_bases import MsmWithFixedBasesUnlockingKey
from src.zkscript.types.unlocking_keys.unrolled_ec_multiplication import EllipticCurveFqUnrolledUnlockingKey
from src.zkscript.util.utility_scripts import nums_to_script
from tests.elliptic_curves.util import (
    generate_test,
    generate_test_data,
    generate_unlock,
    generate_verify_point,
    modify_verify_modulo_check,
    save_scripts,
)


@dataclass
class Secp256k1:
    modulus = 115792089237316195423570985008687907853269984665640564039457584007908834671663
    order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    Fq_k1 = PrimeField(modulus)
    Fr_k1 = PrimeField(order)
    secp256k1 = ShortWeierstrassEllipticCurve(a=Fq_k1(0), b=Fq_k1(7))
    degree = 1
    point_at_infinity = secp256k1.infinity()
    generator = secp256k1(
        x=Fq_k1(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798),
        y=Fq_k1(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8),
        infinity=False,
    )
    test_script = EllipticCurveFq(q=modulus, curve_a=0)
    # All possible combinations: ± P ± Q are tested. Refer to ./util.py
    positions_addition = [
        {"modulus": 5, "gradient": 4, "P": 3, "Q": 1},
        {"modulus": 8, "gradient": 6, "P": 3, "Q": 1},
        {"modulus": 11, "gradient": 9, "P": 5, "Q": 1},
        {"modulus": 20, "gradient": 15, "P": 10, "Q": 6},
        {"modulus": 25, "gradient": 20, "P": 14, "Q": 5},
    ]
    # All possible combinations: ± 2P are tested. Refer to ./util.py
    positions_doubling = [
        {"modulus": 3, "gradient": 2, "P": 1},
        {"modulus": 8, "gradient": 6, "P": 3},
        {"modulus": 11, "gradient": 9, "P": 5},
        {"modulus": 20, "gradient": 15, "P": 10},
        {"modulus": 25, "gradient": 20, "P": 14},
    ]
    # Define filename for saving scripts
    filename = "secp256k1"
    # Test data
    P = secp256k1(
        x=Fq_k1(41215615274060316946324649613818309412392301453105041246304560830716313169400),
        y=Fq_k1(74117305601093926817905542912257614464261406761524109253393548124815807467650),
        infinity=False,
    )
    Q = secp256k1(
        x=Fq_k1(75022427023119710175388682918928560109160388746708368835324539025120909485774),
        y=Fq_k1(70716735503538187278140999937647087780607401911659658020223121861184446029572),
        infinity=False,
    )
    a = 64046112301879843941239178948101222343000413030798872646069227448863068996094
    test_data = {
        "test_addition": [
            # Test standard configuration
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 5, "gradient": 4, "P": 3, "Q": 1},
                {"P": False, "Q": False},
                {"gradient": False, "P": False, "Q": False},
            ),
            # Test signs
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 5, "gradient": 4, "P": 3, "Q": 1},
                {"P": True, "Q": True},
                {"gradient": False, "P": False, "Q": False},
            ),
            # Test random positions
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 25, "gradient": 20, "P": 14, "Q": 5},
                {"P": False, "Q": False},
                {"gradient": False, "P": False, "Q": False},
            ),
        ],
        "test_doubling": [
            # Test standard configuration
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 3, "gradient": 2, "P": 1},
                {"P": False},
                {"gradient": False, "P": False},
            ),
            # Test signs
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 3, "gradient": 2, "P": 1},
                {"P": True},
                {"gradient": False, "P": False},
            ),
            # Test random positions
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 25, "gradient": 20, "P": 14},
                {"P": False},
                {"gradient": False, "P": False},
            ),
        ],
        "test_addition_slow": generate_test_data(modulus, P, Q, positions_addition),
        "test_doubling_slow": generate_test_data(modulus, P, P, positions_doubling),
        "test_addition_unknown_points": [
            {"P": P, "Q": Q, "expected": P + Q},
            {"P": P, "Q": -P, "expected": point_at_infinity},
            {"P": P, "Q": point_at_infinity, "expected": P},
            {"P": point_at_infinity, "Q": Q, "expected": Q},
        ],
        "test_multiplication_unrolled": [
            {"P": P, "a": a, "expected": P.multiply(a), "max_multiplier": order},
            {"P": P, "a": 0, "expected": P.multiply(0), "max_multiplier": order},
            {"P": P, "a": order // 4, "expected": P.multiply(order // 4), "max_multiplier": order // 2},
        ],
        "test_multi_addition": [
            {"points": [P, Q, P, Q], "expected": P + Q + P + Q},
            {"points": [P, Q, point_at_infinity], "expected": P + Q},
            {"points": [point_at_infinity, P, Q], "expected": P + Q},
            {"points": [P, -P, P, -P], "expected": point_at_infinity},
        ],
        "test_multi_scalar_multiplication_with_fixed_bases": [
            {"scalars": [1, 1, 1, 1], "bases": [P, Q, P, Q], "expected": P + Q + P + Q},
            {"scalars": [1, 0, 1, 1], "bases": [P, Q, P, Q], "expected": P + P + Q},
            {"scalars": [1, 2, 2, 1], "bases": [P, Q, P, Q], "expected": P.multiply(3) + Q.multiply(3)},
            {"scalars": [0, 0, 0, 0], "bases": [P, Q, P, Q], "expected": point_at_infinity},
            {"scalars": [2, 3, 4, 5], "bases": [P, (Q + P), P, Q], "expected": P.multiply(9) + Q.multiply(8)},
        ],
    }


@dataclass
class Secp256r1:
    modulus = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
    order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
    Fq_r1 = PrimeField(modulus)
    Fr_r1 = PrimeField(order)
    secp256r1 = ShortWeierstrassEllipticCurve(
        a=Fq_r1(0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC),
        b=Fq_r1(0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B),
    )
    degree = 1
    point_at_infinity = secp256r1.infinity()
    generator = secp256r1(
        x=Fq_r1(0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296),
        y=Fq_r1(0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5),
        infinity=False,
    )
    test_script = EllipticCurveFq(q=modulus, curve_a=0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC)
    # All possible combinations: ± P ± Q are tested. Refer to ./util.py
    positions_addition = [
        {"modulus": 5, "gradient": 4, "P": 3, "Q": 1},
        {"modulus": 8, "gradient": 6, "P": 3, "Q": 1},
        {"modulus": 11, "gradient": 9, "P": 5, "Q": 1},
        {"modulus": 20, "gradient": 15, "P": 10, "Q": 6},
        {"modulus": 25, "gradient": 20, "P": 14, "Q": 5},
    ]
    # All possible combinations: ± 2P are tested. Refer to ./util.py
    positions_doubling = [
        {"modulus": 3, "gradient": 2, "P": 1},
        {"modulus": 8, "gradient": 6, "P": 3},
        {"modulus": 11, "gradient": 9, "P": 5},
        {"modulus": 20, "gradient": 15, "P": 10},
        {"modulus": 25, "gradient": 20, "P": 14},
    ]
    # Define filename for saving scripts
    filename = "secp256r1"
    # Test data
    P = secp256r1(
        x=Fq_r1(11990862373011617163317646558408705408882310560667899835694339942976011369232),
        y=Fq_r1(80247255150202856195005696069978490751513498800937223995637125987523375481630),
        infinity=False,
    )
    Q = secp256r1(
        x=Fq_r1(64260480261783363550587538316957846447400713742342025589747159311266528268825),
        y=Fq_r1(68194036500363828464317082173162010818073467174652382578837906057865410662381),
        infinity=False,
    )
    a = 104614095137500434070196828944928516815982260532830080798264081596642730786155
    test_data = {
        "test_addition": [
            # Test standard configuration
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 5, "gradient": 4, "P": 3, "Q": 1},
                {"P": False, "Q": False},
                {"gradient": False, "P": False, "Q": False},
            ),
            # Test signs
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 5, "gradient": 4, "P": 3, "Q": 1},
                {"P": True, "Q": True},
                {"gradient": False, "P": False, "Q": False},
            ),
            # Test random positions
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 25, "gradient": 20, "P": 14, "Q": 5},
                {"P": False, "Q": False},
                {"gradient": False, "P": False, "Q": False},
            ),
        ],
        "test_doubling": [
            # Test standard configuration
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 3, "gradient": 2, "P": 1},
                {"P": False},
                {"gradient": False, "P": False},
            ),
            # Test signs
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 3, "gradient": 2, "P": 1},
                {"P": True},
                {"gradient": False, "P": False},
            ),
            # Test random positions
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 25, "gradient": 20, "P": 14},
                {"P": False},
                {"gradient": False, "P": False},
            ),
        ],
        "test_addition_slow": generate_test_data(modulus, P, Q, positions_addition),
        "test_doubling_slow": generate_test_data(modulus, P, P, positions_doubling),
        "test_addition_unknown_points": [
            # {"P": P, "Q": Q, "expected": P + Q},
            {"P": P, "Q": -P, "expected": point_at_infinity},
            {"P": P, "Q": point_at_infinity, "expected": P},
            {"P": point_at_infinity, "Q": Q, "expected": Q},
        ],
        "test_multiplication_unrolled": [
            {"P": P, "a": a, "expected": P.multiply(a), "max_multiplier": order},
            {"P": P, "a": 0, "expected": P.multiply(0), "max_multiplier": order},
            {"P": P, "a": order // 4, "expected": P.multiply(order // 4), "max_multiplier": order // 2},
        ],
        "test_multi_addition": [
            {"points": [P, Q, P, Q], "expected": P + Q + P + Q},
            {"points": [P, Q, secp256r1.infinity()], "expected": P + Q},
            {"points": [secp256r1.infinity(), P, Q], "expected": P + Q},
            {"points": [P, -P, P, -P], "expected": secp256r1.infinity()},
        ],
        "test_multi_scalar_multiplication_with_fixed_bases": [
            {"scalars": [1, 1, 1, 1], "bases": [P, Q, P, Q], "expected": P + Q + P + Q},
            {"scalars": [1, 0, 1, 1], "bases": [P, Q, P, Q], "expected": P + P + Q},
            {"scalars": [1, 2, 2, 1], "bases": [P, Q, P, Q], "expected": P.multiply(3) + Q.multiply(3)},
            {"scalars": [0, 0, 0, 0], "bases": [P, Q, P, Q], "expected": point_at_infinity},
            {"scalars": [2, 3, 4, 5], "bases": [P, (Q + P), P, Q], "expected": P.multiply(9) + Q.multiply(8)},
        ],
    }


@dataclass
class Secp256k1Extension:
    modulus = Secp256k1.modulus
    order = Secp256k1.order
    Fq_k1 = Secp256k1.Fq_k1
    NON_RESIDUE_K1 = Fq_k1(3)
    Fq2_k1 = QuadraticExtension(base_field=Fq_k1, non_residue=NON_RESIDUE_K1)
    Fr_k1 = Secp256k1.Fr_k1
    secp256k1ext = ShortWeierstrassEllipticCurve(a=Fq2_k1.zero(), b=Fq2_k1(Fq_k1(7), Fq_k1.zero()))
    generator = secp256k1ext(
        x=Fq2_k1(Fq_k1(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798), Fq_k1.zero()),
        y=Fq2_k1(Fq_k1(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8), Fq_k1.zero()),
        infinity=False,
    )
    degree = 2
    point_at_infinity = secp256k1ext.infinity()
    test_script = EllipticCurveFq2(
        q=modulus, curve_a=[0, 0], fq2=Fq2Script(q=modulus, non_residue=NON_RESIDUE_K1.to_int())
    )
    # All possible combinations: ± P ± Q are tested. Refer to ./util.py
    positions_addition = [
        {"modulus": 10, "gradient": 9, "P": 7, "Q": 3},
        {"modulus": 12, "gradient": 11, "P": 7, "Q": 3},
        {"modulus": 18, "gradient": 13, "P": 9, "Q": 3},
        {"modulus": 20, "gradient": 15, "P": 10, "Q": 6},
        {"modulus": 25, "gradient": 20, "P": 14, "Q": 5},
    ]
    # All possible combinations: ± 2P are tested. Refer to ./util.py
    positions_doubling = [
        {"modulus": 6, "gradient": 5, "P": 3},
        {"modulus": 12, "gradient": 11, "P": 7},
        {"modulus": 18, "gradient": 13, "P": 9},
        {"modulus": 20, "gradient": 15, "P": 10},
        {"modulus": 25, "gradient": 20, "P": 14},
    ]
    # Define filename for saving scripts
    filename = "secp256k1_extension"
    # Test data
    P = secp256k1ext(
        x=Fq2_k1(
            Fq_k1(0xB981DA1FE0F34CA56B4C7A15F7A33946DCD3E60C7A12727068D8ED449D15F70E),
            Fq_k1(0xFA2C34DA64A420D491AD1743D09445FAC971C28B03C203A7AF2768619391463C),
        ),
        y=Fq2_k1(
            Fq_k1(0xDAADB913FAFB7EEAC301D7F430AA98FC1EAA5CAED1FE66D3399074CCFAA78B32),
            Fq_k1(0x93620E1F5AE7B6F2B46ACA13F339BBAAFDBBA268F6A61E7571B5EA5F25C662A7),
        ),
        infinity=False,
    )
    Q = secp256k1ext(
        x=Fq2_k1(
            Fq_k1(0xFBD173BDFFC6C303177D831811800DAE3A7EDC335F420BE0FE3FC643E2019DDF),
            Fq_k1(0xB2CD8B5AF66F524BBC351B2A3EA4687408644A9871C6C00973C47F2CEFD03FA9),
        ),
        y=Fq2_k1(
            Fq_k1(0xC61512666F8EC06B462C3002045D59525C63BCD0BFC4E2BB83BA19E1111CD2DE),
            Fq_k1(0xC52748235BFD3380D1620DE3B2CD038BDDEBB98064902EA0303214E7B273C7D5),
        ),
        infinity=False,
    )
    test_data = {
        "test_addition": [
            # Test standard configuration
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 10, "gradient": 9, "P": 7, "Q": 3},
                {"P": False, "Q": False},
                {"gradient": False, "P": False, "Q": False},
            ),
            # Test signs
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 10, "gradient": 9, "P": 7, "Q": 3},
                {"P": True, "Q": True},
                {"gradient": False, "P": False, "Q": False},
            ),
            # Test random positions
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 25, "gradient": 20, "P": 14, "Q": 5},
                {"P": False, "Q": False},
                {"gradient": False, "P": False, "Q": False},
            ),
        ],
        "test_doubling": [
            # Test standard configuration
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 6, "gradient": 5, "P": 3},
                {"P": False},
                {"gradient": False, "P": False},
            ),
            # Test signs
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 6, "gradient": 5, "P": 3},
                {"P": True},
                {"gradient": False, "P": False},
            ),
            # Test random positions
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 25, "gradient": 20, "P": 14},
                {"P": False},
                {"gradient": False, "P": False},
            ),
        ],
        "test_addition_slow": generate_test_data(modulus, P, Q, positions_addition),
        "test_doubling_slow": generate_test_data(modulus, P, P, positions_doubling),
    }


@dataclass
class Secp256r1Extension:
    modulus = Secp256r1.modulus
    order = Secp256r1.order
    Fq_r1 = Secp256r1.Fq_r1
    NON_RESIDUE_R1 = Fq_r1(3)
    Fq2_r1 = QuadraticExtension(base_field=Fq_r1, non_residue=NON_RESIDUE_R1)
    Fr_r1 = Secp256r1.Fr_r1
    secp256r1ext = ShortWeierstrassEllipticCurve(
        a=Fq2_r1(Fq_r1(0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC), Fq_r1.zero()),
        b=Fq2_r1(Fq_r1(0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B), Fq_r1.zero()),
    )
    generator = secp256r1ext(
        x=Fq2_r1(Fq_r1(0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296), Fq_r1.zero()),
        y=Fq2_r1(Fq_r1(0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5), Fq_r1.zero()),
        infinity=False,
    )
    degree = 2
    point_at_infinity = secp256r1ext.infinity()
    test_script = EllipticCurveFq2(
        q=modulus,
        curve_a=[0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC, 0],
        fq2=Fq2Script(q=modulus, non_residue=NON_RESIDUE_R1.to_int()),
    )
    # All possible combinations: ± P ± Q are tested. Refer to ./util.py
    positions_addition = [
        {"modulus": 10, "gradient": 9, "P": 7, "Q": 3},
        {"modulus": 12, "gradient": 11, "P": 7, "Q": 3},
        {"modulus": 18, "gradient": 13, "P": 9, "Q": 3},
        {"modulus": 20, "gradient": 15, "P": 10, "Q": 6},
        {"modulus": 25, "gradient": 20, "P": 14, "Q": 5},
    ]
    # All possible combinations: ± 2P are tested. Refer to ./util.py
    positions_doubling = [
        {"modulus": 6, "gradient": 5, "P": 3},
        {"modulus": 12, "gradient": 11, "P": 7},
        {"modulus": 18, "gradient": 13, "P": 9},
        {"modulus": 20, "gradient": 15, "P": 10},
        {"modulus": 25, "gradient": 20, "P": 14},
    ]
    # Define filename for saving scripts
    filename = "secp256r1_extension"
    # Test data
    P = secp256r1ext(
        x=Fq2_r1(
            Fq_r1(0x9D764123F35983906F6D4835B1843F8B842355BD1744B7CB1A28CFE182FB45F3),
            Fq_r1(0xD739D84ADA8F5C667F71179D87A811E3C81C13A373F2F147758E038B0AA4D173),
        ),
        y=Fq2_r1(
            Fq_r1(0xB76CF9D7E1FB44B9D229A7C1412AC648F1DFDAB223DE92E42E02C7E5057E390F),
            Fq_r1(0x2AC60E3EBC7F1E8EF6DB6D07009F6FAF10C7F3AA71FAEE13FE273DF57C174F9F),
        ),
        infinity=False,
    )
    Q = secp256r1ext(
        x=Fq2_r1(
            Fq_r1(0x6C3AC0A83056E2E5DD4C1883D69F9BD64A2ACB655D843F7B7695EFA2392E30F4),
            Fq_r1(0xBAA280A48466BB5BBD73ED70054947C4A929BF2529E20489E99490CFFE1E4EA6),
        ),
        y=Fq2_r1(
            Fq_r1(0xFEA7280CF96F9012ED154141E753047EEBD3D810469BAADA62CC43CE26B63858),
            Fq_r1(0x9C26432B2554E32601E74658E881AAE4A6285106CE5E943467FE30E7396446EB),
        ),
        infinity=False,
    )
    test_data = {
        "test_addition": [
            # Test standard configuration
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 10, "gradient": 9, "P": 7, "Q": 3},
                {"P": False, "Q": False},
                {"gradient": False, "P": False, "Q": False},
            ),
            # Test signs
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 10, "gradient": 9, "P": 7, "Q": 3},
                {"P": True, "Q": True},
                {"gradient": False, "P": False, "Q": False},
            ),
            # Test random positions
            generate_test(
                modulus,
                P,
                Q,
                {"modulus": 25, "gradient": 20, "P": 14, "Q": 5},
                {"P": False, "Q": False},
                {"gradient": False, "P": False, "Q": False},
            ),
        ],
        "test_doubling": [
            # Test standard configuration
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 6, "gradient": 5, "P": 3},
                {"P": False},
                {"gradient": False, "P": False},
            ),
            # Test signs
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 6, "gradient": 5, "P": 3},
                {"P": True},
                {"gradient": False, "P": False},
            ),
            # Test random positions
            generate_test(
                modulus,
                P,
                P,
                {"modulus": 25, "gradient": 20, "P": 14},
                {"P": False},
                {"gradient": False, "P": False},
            ),
        ],
        "test_addition_slow": generate_test_data(modulus, P, Q, positions_addition),
        "test_doubling_slow": generate_test_data(modulus, P, P, positions_doubling),
    }


def generate_test_cases(test_name):
    configurations = [Secp256k1, Secp256r1, Secp256k1Extension, Secp256r1Extension]
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
                                test_data["unlocking_script"],
                                test_data["expected"],
                                test_data["stack_elements"],
                                test_data["rolling_options"],
                            )
                        )
                    case "test_doubling":
                        out.append(
                            (
                                config,
                                test_data["unlocking_script"],
                                test_data["expected"],
                                test_data["stack_elements"],
                                test_data["rolling_options"],
                            )
                        )
                    case "test_addition_slow":
                        out.append(
                            (
                                config,
                                test_data["unlocking_script"],
                                test_data["expected"],
                                test_data["stack_elements"],
                                test_data["rolling_options"],
                            )
                        )
                    case "test_doubling_slow":
                        out.append(
                            (
                                config,
                                test_data["unlocking_script"],
                                test_data["expected"],
                                test_data["stack_elements"],
                                test_data["rolling_options"],
                            )
                        )
                    case "test_addition_unknown_points":
                        out.append((config, test_data["P"], test_data["Q"], test_data["expected"]))
                    case "test_multiplication_unrolled":
                        out.append(
                            (config, test_data["P"], test_data["a"], test_data["expected"], test_data["max_multiplier"])
                        )
                    case "test_multi_addition":
                        out.append((config, test_data["points"], test_data["expected"]))
                    case "test_multi_scalar_multiplication_with_fixed_bases":
                        out.append((config, test_data["scalars"], test_data["bases"], test_data["expected"]))
    return out


@pytest.mark.parametrize("verify_gradient", [True, False])
@pytest.mark.parametrize(
    ("config", "unlocking_script", "expected", "stack_elements", "rolling_options"),
    generate_test_cases("test_addition"),
)
def test_addition(
    config, unlocking_script, expected, stack_elements, rolling_options, verify_gradient, save_to_json_folder
):
    unlock = unlocking_script

    clean_constant = verify_gradient

    lock = config.test_script.point_algebraic_addition(
        take_modulo=True,
        check_constant=True,
        clean_constant=clean_constant,
        verify_gradient=verify_gradient,
        gradient=stack_elements["gradient"],
        P=stack_elements["P"],
        Q=stack_elements["Q"],
        rolling_options=rolling_options,
    )

    lock += (
        expected if verify_gradient else modify_verify_modulo_check(expected) + Script.parse_string("OP_SWAP OP_DROP")
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point addition")


@pytest.mark.parametrize("verify_gradient", [True, False])
@pytest.mark.parametrize(
    ("config", "unlocking_script", "expected", "stack_elements", "rolling_options"),
    generate_test_cases("test_doubling"),
)
def test_doubling(
    config, unlocking_script, expected, stack_elements, rolling_options, verify_gradient, save_to_json_folder
):
    unlock = unlocking_script
    clean_constant = verify_gradient

    lock = config.test_script.point_algebraic_doubling(
        take_modulo=True,
        check_constant=True,
        clean_constant=clean_constant,
        verify_gradient=verify_gradient,
        gradient=stack_elements["gradient"],
        P=stack_elements["P"],
        rolling_options=rolling_options,
    )

    lock += (
        expected if verify_gradient else modify_verify_modulo_check(expected) + Script.parse_string("OP_SWAP OP_DROP")
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point doubling")


@pytest.mark.slow
@pytest.mark.parametrize("verify_gradient", [True, False])
@pytest.mark.parametrize(
    ("config", "unlocking_script", "expected", "stack_elements", "rolling_options"),
    generate_test_cases("test_addition_slow"),
)
def test_addition_slow(
    config, unlocking_script, expected, stack_elements, rolling_options, verify_gradient, save_to_json_folder
):
    unlock = unlocking_script
    clean_constant = verify_gradient

    lock = config.test_script.point_algebraic_addition(
        take_modulo=True,
        check_constant=True,
        clean_constant=clean_constant,
        verify_gradient=verify_gradient,
        gradient=stack_elements["gradient"],
        P=stack_elements["P"],
        Q=stack_elements["Q"],
        rolling_options=rolling_options,
    )

    lock += (
        expected if verify_gradient else modify_verify_modulo_check(expected) + Script.parse_string("OP_SWAP OP_DROP")
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point addition slow")


@pytest.mark.slow
@pytest.mark.parametrize("verify_gradient", [True, False])
@pytest.mark.parametrize(
    ("config", "unlocking_script", "expected", "stack_elements", "rolling_options"),
    generate_test_cases("test_doubling_slow"),
)
def test_doubling_slow(
    config, unlocking_script, expected, stack_elements, rolling_options, verify_gradient, save_to_json_folder
):
    unlock = unlocking_script
    clean_constant = verify_gradient

    lock = config.test_script.point_algebraic_doubling(
        take_modulo=True,
        check_constant=True,
        clean_constant=clean_constant,
        verify_gradient=verify_gradient,
        gradient=stack_elements["gradient"],
        P=stack_elements["P"],
        rolling_options=rolling_options,
    )

    lock += (
        expected if verify_gradient else modify_verify_modulo_check(expected) + Script.parse_string("OP_SWAP OP_DROP")
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point doubling slow")


@pytest.mark.parametrize("positive_modulo", [True, False])
@pytest.mark.parametrize(("config", "P", "Q", "expected"), generate_test_cases("test_addition_unknown_points"))
def test_addition_unknown_points(config, P, Q, positive_modulo, expected, save_to_json_folder):  # noqa: N803
    unlock = nums_to_script([config.modulus])
    # If the modulo is positive or the point is at infinity
    # we don't need the modulo for the modified verification script
    clean_constant = positive_modulo or expected.is_infinity()
    if not (P.is_infinity() or Q.is_infinity() or expected.is_infinity()):
        gradient = P.gradient(Q)
        unlock += nums_to_script(gradient.to_list())

    unlock += generate_unlock(P, degree=config.degree)
    unlock += generate_unlock(Q, degree=config.degree)

    lock = config.test_script.point_addition_with_unknown_points(
        take_modulo=True, positive_modulo=positive_modulo, check_constant=True, clean_constant=clean_constant
    )

    verification_script = generate_verify_point(expected, degree=config.degree)
    lock += (
        verification_script
        if clean_constant
        else modify_verify_modulo_check(verification_script) + Script.parse_string("OP_SWAP OP_DROP")
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "point addition with unknown points")


@pytest.mark.parametrize(
    ("config", "P", "a", "expected", "max_multiplier"), generate_test_cases("test_multiplication_unrolled")
)
def test_multiplication_unrolled(config, P, a, expected, max_multiplier, save_to_json_folder):  # noqa: N803
    unlocking_key = EllipticCurveFqUnrolledUnlockingKey(
        P=P.to_list(), a=a, gradients=unrolled_multiplication_gradients(a, P).as_data(), max_multiplier=max_multiplier
    )

    unlock = unlocking_key.to_unlocking_script(config.test_script, load_modulus=True)

    lock = config.test_script.unrolled_multiplication(
        max_multiplier=max_multiplier, modulo_threshold=1, check_constant=True, clean_constant=True
    )
    lock += generate_verify_point(expected, degree=config.degree) + Script.parse_string("OP_VERIFY")
    lock += generate_verify_point(P, degree=config.degree)

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "unrolled multiplication")


@pytest.mark.parametrize("positive_modulo", [True, False])
@pytest.mark.parametrize("points_on_altstack", [True, False])
@pytest.mark.parametrize(("config", "points", "expected"), generate_test_cases("test_multi_addition"))
def test_multi_addition(config, points, expected, positive_modulo, points_on_altstack, save_to_json_folder):
    unlock = nums_to_script([config.modulus])
    # If the modulo is positive or the point is at infinity
    # we don't need the modulo for the modified verification script
    clean_constant = positive_modulo or expected.is_infinity()

    # Compute the gradients
    gradients = multi_addition_gradients(points).as_data()
    if points_on_altstack:
        # Load the gradients
        for gradient in gradients[::-1]:
            if len(gradient) != 0:
                unlock += nums_to_script(gradient)
        # Load the points
        for point in points[::-1]:
            unlock += generate_unlock(point, degree=config.degree)
            unlock += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
    else:
        for i, point in enumerate(points[:0:-1]):
            if len(gradients[::-1][i]) != 0:
                unlock += nums_to_script(gradients[::-1][i])
            unlock += generate_unlock(point, degree=config.degree)
        unlock += generate_unlock(points[0], degree=config.degree)

    lock = config.test_script.multi_addition(
        n_points=len(points),
        points_on_altstack=points_on_altstack,
        take_modulo=True,
        check_constant=True,
        clean_constant=clean_constant,
        positive_modulo=positive_modulo,
    )

    verification_script = generate_verify_point(expected, degree=config.degree)
    lock += (
        verification_script
        if clean_constant
        else modify_verify_modulo_check(verification_script) + Script.parse_string("OP_SWAP OP_DROP")
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "multi addition")


@pytest.mark.parametrize("positive_modulo", [True, False])
@pytest.mark.parametrize(
    ("config", "scalars", "bases", "expected"), generate_test_cases("test_multi_scalar_multiplication_with_fixed_bases")
)
def test_multi_scalar_multiplication_with_fixed_bases(
    config, scalars, bases, expected, positive_modulo, save_to_json_folder
):
    # If the modulo is positive or the point is at infinity
    # we don't need the modulo for the modified verification script
    clean_constant = positive_modulo or expected.is_infinity()

    gradients_multiplications, gradients_additions = multi_scalar_multiplication_with_fixed_bases_gradients(
        scalars, bases
    ).as_data()

    unlocking_key = MsmWithFixedBasesUnlockingKey.from_data(
        scalars=scalars,
        gradients_multiplications=gradients_multiplications,
        max_multipliers=[config.order] * len(bases),
        gradients_additions=gradients_additions,
    )

    unlock = unlocking_key.to_unlocking_script(config.test_script, load_modulus=True)

    lock = config.test_script.multi_scalar_multiplication_with_fixed_bases(
        bases=[base.to_list() for base in bases],
        max_multipliers=[config.order] * len(bases),
        modulo_threshold=1,
        take_modulo=True,
        check_constant=True,
        clean_constant=clean_constant,
        positive_modulo=positive_modulo,
    )

    verification_script = generate_verify_point(expected, degree=config.degree)
    lock += (
        verification_script
        if clean_constant
        else modify_verify_modulo_check(verification_script) + Script.parse_string("OP_SWAP OP_DROP")
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(
            str(lock), str(unlock), save_to_json_folder, config.filename, "multi scalar multiplication with fixed bases"
        )
