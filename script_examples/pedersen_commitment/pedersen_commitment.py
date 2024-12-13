"""Pedersen commitment package."""

from tx_engine import Script

from src.zkscript.elliptic_curves.secp256k1.secp256k1 import Secp256k1
from src.zkscript.types.stack_elements import (
    StackBaseElement,
    StackEllipticCurvePoint,
    StackFiniteFieldElement,
    StackNumber,
)
from src.zkscript.util.utility_scripts import move, nums_to_script, pick, roll


class PedersenCommitmentSecp256k1:
    """Bitcoin scripts for the Pedersen commitment scheme over Secp256k1."""

    def __init__(self, B: list[int], H: list[int]):  # noqa: N803
        """Initialise the Pedersen commitment scheme.

        The scheme is: Pedersen.commit(m,r) = mB + rH.

        Args:
            B (list[int]): The base of the commitment scheme.
            H (list[int]): The element used to introduce randomness in the commitment.
        """
        self.B = B
        self.H = H

    def commit(self, commitment: bytes) -> Script:
        """Commitment script for Pedersen commitment scheme.

        Stack input:
            - stack:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, MODULUS, sig_hash_preimage, h, gradient(Q,R),
                            data(Q,m,P), data(R,r,S)]
            - altstack: []
        Stack output:
            - stack:    [0/1]
            - altstack: []

        Where data(Q,m,P) and data(R,r,S) is the data required to execute the method
        `Secp256k1.verify_point_multiplication` to prove that Q = mP and R = rS, respectively.
        This data does not contain `sig_hash_preimage` and `h`.

        Args:
            commitment (bytes): The commitment.

        Returns:
            The Bitcoin script that commits to `commitment`.
        """
        sig_hash_preimage = StackBaseElement(38)
        h = StackFiniteFieldElement(37, False, 1)
        gradient = StackFiniteFieldElement(36, False, 1)
        Q = StackEllipticCurvePoint(StackFiniteFieldElement(22, False, 1), StackFiniteFieldElement(21, False, 1))
        R = StackEllipticCurvePoint(StackFiniteFieldElement(4, False, 1), StackFiniteFieldElement(3, False, 1))
        out = Script()

        # Verify Q != R
        out += move(Q, pick)  # Move Q
        out += Script.parse_string("OP_2DUP OP_CAT")
        out += move(R.shift(3), pick)  # Move R
        out += Script.parse_string("OP_2DUP OP_CAT")
        out += roll(position=3, n_elements=1)
        out += Script.parse_string("OP_EQUAL OP_NOT OP_VERIFY")

        # Compute Q + R and place it on the altstack
        out += Secp256k1.ec_fq.point_algebraic_addition(
            take_modulo=True,
            check_constant=False,
            clean_constant=False,
            verify_gradient=True,
            positive_modulo=True,
            modulus=StackNumber(-4, False),
            gradient=gradient.shift(4),
        )
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Verify that R = rS
        out += Secp256k1.verify_point_multiplication(
            check_constants=True,
            clean_constants=False,
            sig_hash_preimage=sig_hash_preimage.shift(-1),
            h=h.shift(-1),
            rolling_options=((1 << 15) - 1) ^ 1 ^ (1 << 1) ^ (1 << 14),
        )
        out += Script.parse_string("OP_VERIFY")

        # Verify S = H
        for el in self.H[::-1]:
            out += nums_to_script([el])
            out += Script.parse_string("OP_EQUALVERIFY")

        # Verify that Q = mP
        out += Secp256k1.verify_point_multiplication(
            check_constants=False,
            clean_constants=True,
            sig_hash_preimage=sig_hash_preimage.shift(-19),
            h=h.shift(-19),
            rolling_options=((1 << 15) - 1) ^ (1 << 14),
        )
        out += Script.parse_string("OP_VERIFY")

        # Verify P = B
        for el in self.B[::-1]:
            out += nums_to_script([el])
            out += Script.parse_string("OP_EQUALVERIFY")

        # Verify Q + R = commitment
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_CAT")
        out.append_pushdata(commitment)
        out += Script.parse_string("OP_EQUAL")

        return out
