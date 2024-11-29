"""Unlocking key for Groth16."""

from dataclasses import dataclass

from tx_engine import Script

from src.zkscript.groth16.model.groth16 import Groth16
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class Groth16UnlockingKey:
    r"""Class encapsulating the data required to generate an unlocking script for a Groth16 verifier.

    Attributes:
        pub (list[int]): list of public statements (extended with).
        A (list[int]): Component of the zk proof.
        B (list[int]): Component of the zk proof.
        C (list[int]): Component of the zk proof.
        gradients_pairings (list[list[list[list[int]]]]): list of gradients required to compute the pairings
            in the Groth16 verification equation. The meaning of the lists is:
                - gradients_pairings[0]: gradients required to compute w*B
                - gradients_pairings[1]: gradients required to compute w*(-gamma)
                - gradients_pairings[2]: gradients required to compute w*(-delta)
        inverse_miller_loop (list[int]): the inverse of
            miller(A,B) * miller(gamma_abc[0] + \sum_{i >=0} pub[i-1] * gamma_abc[i], -gamma) * miller(C, -delta)
        gradients_partial_sums (list[list[list[list[int]]]]): gradients_partial_sums[n_pub - i - 1] is the gradient
            required to compute the sum
                (gamma_abc[0] + \sum_{j=1}^{i} pub[j-1] gamma_abc[j]) + (pub[i] * gamma_abc[i+1])
            where 0 <= i <= n_pub-1
        gradients_multiplication (list[list[list[list[int]]]]): gradients_multiplication[i] is the list of
            gradients required to compute pub[i] * gamma_abc[i+1], 0 <= i <= n_pub-1
    """

    pub: list[int]
    A: list[int]
    B: list[int]
    C: list[int]
    gradients_pairings: list[list[list[list[int]]]]
    inverse_miller_output: list[int]
    gradients_partial_sums: list[list[list[list[int]]]]
    gradients_multiplication: list[list[list[list[int]]]]

    def to_unlocking_script(
        self,
        groth16_model: Groth16,
        max_multipliers: list[int] | None = None,
        load_modulus: bool = True,
    ) -> Script:
        r"""Return the script needed to execute the groth16_verifier script.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the groth16_verifier script.
            max_multipliers (list[int] | None): The integer n such that |pub[i]| <= n for all i. If passed as
                None, then n = groth16_model.r.
            load_modulus (bool): Whether or not to load the modulus. Defaults to `True`.
        """
        n_pub = len(self.pub)

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

        # Partial sums
        for i in range(n_pub):
            out += nums_to_script(self.gradients_partial_sums[i])

        # Multiplications pub[i] * gamma_abc[i+1]
        for i in range(n_pub):
            M = groth16_model.r.bit_length() - 1 if max_multipliers is None else max_multipliers[i].bit_length() - 1

            if self.pub[i] == 0:
                out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * M))
            else:
                # Binary expansion of pub[i]
                exp_pub_i = [int(bin(self.pub[i])[j]) for j in range(2, len(bin(self.pub[i])))][::-1]

                N = len(exp_pub_i) - 1

                # Marker marker_a_equal_zero
                out += Script.parse_string("OP_0")

                # Load the lambdas and the markers
                for j in range(len(self.gradients_multiplication[i]) - 1, -1, -1):
                    if exp_pub_i[-j - 2] == 1:
                        out += nums_to_script(self.gradients_multiplication[i][j][1]) + Script.parse_string("OP_1")
                        out += nums_to_script(self.gradients_multiplication[i][j][0]) + Script.parse_string("OP_1")
                    else:
                        out += (
                            Script.parse_string("OP_0")
                            + nums_to_script(self.gradients_multiplication[i][j][0])
                            + Script.parse_string("OP_1")
                        )
                out += Script.parse_string(" ".join(["OP_0"] * (M - N)))

        return out
