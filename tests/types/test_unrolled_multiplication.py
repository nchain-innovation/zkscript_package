from math import log2

import pytest
from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.models.ec import ShortWeierstrassEllipticCurve
from elliptic_curves.util.zkscript import (
    unrolled_multiplication_gradients,
)
from tx_engine import Context, Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.types.unlocking_keys.unrolled_ec_multiplication import EllipticCurveFqUnrolledUnlockingKey
from src.zkscript.util.utility_scripts import nums_to_script

# Data for Secp256k1
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


@pytest.mark.parametrize(
    ("P", "a", "max_multiplier", "expected"),
    [
        (
            generator,
            3,
            8,
            3,
        ),
        (
            generator,
            89179908133058966563943425115874784614382846700656822879827803812293592024531,
            order,
            89179908133058966563943425115874784614382846700656822879827803812293592024531,
        ),
        (
            generator,
            99918161303508978633620523839997829444876269911501350624465443203877613350,
            2**250,
            99918161303508978633620523839997829444876269911501350624465443203877613350,
        ),
        (
            generator,
            245130299858301666475531021987374198395,
            2**128,
            245130299858301666475531021987374198395,
        ),
        (
            generator,
            10204030,
            2**128,
            10204030,
        ),
    ],
)
def test_extract_scalar_as_unsigned(P, a, expected, max_multiplier):  # noqa: N803
    unlocking_key = EllipticCurveFqUnrolledUnlockingKey(
        P=P.to_list(), a=a, gradients=unrolled_multiplication_gradients(a, P).as_data(), max_multiplier=max_multiplier
    )

    script = unlocking_key.to_unlocking_script(test_script, fixed_length_unlock=True, load_modulus=True)
    script += unlocking_key.extract_scalar_as_unsigned(rolling_option=True)
    script += nums_to_script([expected]) + Script.parse_string("OP_EQUALVERIFY")
    script += Script.parse_string(" ".join(["OP_DROP"] * (int(log2(max_multiplier)) * 2 + 4)))
    script += Script.parse_string("OP_1")

    context = Context(script=script)
    assert context.evaluate()
    assert context.get_stack().size() == 1
