from math import log2

import pytest
from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.models.ec import ShortWeierstrassEllipticCurve
from elliptic_curves.util.zkscript import (
    multi_scalar_multiplication_with_fixed_bases_gradients,
)
from tx_engine import Context, Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.types.unlocking_keys.msm_with_fixed_bases import MsmWithFixedBasesUnlockingKey
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


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize(
    ("scalars", "bases", "max_multipliers"),
    [
        (
            [1, 2, 3],
            [generator, generator, generator],
            [8, 16, 8],
        ),
        (
            [
                89179908133058966563943425115874784614382846700656822879827803812293592024531,
                99918161303508978633620523839997829444876269911501350624465443203877613350,
                245130299858301666475531021987374198395,
            ],
            [generator, generator, generator],
            [order, 2**250, 2**128],
        ),
    ],
)
def test_msm_with_fixed_bases(scalars, bases, max_multipliers, index):
    expected = scalars[index]
    gradients_multiplications, gradients_additions = multi_scalar_multiplication_with_fixed_bases_gradients(
        scalars, bases
    ).as_data()

    unlocking_key = MsmWithFixedBasesUnlockingKey.from_data(
        scalars=scalars,
        gradients_multiplications=gradients_multiplications,
        max_multipliers=max_multipliers,
        gradients_additions=gradients_additions,
    )

    script = unlocking_key.to_unlocking_script(test_script, load_modulus=True, extractable_scalars=3)
    script += MsmWithFixedBasesUnlockingKey.extract_scalar_as_unsigned(
        max_multipliers=unlocking_key.max_multipliers, index=index, rolling_option=True
    )
    script += nums_to_script([expected]) + Script.parse_string("OP_EQUALVERIFY")
    script += Script.parse_string("OP_DROP")  # Drop modulus
    script += Script.parse_string(" ".join(["OP_DROP"] * len(gradients_additions)))  # Drop gradients addition
    for ix, multiplier in enumerate(max_multipliers):
        if ix != index:
            script += Script.parse_string(" ".join(["OP_DROP"] * (int(log2(multiplier)) * 4 + 1)))
        else:
            script += Script.parse_string(" ".join(["OP_DROP"] * (int(log2(multiplier)) * 2 + 1)))
    script += Script.parse_string("OP_1")

    context = Context(script=script)
    # context.evaluate()
    # print(context.get_stack(),"\n")
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0
