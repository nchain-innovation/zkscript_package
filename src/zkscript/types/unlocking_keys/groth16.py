"""Unlocking keys for Groth16."""

from dataclasses import dataclass
from typing import Self

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.groth16.model.groth16 import Groth16
from src.zkscript.types.unlocking_keys.msm_with_fixed_bases import MsmWithFixedBasesUnlockingKey
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class Groth16UnlockingKey:
    r"""Class encapsulating the data required to generate an unlocking script for a Groth16 verifier.

    Attributes:
        pub (list[int]): list of public statements.
        A (list[int]): Component of the zk proof.
        B (list[int]): Component of the zk proof.
        C (list[int]): Component of the zk proof.
        gradients_pairings (list[list[list[list[int]]]]): list of gradients required to compute the pairings
            in the Groth16 verification equation. The meaning of the lists is:
                - gradients_pairings[0]: gradients required to compute w*B
                - gradients_pairings[1]: gradients required to compute w*(-gamma)
                - gradients_pairings[2]: gradients required to compute w*(-delta)
        inverse_miller_output (list[int]): the inverse of
            miller(A,B) * miller(gamma_abc[0] + \sum_{i >=0} pub[i] * gamma_abc[i+1], -gamma) * miller(C, -delta)
        msm_key (MsmWithFixedBasesUnlockingKey): Unlocking key required to compute the msm
            \sum_(i=1)^l pub[i] * gamma_abc[i+1]
        gradient_gamma_abc_zero (list[int]): The gradient required to compute the sum
            gamma_abc[0] + \sum_(i=1)^l pub[i] * gamma_abc[i+1]
    """

    pub: list[int]
    A: list[int]
    B: list[int]
    C: list[int]
    gradients_pairings: list[list[list[list[int]]]]
    inverse_miller_output: list[int]
    msm_key: MsmWithFixedBasesUnlockingKey
    gradient_gamma_abc_zero: list[int]

    @staticmethod
    def from_data(
        groth16_model: Groth16,
        pub: list[int],
        A: list[int],  # noqa: N803
        B: list[int],  # noqa: N803
        C: list[int],  # noqa: N803
        gradients_pairings: list[list[list[list[int]]]],
        gradients_multiplications: list[list[list[list[int]]]],
        max_multipliers: list[int] | None,
        gradients_additions: list[list[int]],
        inverse_miller_output: list[int],
        gradient_gamma_abc_zero: list[int],
    ) -> Self:
        r"""Construct an instance of `Self` from the provided data.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the groth16_verifier script.
            pub (list[int]): The list of public statements.
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
                multiplication of gamma_abc[i]
            gradients_additions (list[int]): `gradients_additions[i]` is the gradient of the addition
                `gamma_abc[n-i-2] + (\sum_(j=n-i-1)^(n-1) gamma_abc[j]`
            inverse_miller_output (list[int]): the inverse of
                miller(A,B) * miller(gamma_abc[0] + \sum_{i >=0} pub[i] * gamma_abc[i+1], -gamma) * miller(C, -delta)
            gradient_gamma_abc_zero (list[int]): The gradient required to compute the sum
                gamma_abc[0] + \sum_(i=1)^l pub[i] * gamma_abc[i+1]
        """
        max_multipliers = max_multipliers if max_multipliers is not None else [groth16_model.r] * len(pub)
        msm_key = MsmWithFixedBasesUnlockingKey.from_data(
            scalars=pub,
            gradients_multiplications=gradients_multiplications,
            max_multipliers=max_multipliers,
            gradients_additions=gradients_additions,
        )

        return Groth16UnlockingKey(
            pub,
            A,
            B,
            C,
            gradients_pairings,
            inverse_miller_output,
            msm_key,
            gradient_gamma_abc_zero,
        )

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
        ec_fq = EllipticCurveFq(groth16_model.pairing_model.MODULUS, groth16_model.curve_a)

        out = nums_to_script([groth16_model.pairing_model.MODULUS]) if load_modulus else Script()

        # Load inverse_miller_output inverse
        out += nums_to_script(self.inverse_miller_output)

        # Load gradients_pairings
        for i in range(len(self.gradients_pairings[0]) - 1, -1, -1):
            for j in range(len(self.gradients_pairings[0][i]) - 1, -1, -1):
                for k in range(3):
                    out += nums_to_script(self.gradients_pairings[k][i][j])

        # Load A, B, C
        out += nums_to_script(self.A)
        out += nums_to_script(self.B)
        out += nums_to_script(self.C)

        # Sum w/ gamma_abc
        out += nums_to_script(self.gradient_gamma_abc_zero)

        # MSM
        out += self.msm_key.to_unlocking_script(
            ec_over_fq=ec_fq,
            load_modulus=False,
        )

        return out


@dataclass
class Groth16UnlockingKeyWithPrecomputedMsm:
    r"""Class encapsulating the data required to generate unlocking script for Groth16 verifier with precomputed msm.

    Attributes:
        A (list[int]): Component of the zk proof.
        B (list[int]): Component of the zk proof.
        C (list[int]): Component of the zk proof.
        gradients_pairings (list[list[list[list[int]]]]): list of gradients required to compute the pairings
            in the Groth16 verification equation. The meaning of the lists is:
                - gradients_pairings[0]: gradients required to compute w*B
                - gradients_pairings[1]: gradients required to compute w*(-gamma)
                - gradients_pairings[2]: gradients required to compute w*(-delta)
        inverse_miller_output (list[int]): the inverse of
            miller(A,B) * miller(gamma_abc[0] + \sum_{i >=0} pub[i] * gamma_abc[i+1], -gamma) * miller(C, -delta)
        precomputed_msm: the sum \sum_(i=0)^l a_i * gamma_abc[i]
    """

    A: list[int]
    B: list[int]
    C: list[int]
    gradients_pairings: list[list[list[list[int]]]]
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
        out = nums_to_script([groth16_model.pairing_model.MODULUS]) if load_modulus else Script()

        # Load inverse_miller_output inverse
        out += nums_to_script(self.inverse_miller_output)

        # Load gradients_pairings
        for i in range(len(self.gradients_pairings[0]) - 1, -1, -1):
            for j in range(len(self.gradients_pairings[0][i]) - 1, -1, -1):
                for k in range(3):
                    out += nums_to_script(self.gradients_pairings[k][i][j])

        # Load A, B, C
        out += nums_to_script(self.A)
        out += nums_to_script(self.B)
        out += nums_to_script(self.C)

        # Load precomputed msm
        out += nums_to_script(self.precomputed_msm)

        return out
