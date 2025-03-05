"""Unlocking key for `multi_scalar_multiplication_with_fixed_bases` in EllipticCurveFq."""

from dataclasses import dataclass
from math import log2
from typing import Self

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.script_types.unlocking_keys.unrolled_ec_multiplication import EllipticCurveFqUnrolledUnlockingKey
from src.zkscript.script_types.stack_elements import StackBaseElement
from src.zkscript.util.utility_scripts import nums_to_script
from src.zkscript.util.utility_scripts import bool_to_moving_function, move, nums_to_script


@dataclass
class MsmWithFixedBasesUnlockingKey:
    r"""Unlocking key for multi scalar multiplication with fixed bases.

    Args:
        scalar_multiplications_keys (list[EllipticCurveFqUnrolledUnlockingKey]): `scalar_multiplications_keys[i]` is the
            unlocking key required to compute `scalars[i] * bases[i]`
        max_multipliers (list[int]): `max_multipliers[i]` is the the maximum value of the i-th scalar.
        gradients_additions (list[list[int]]): `gradients_additions[i]` is the gradient required to compute the addition
            `bases[n-i-2] + (\sum_(j=n-i-1)^(n-1) bases[j]`
    """

    scalar_multiplications_keys: list[EllipticCurveFqUnrolledUnlockingKey]
    max_multipliers: list[int]
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
            max_multipliers=max_multipliers,
            gradients_additions=gradients_additions,
        )

    def to_unlocking_script(
        self, ec_over_fq: EllipticCurveFq, load_modulus=True, extractable_scalars: int = 0
    ) -> Script:
        """Return the unlocking script required by multi_scalar_multiplication_with_fixed_bases script.

        Args:
            ec_over_fq (EllipticCurveFq): The instantiation of ec arithmetic over Fq used to
                construct the unrolled_multiplication locking script.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.
            extractable_scalars (int): The number of scalars that are extractable in script. Defaults to `0`.
                Indexing starts counting from the first scalar, i.e., the last loaded on the stack.

        """
        n_keys = len(self.scalar_multiplications_keys)
        assert extractable_scalars <= n_keys, "Index out of bounds"

        out = nums_to_script([ec_over_fq.MODULUS]) if load_modulus else Script()

        # Load the gradients for the additions
        for gradient in self.gradients_additions[::-1]:
            out += nums_to_script(gradient) if len(gradient) != 0 else Script()

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
        n_blocks = sum([int(log2(max_multipliers[i])) for i in range(index + 1)])
        front = StackBaseElement(n_blocks * 4 + index - 4)
        rear = StackBaseElement(n_blocks * 4 + index - 2)

        out = Script()

        # Extract the bits
        # stack out: [.., rear[0], front[0], .., rear[M-1], front[M-1]]
        for i in range(M):
            out += move(rear.shift(-2 * i), bool_to_moving_function(rolling_option))
            out += move(front.shift(-2 * i + 1), bool_to_moving_function(rolling_option))

        out += Script.parse_string("OP_1")
        out += Script.parse_string(
            " ".join(["OP_SWAP OP_IF OP_2 OP_MUL OP_SWAP OP_IF OP_1ADD OP_ENDIF OP_ELSE OP_NIP OP_ENDIF"] * M)
        )

        return out
