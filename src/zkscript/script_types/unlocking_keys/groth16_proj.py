"""Unlocking keys for Groth16."""

from dataclasses import dataclass
from typing import Self

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq_projective import EllipticCurveFqProjective
from src.zkscript.groth16.model.groth16 import Groth16
from src.zkscript.script_types.unlocking_keys.msm_with_fixed_bases_projective import (
    MsmWithFixedBasesProjectiveUnlockingKey,
)
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class Groth16ProjUnlockingKey:
    r"""Class encapsulating the data to generate a Groth16 unlocking script using projective coordinates.

    Attributes:
        pub (list[int]): list of public statements.
        A (list[int]): Component of the zk proof.
        B (list[int]): Component of the zk proof.
        C (list[int]): Component of the zk proof.
        inverse_miller_output (list[int]): the inverse of
            miller(A,B) * miller(gamma_abc[0] + \sum_{i >=0} pub[i] * gamma_abc[i+1], -gamma) * miller(C, -delta)
        msm_key (MsmWithFixedBasesUnlockingKey): Unlocking key required to compute the msm
            \sum_(i=1)^l pub[i] * gamma_abc[i+1]
    """

    pub: list[int]
    A: list[int]
    B: list[int]
    C: list[int]
    inverse_miller_output: list[int]
    msm_key: MsmWithFixedBasesProjectiveUnlockingKey

    @staticmethod
    def from_data(
        groth16_model: Groth16,
        pub: list[int],
        A: list[int],  # noqa: N803
        B: list[int],  # noqa: N803
        C: list[int],  # noqa: N803
        max_multipliers: list[int] | None,
        inverse_miller_output: list[int],
    ) -> Self:
        r"""Construct an instance of `Self` from the provided data.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the groth16_verifier script.
            pub (list[int]): The list of public statements.
            A (list[int]): The value of `A` in the proof.
            B (list[int]): The value of `B` in the proof.
            C (list[int]): The value of `C` in the proof.
            max_multipliers (list[int]): `max_multipliers[i]` is the maximum multiplier allowed for the
                multiplication of gamma_abc[i]
            inverse_miller_output (list[int]): the inverse of
                miller(A,B) * miller(gamma_abc[0] + \sum_{i >=0} pub[i] * gamma_abc[i+1], -gamma) * miller(C, -delta)
        """
        max_multipliers = max_multipliers if max_multipliers is not None else [groth16_model.r] * len(pub)

        msm_key = MsmWithFixedBasesProjectiveUnlockingKey.from_data(
            scalars=pub,
            max_multipliers=max_multipliers,
        )

        return Groth16ProjUnlockingKey(
            pub,
            A,
            B,
            C,
            inverse_miller_output,
            msm_key,
        )

    def to_unlocking_script(
        self,
        groth16_model: Groth16,
        load_modulus: bool = True,
        extractable_inputs: int = 0,
    ) -> Script:
        r"""Return the script needed to execute the groth16_verifier script.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the groth16_verifier script.
            load_modulus (bool): Whether or not to load the modulus. Defaults to `True`.
            extractable_inputs (int): The number of inputs that are extractable in script. Defaults to `0`.
        """
        ec_fq = EllipticCurveFqProjective(
            groth16_model.pairing_model.modulus, groth16_model.curve_a, groth16_model.curve_b
        )

        out = nums_to_script([groth16_model.pairing_model.modulus]) if load_modulus else Script()

        # Load inverse_miller_output inverse
        out += nums_to_script(self.inverse_miller_output)

        # Load A, B, C
        out += nums_to_script(self.A)
        out += nums_to_script(self.B)
        out += nums_to_script(self.C)

        out += self.msm_key.to_unlocking_script(
            ec_over_fq=ec_fq,
            load_modulus=False,
            extractable_scalars=extractable_inputs,
        )

        return out


@dataclass
class Groth16ProjUnlockingKeyWithPrecomputedMsm:
    r"""Class encapsulating the data for a Groth16 unlocking script with precomputed msm in projective coordinates.

    Attributes:
        A (list[int]): Component of the zk proof.
        B (list[int]): Component of the zk proof.
        C (list[int]): Component of the zk proof.
        inverse_miller_output (list[int]): the inverse of
            miller(A,B) * miller(gamma_abc[0] + \sum_{i >=0} pub[i] * gamma_abc[i+1], -gamma) * miller(C, -delta)
        precomputed_msm: the sum \sum_(i=0)^l a_i * gamma_abc[i]
    """

    A: list[int]
    B: list[int]
    C: list[int]
    inverse_miller_output: list[int]
    precomputed_msm: list[int]

    def to_unlocking_script(
        self,
        groth16_model: Groth16,
        load_modulus: bool = True,
    ) -> Script:
        r"""Return the script needed to execute the groth16_verifier script.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the groth16_verifier script.
            max_multipliers (list[int] | None): The integer n such that |pub[i]| <= n for all i. If passed as
                None, then n = groth16_model.r.
            load_modulus (bool): Whether or not to load the modulus. Defaults to `True`.
        """
        out = nums_to_script([groth16_model.pairing_model.modulus]) if load_modulus else Script()

        # Load inverse_miller_output inverse
        out += nums_to_script(self.inverse_miller_output)

        # Load A, B, C
        out += nums_to_script(self.A)
        out += nums_to_script(self.B)
        out += nums_to_script(self.C)

        # Load precomputed msm
        out += nums_to_script(self.precomputed_msm)

        return out
