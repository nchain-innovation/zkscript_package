import pytest
from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.models.curve import Curve
from elliptic_curves.models.ec import elliptic_curve_from_curve
from tx_engine import Context, Script, hash256d
from tx_engine.engine.util import GROUP_ORDER_INT, PRIME_INT, Gx, Gx_bytes, Gy

from src.zkscript.elliptic_curves.secp256k1.secp256k1 import Secp256k1
from src.zkscript.types.stack_elements import StackBaseElement, StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_scripts import nums_to_script

modulus = 115792089237316195423570985008687907853269984665640564039457584007908834671663
order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Fq_k1 = base_field_from_modulus(q=modulus)
Fr_k1 = base_field_from_modulus(q=order)
secp256k1, _ = elliptic_curve_from_curve(curve=Curve(a=Fq_k1(0), b=Fq_k1(7)))
generator = secp256k1(
    x=Fq_k1(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798),
    y=Fq_k1(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8),
)

signature_prefix = bytes.fromhex("0220") + Gx_bytes + bytes.fromhex("02")
dummy_h = int.to_bytes(53458750141241331933368176931386592061784348704092867077248862953896423193426, 32)


def compress(P) -> bytes:  # noqa: N803
    point_as_list = P.to_list()
    x_coordinate = int.to_bytes(point_as_list[0], (point_as_list[0].bit_length() + 8) // 8)
    ix = 0
    while x_coordinate[ix] == 0:
        ix += 1
    x_coordinate = x_coordinate[ix:]
    out = bytes.fromhex("03") if point_as_list[1] % 2 else bytes.fromhex("02")
    out += x_coordinate

    return out


def tweak_private_key(a: int) -> int:
    return (-2 * int.from_bytes(hash256d(dummy_h)) * pow(Gx, -1, GROUP_ORDER_INT) - a) % GROUP_ORDER_INT


@pytest.mark.parametrize(
    ("a", "A", "additional_constant"),
    [
        (2, generator.multiply(2), 0),
        (2, generator.multiply(tweak_private_key(2)), 0),
        (2, generator.multiply(3), 1),
        (3, generator.multiply(2), -1),
        (2, generator.multiply(12), 10),
    ],
)
@pytest.mark.parametrize("compressed_pubkey", [True, False])
def test_verify_base_point_multiplication_up_to_epsilon(a, A, additional_constant, compressed_pubkey):  # noqa: N803
    lock = Secp256k1.verify_base_point_multiplication_up_to_epsilon(
        True,
        True,
        additional_constant,
        h=StackFiniteFieldElement(2, False, 1) if compressed_pubkey else StackFiniteFieldElement(3, False, 1),
        a=StackFiniteFieldElement(1, False, 1) if compressed_pubkey else StackFiniteFieldElement(2, False, 1),
        A=StackBaseElement(0)
        if compressed_pubkey
        else StackEllipticCurvePoint(
            StackFiniteFieldElement(1, False, 1),
            StackFiniteFieldElement(0, False, 1),
        ),
    )
    lock += Script.parse_string("OP_1")

    unlock = nums_to_script([GROUP_ORDER_INT, Gx])
    unlock.append_pushdata(signature_prefix)
    unlock.append_pushdata(hash256d(dummy_h)[::-1])
    unlock += nums_to_script([a])
    if compressed_pubkey:
        unlock.append_pushdata(compress(A))
    else:
        unlock += nums_to_script(A.to_list())

    context = Context(unlock + lock, z=hash256d(dummy_h))
    assert context.evaluate()
    assert len(context.get_stack()) == 1


@pytest.mark.parametrize(
    ("gradient", "a", "A"),
    [
        (generator.get_lambda(generator.multiply(2)), 2, generator.multiply(2)),
        (generator.get_lambda(generator.multiply(5)), 5, generator.multiply(5)),
    ],
)
def test_verify_base_point_multiplication_with_addition(gradient, a, A):  # noqa: N803
    lock = Secp256k1.verify_base_point_multiplication_with_addition(
        True,
        True,
    )
    lock += Script.parse_string("OP_1")

    unlock = nums_to_script([PRIME_INT, GROUP_ORDER_INT, Gx])
    unlock.append_pushdata(signature_prefix)
    unlock += nums_to_script([Gy])
    unlock.append_pushdata(hash256d(dummy_h)[::-1])
    unlock += nums_to_script(gradient.to_list())
    unlock += nums_to_script([a])
    unlock += nums_to_script(A.to_list())

    context = Context(unlock + lock, z=hash256d(dummy_h))
    assert context.evaluate()
    assert len(context.get_stack()) == 1


@pytest.mark.parametrize(("a", "A"), [(2, generator.multiply(2)), (10, generator.multiply(10))])
def test_verify_base_point_multiplication_with_negation(a, A):  # noqa: N803
    lock = Secp256k1.verify_base_point_multiplication_with_negation(
        True,
        True,
    )
    lock += Script.parse_string("OP_1")

    unlock = nums_to_script([GROUP_ORDER_INT, Gx])
    unlock.append_pushdata(signature_prefix)
    unlock.append_pushdata(hash256d(dummy_h)[::-1])
    unlock += nums_to_script([a])
    unlock += nums_to_script(A.to_list())

    context = Context(unlock + lock, z=hash256d(dummy_h))
    assert context.evaluate()
    assert len(context.get_stack()) == 1
