"""Unlocking key for `multi_scalar_multiplication_with_fixed_bases` in EllipticCurveFq."""

from dataclasses import dataclass
from math import log2
from typing import Self

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq_projective import EllipticCurveFqProjective
from src.zkscript.script_types.stack_elements import StackBaseElement
from src.zkscript.script_types.unlocking_keys.unrolled_projective_ec_multiplication import (
    EllipticCurveFqProjectiveUnrolledUnlockingKey,
)
from src.zkscript.util.utility_scripts import bool_to_moving_function, move, nums_to_script


@dataclass
class MsmWithFixedBasesProjectiveUnlockingKey:
    r"""Unlocking key for multi scalar multiplication with fixed bases.

    Args:
        scalar_multiplications_keys (list[EllipticCurveFqProjectiveUnrolledUnlockingKey]):
            `scalar_multiplications_keys[i]` is the unlocking key required to compute `scalars[i] * bases[i]`
        max_multipliers (list[int]): `max_multipliers[i]` is the the maximum value of the i-th scalar.
    """

    scalar_multiplications_keys: list[EllipticCurveFqProjectiveUnrolledUnlockingKey]
    max_multipliers: list[int]

    @staticmethod
    def from_data(
        scalars: list[int],
        max_multipliers: list[int],
    ) -> Self:
        r"""Construct an instance of `Self` from the provided data.

        Args:
            scalars (list[int]): `scalar[i]` is the scalar by which we want to multiply the i-th base point.
            max_multipliers (list[int]): `max_multipliers[i]` is the maximum multiplier allowed for the
                multiplication of the i-th base point
        """
        scalar_multiplications_keys = [
            EllipticCurveFqProjectiveUnrolledUnlockingKey(P=None, a=scalar, max_multiplier=multiplier)
            for (scalar, multiplier) in zip(scalars, max_multipliers)
        ]

        return MsmWithFixedBasesProjectiveUnlockingKey(
            scalar_multiplications_keys=scalar_multiplications_keys, max_multipliers=max_multipliers
        )

    def to_unlocking_script(
        self, ec_over_fq: EllipticCurveFqProjective, load_modulus=True, extractable_scalars: int = 0
    ) -> Script:
        """Return the unlocking script required by msm_with_fixed_bases script.

        Args:
            ec_over_fq (EllipticCurveFqProjective): The instantiation of ec arithmetic over Fq used to
                construct the unrolled_multiplication locking script.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.
            extractable_scalars (int): The number of scalars that are extractable in script. Defaults to `0`.
                Indexing starts counting from the first scalar, i.e., the last loaded on the stack.

        """
        n_keys = len(self.scalar_multiplications_keys)
        assert extractable_scalars <= n_keys, "Index out of bounds"

        out = nums_to_script([ec_over_fq.modulus]) if load_modulus else Script()

        # Load the unlocking scripts for the scalar multiplications
        for i, key in enumerate(self.scalar_multiplications_keys[::-1]):
            out += key.to_unlocking_script(
                ec_over_fq=ec_over_fq,
                fixed_length_unlock=(n_keys - extractable_scalars <= i),
                load_modulus=False,
                load_P=False,
            )

        return out

    @staticmethod
    def extract_scalar_as_unsigned(max_multipliers: list[int], index: int, rolling_option: bool) -> Script:
        """Return the script that extracts the scalar at position `index` as an unsigned number.

        Args:
            max_multipliers (list[int]): `max_multipliers[i]` is the maximum multiplier allowed for the
                multiplication of the i-th base point
            index (int): The index of the scalar to extract.
            rolling_option (bool): If `True`, the bits are rolled.
        """
        assert index < len(max_multipliers), "Index out of bounds"

        M = int(log2(max_multipliers[index]))
        # Each block ha (log2(max_multipliers[i]) * 2) elements
        n_blocks = sum([int(log2(max_multipliers[i])) for i in range(index + 1)])
        # On top of each block's elements, we have the zero marker: add `index` elements
        element = StackBaseElement(n_blocks * 2 - 1 + index)

        out = Script()

        # Extract the bits
        # stack out: [.., rear[0], front[0], .., rear[M-1], front[M-1]]
        for _ in range(2 * M):
            out += move(element, bool_to_moving_function(rolling_option))

        out += Script.parse_string("OP_1")
        out += Script.parse_string(
            " ".join(["OP_SWAP OP_IF OP_2 OP_MUL OP_SWAP OP_IF OP_1ADD OP_ENDIF OP_ELSE OP_NIP OP_ENDIF"] * M)
        )

        return out
