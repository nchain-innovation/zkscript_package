"""Unlocking key for RefTx."""

from dataclasses import dataclass
from typing import Self

from tx_engine import Script
from tx_engine.engine.util import GROUP_ORDER_INT, Gx, Gx_bytes

from src.zkscript.groth16.model.groth16 import Groth16
from src.zkscript.script_types.unlocking_keys.groth16 import Groth16UnlockingKey
from src.zkscript.script_types.unlocking_keys.groth16_proj import Groth16ProjUnlockingKey
from src.zkscript.script_types.unlocking_keys.msm_with_fixed_bases import MsmWithFixedBasesUnlockingKey
from src.zkscript.script_types.unlocking_keys.msm_with_fixed_bases_projective import (
    MsmWithFixedBasesProjectiveUnlockingKey,
)
from src.zkscript.util.utility_scripts import nums_to_script

BYTES_32 = 32
BYTES_16 = 16
BYTES_8 = 8
BYTES_4 = 4
BYTES_2 = 2
BYTES_1 = 1


@dataclass
class RefTxUnlockingKey:
    r"""Class encapsulating the data required to generate an unlocking script for a RefTx verifier.

    Attributes:
        __groth16_unlocking_key (Groth16UnLockingKey | Groth16ProjUnlockingKey): The Groth16 unlocking key
            used to construct the RefTx unlocking script. This is the key for the RefTx circuit
            C'(l_out, sighash(stx), u_stx) with l_out fixed.

    Notes:
        The public inputs to the RefTx circuit are (l_out, sighash(stx), u_stx). However, for the purpose of this
        dataclass we consider l_out fixed and only consider the public inputs (sighash(stx), u_stx). This means
        that gamma_abc is only given by the subset needed to compute the msm for u_stx and sighash(stx). Similarly,
        the gradient for the final sum in the computation of the msm is not to add gamma_abc[0], but to add
            gamma_abc[0] + \sum_(i=1)^(n_l_out) pub[i] * gamma_abc[i+1]
    """

    __groth16_unlocking_key: Groth16UnlockingKey | Groth16ProjUnlockingKey

    @staticmethod
    def __bytes_sighash_chunks(groth16_model: Groth16) -> int:
        """Compute the number of bytes of each chunk of the sighash.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the reftx script.
        """
        # Compute the byte size of self.groth_model.r
        byte_size_r = groth16_model.r.bit_length() // 8
        # Compute the max multiplier for the chunks in which sighash is split
        if byte_size_r > BYTES_32:
            return BYTES_32
        if byte_size_r > BYTES_16:
            return BYTES_16
        if byte_size_r > BYTES_8:
            return BYTES_8
        if byte_size_r > BYTES_4:
            return BYTES_4
        if byte_size_r > BYTES_2:
            return BYTES_2
        return BYTES_1

    @staticmethod
    def __multipliers(groth16_model: Groth16, pub: list[int], max_multipliers: list[int] | None = None) -> list[int]:
        """Append the max multipliers for sighash(stx).

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the reftx script.
            pub (list[int]): The list of public statements: (sighash(stx), u_stx).
            max_multipliers (list[int]): `max_multipliers[i]` is the maximum multiplier allowed for the
                multiplication of gamma_abc[i], only considering the ones for u_stx.
        """
        # Compute the byte size of self.groth_model.r
        bytes_sighash_chunks = RefTxUnlockingKey.__bytes_sighash_chunks(groth16_model)
        n_chunks = 32 // bytes_sighash_chunks
        max_multipliers = max_multipliers if max_multipliers is not None else [groth16_model.r] * (len(pub) - n_chunks)
        return [*[2 ** (bytes_sighash_chunks * 8)] * n_chunks, *max_multipliers]

    @staticmethod
    def from_data(
        groth16_model: Groth16,
        pub: list[int],
        A: list[int],  # noqa: N803
        B: list[int],  # noqa: N803
        C: list[int],  # noqa: N803
        gradients_pairings: list[list[list[list[int]]]] | None,
        gradients_multiplications: list[list[list[list[int]]]] | None,
        max_multipliers: list[int] | None,
        gradients_additions: list[list[int]] | None,
        inverse_miller_output: list[int],
        gradient_precomputed_l_out: list[int] | None,
        has_precomputed_gradients: bool = True,
        use_proj_coordinates: bool = False,
    ) -> Self:
        r"""Construct an instance of `Self` from the provided data.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the reftx script.
            pub (list[int]): The list of public statements: (sighash(stx), u_stx).
            A (list[int]): The value of `A` in the proof.
            B (list[int]): The value of `B` in the proof.
            C (list[int]): The value of `C` in the proof.
            gradients_pairings (list[list[list[list[int]]]]): list of gradients required to compute the pairings
                in the Groth16 verification equation. The meaning of the lists is:
                    - gradients_pairings[0]: gradients required to compute w*B
                    - gradients_pairings[1]: gradients required to compute w*(-gamma)
                    - gradients_pairings[2]: gradients required to compute w*(-delta)
            gradients_multiplications (list[list[list[int]]]): the gradients to execute the script
                `unrolled_multiplication` that computes `pub[i] * gamma_abc[i]`
            max_multipliers (list[int]): `max_multipliers[i]` is the maximum multiplier allowed for the
                multiplication of gamma_abc[i], only considering u_stx.
            gradients_additions (list[int]): `gradients_additions[i]` is the gradient of the addition
                `gamma_abc[n-i-2] + (\sum_(j=n-i-1)^(n-1) gamma_abc[j]`
            inverse_miller_output (list[int]): the inverse of
                miller(A,B) * miller(gamma_abc[0] + \sum_{i >=0} pub[i] * gamma_abc[i+1], -gamma) * miller(C, -delta)
            gradient_precomputed_l_out (list[int]): The gradient required to compute the sum
                (gamma_abc[0] + \sum_(i=1)^(n_l_out) pub[i] * gamma_abc[i+1]) +
                    \sum_(i=n_l_out+1)^(n_pub) pub[i] * gamma_abc[i+1]
            has_precomputed_gradients (bool): Flag determining if the precomputed gradients used to compute
                w*(-gamma) and w*(-delta) are in the unlocking script. Defaults to `True`.
            use_proj_coordinates (bool): Flag indicating whether the groth16 algorithm uses projective coordinates.
        """
        max_multipliers = RefTxUnlockingKey.__multipliers(groth16_model, pub)
        if use_proj_coordinates:
            msm_key = MsmWithFixedBasesProjectiveUnlockingKey.from_data(
                scalars=pub,
                max_multipliers=max_multipliers,
            )

            groth16_key = Groth16ProjUnlockingKey(
                pub,
                A,
                B,
                C,
                inverse_miller_output,
                msm_key,
            )

        else:
            msm_key = MsmWithFixedBasesUnlockingKey.from_data(
                scalars=pub,
                gradients_multiplications=gradients_multiplications,
                max_multipliers=max_multipliers,
                gradients_additions=gradients_additions,
            )

            groth16_key = Groth16UnlockingKey(
                pub,
                A,
                B,
                C,
                gradients_pairings,
                inverse_miller_output,
                msm_key,
                gradient_precomputed_l_out,
                has_precomputed_gradients=has_precomputed_gradients,
            )

        return RefTxUnlockingKey(groth16_key)

    def to_unlocking_script(
        self,
        groth16_model: Groth16,
        load_constants: bool = True,
    ) -> Script:
        r"""Return the script needed to execute the RefTx locking script.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the groth16_verifier script.
            load_constants (bool): If `True`, it loads to the stack the constants needed to execute the
                RefTx locking script. Defauls to `True`.
        """
        # Compute bytes sighash chunks and number of chunks
        bytes_sighash_chunks = self.__bytes_sighash_chunks(groth16_model)
        n_chunks = 32 // bytes_sighash_chunks
        out = nums_to_script([groth16_model.pairing_model.modulus]) if load_constants else Script()

        if load_constants:
            out += nums_to_script([GROUP_ORDER_INT, Gx])
            out.append_pushdata(bytes.fromhex("0220") + Gx_bytes + bytes.fromhex("02"))

        out += self.__groth16_unlocking_key.to_unlocking_script(
            groth16_model=groth16_model,
            load_modulus=False,
            extractable_inputs=n_chunks,
        )

        return out
