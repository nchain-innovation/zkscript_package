"""Unlocking key for `multi_scalar_multiplication_with_fixed_bases` in EllipticCurveFq."""

from dataclasses import dataclass
from typing import Self

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.script_types.unlocking_keys.unrolled_ec_multiplication import EllipticCurveFqUnrolledUnlockingKey
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class MsmWithFixedBasesUnlockingKey:
    r"""Unlocking key for multi scalar multiplication with fixed bases.

    Args:
        scalar_multiplications_keys (list[EllipticCurveFqUnrolledUnlockingKey]): `scalar_multiplications_keys[i]` is the
            unlocking key required to compute `scalars[i] * bases[i]`
        gradients_additions (list[list[int]]): `gradients_additions[i]` is the gradient required to compute the addition
            `bases[n-i-2] + (\sum_(j=n-i-1)^(n-1) bases[j]`
    """

    scalar_multiplications_keys: list[EllipticCurveFqUnrolledUnlockingKey]
    gradients_additions: list[list[int]]

    @staticmethod
    def from_data(
        scalars: list[int],
        gradients_multiplications: list[list[list[list[int]]]],
        max_multipliers: list[int],
        gradients_additions: list[list[int]],
    ) -> Self:
        r"""Construct an instance of `Self` from the provided data.

        Args:
            scalars (list[int]): `scalar[i]` is the scalar by which we want to multiply the i-th base point.
            gradients_multiplications (list[list[list[int]]]): the gradients to execute the script
                `unrolled_multiplication` that computes `scalars[i] * bases[i]`
            max_multipliers (list[int]): `max_multipliers[i]` is the maximum multiplier allowed for the
                multiplication of the i-th base point
            gradients_additions (list[int]): `gradients_additions[i]` is the gradient of the addition
                `bases[n-i-2] + (\sum_(j=n-i-1)^(n-1) bases[j]`
        """
        scalar_multiplications_keys = [
            EllipticCurveFqUnrolledUnlockingKey(P=None, a=scalar, gradients=gradients, max_multiplier=multiplier)
            for (scalar, gradients, multiplier) in zip(scalars, gradients_multiplications, max_multipliers)
        ]

        return MsmWithFixedBasesUnlockingKey(
            scalar_multiplications_keys=scalar_multiplications_keys,
            gradients_additions=gradients_additions,
        )

    def to_unlocking_script(
        self, ec_over_fq: EllipticCurveFq, load_modulus=True, extractable_scalars: bool = False
    ) -> Script:
        """Return the unlocking script required by multi_scalar_multiplication_with_fixed_bases script.

        Args:
            ec_over_fq (EllipticCurveFq): The instantiation of ec arithmetic over Fq used to
                construct the unrolled_multiplication locking script.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.
            extractable_scalars (bool): If `True`, the unlocking scripts for the unrolled multiplications ar
                constructed with `fixed_length_unlock = True`.

        """
        out = nums_to_script([ec_over_fq.modulus]) if load_modulus else Script()

        # Load the gradients for the additions
        for gradient in self.gradients_additions[::-1]:
            out += nums_to_script(gradient) if len(gradient) != 0 else Script()

        # Load the unlocking scripts for the scalar multiplications
        for key in self.scalar_multiplications_keys[::-1]:
            out += key.to_unlocking_script(
                ec_over_fq=ec_over_fq, fixed_length_unlock=extractable_scalars, load_modulus=False, load_P=False
            )

        return out
