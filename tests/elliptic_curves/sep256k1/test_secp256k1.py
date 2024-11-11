import pytest
from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.models.curve import Curve
from elliptic_curves.models.ec import elliptic_curve_from_curve
from tx_engine import Context, Script, hash256d

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

signature_prefix = bytes.fromhex("0220") + generator.x.x.to_bytes(32) + bytes.fromhex("02")
dummy_h = int.to_bytes(53458750141241331933368176931386592061784348704092867077248862953896423193426, 32)
h = int.from_bytes(hash256d(dummy_h))


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
    return (-2 * h * pow(generator.x.x, -1, order) - a) % order


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

    unlock = nums_to_script([order, generator.x.x])
    unlock.append_pushdata(signature_prefix)
    unlock += nums_to_script([h,a])
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

    unlock = nums_to_script([modulus, order, generator.x.x])
    unlock.append_pushdata(signature_prefix)
    unlock += nums_to_script([generator.y.x, h])
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

    unlock = nums_to_script([order, generator.x.x])
    unlock.append_pushdata(signature_prefix)
    unlock += nums_to_script([h, a])
    unlock += nums_to_script(A.to_list())

    context = Context(unlock + lock, z=hash256d(dummy_h))
    assert context.evaluate()
    assert len(context.get_stack()) == 1

@pytest.mark.parametrize("negate", [True,False])
@pytest.mark.parametrize(
    ("b", "P"),
    [
        (3, generator.multiply(2)),
        (56, generator.multiply(231)),
    ],
)
def test_verify_point_multiplication_up_to_sign(b, P, negate):  # noqa: N803
    Q = P.multiply(b)
    h_times_x_coordinate_target_inverse = Fr_k1(h) * Fr_k1(Q.x.x).invert()
    h_times_x_coordinate_target_inverse_times_G = generator.multiply(h_times_x_coordinate_target_inverse.x)
    gradient = P.get_lambda(-h_times_x_coordinate_target_inverse_times_G)
    x_coordinate_times_b_inverse = Fr_k1(Q.x.x) * Fr_k1(b).invert()

    lock = Secp256k1.verify_point_multiplication_up_to_sign(
        True,
        True,
    )
    lock += Script.parse_string("OP_1")

    unlock = Script()
    unlock += nums_to_script([modulus, order, generator.x.x])
    unlock.append_pushdata(signature_prefix)
    unlock += nums_to_script([h, b, x_coordinate_times_b_inverse.x, h_times_x_coordinate_target_inverse.x])
    unlock += nums_to_script(gradient.to_list())
    unlock += nums_to_script(Q.multiply(-1 if negate else 1).to_list())
    unlock += nums_to_script(P.to_list())
    unlock += nums_to_script(h_times_x_coordinate_target_inverse_times_G.to_list())

    context = Context(unlock + lock, z=hash256d(dummy_h))
    assert context.evaluate()
    assert len(context.get_stack()) == 1

@pytest.mark.parametrize(("b","P"), [(3, generator.multiply(10)), (110, generator.multiply(547))])
def test_verify_point_multiplication(b,P):  # noqa: N803
    Q = P.multiply(b)

    d = []
    d.append(Fr_k1(h) * Fr_k1(Q.x.x).invert())
    d.append(Fr_k1(h) * Fr_k1((Q + generator.multiply(b)).x.x).invert())

    s = []
    s.append(Fr_k1(Q.x.x) * Fr_k1(b).invert())
    s.append(Fr_k1((Q + generator.multiply(b)).x.x) * Fr_k1(b).invert())

    D = []
    D.append(generator.multiply(d[0].x))
    D.append(generator.multiply(d[1].x-1))
    D.append(generator.multiply(b))

    gradients = []
    gradients.append(P.get_lambda(-D[0]))
    gradients.append(P.get_lambda(-D[1]))
    gradients.append(Q.get_lambda(D[2]))


    lock = Secp256k1.verify_point_multiplication(
        True,
        True,
    )
    lock += Script.parse_string("OP_1")

    unlock = Script()
    unlock += nums_to_script([modulus,order,generator.x.x])
    unlock.append_pushdata(signature_prefix)

    unlock += nums_to_script([h])
    unlock += nums_to_script([s_.x for s_ in s])
    unlock += nums_to_script([gradients_.x for gradients_ in gradients])
    unlock += nums_to_script([d_.x for d_ in d])
    for D_ in D:
        unlock += nums_to_script(D_.to_list())
    unlock += nums_to_script(Q.to_list())
    unlock += nums_to_script([b])
    unlock += nums_to_script(P.to_list())

    context = Context(unlock + lock, z = hash256d(dummy_h))
    assert context.evaluate()
    assert len(context.get_stack()) == 1
