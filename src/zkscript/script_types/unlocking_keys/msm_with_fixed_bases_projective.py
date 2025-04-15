"""Unlocking key for `multi_scalar_multiplication_with_fixed_bases` in EllipticCurveFq."""

from dataclasses import dataclass
from typing import Self

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq_projective import EllipticCurveFqProjective
from src.zkscript.script_types.unlocking_keys.unrolled_projective_ec_multiplication import (
    EllipticCurveFqProjectiveUnrolledUnlockingKey,
)
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class MsmWithFixedBasesProjectiveUnlockingKey:
    r"""Unlocking key for multi scalar multiplication with fixed bases.

    Args:
        scalar_multiplications_keys (list[EllipticCurveFqProjectiveUnrolledUnlockingKey]):
            `scalar_multiplications_keys[i]` is the unlocking key required to compute `scalars[i] * bases[i]`
    """

    scalar_multiplications_keys: list[EllipticCurveFqProjectiveUnrolledUnlockingKey]

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
            scalar_multiplications_keys=scalar_multiplications_keys,
        )

    def to_unlocking_script(self, ec_over_fq: EllipticCurveFqProjective, load_modulus=True) -> Script:
        """Return the unlocking script required by msm_with_fixed_bases script.

        Args:
            ec_over_fq (EllipticCurveFqProjective): The instantiation of ec arithmetic over Fq used to
                construct the unrolled_multiplication locking script.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.

        """
        out = nums_to_script([ec_over_fq.modulus]) if load_modulus else Script()

        # Load the unlocking scripts for the scalar multiplications
        for key in self.scalar_multiplications_keys[::-1]:
            out += key.to_unlocking_script(ec_over_fq=ec_over_fq, load_modulus=False, load_P=False)

        return out
