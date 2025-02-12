"""Groth16 locking keys."""

from dataclasses import dataclass


@dataclass
class Groth16LockingKey:
    r"""Class encapsulating the data required to generate a locking script for a Groth16 verifier.

    Attributes:
        alpha_beta (list[int]): List of integers representing the alpha and beta coefficients for the computation.
        minus_gamma (list[int]): List of integers representing the negated gamma values for the computation.
        minus_delta (list[int]): List of integers representing the negated delta values for the computation
        gamma_abc (list[list[int]]): List of points given in the Common Reference String for which the verifier
            must compute
                gamma_abc[0] + \sum_{i >= 1} pub[i-1] * gamma_abc[i]
            where pub[i] is is i-th public statement.
        gradients_pairings (list[list[list[list[int]]]]): list of gradients required to compute the pairings
            in the Groth16 verification equation. The meaning of the lists is:
                - gradients_pairings[0]: gradients required to compute w*(-gamma)
                - gradients_pairings[1]: gradients required to compute w*(-delta)
    """

    alpha_beta: list[int]
    minus_gamma: list[int]
    minus_delta: list[int]
    gamma_abc: list[list[int]]
    gradients_pairings: list[list[list[list[int]]]]


@dataclass
class Groth16LockingKeyWithPrecomputedMsm:
    r"""Class encapsulating the data required to generate a locking script for a Groth16 verifier with precomputed msm.

    Attributes:
        alpha_beta (list[int]): List of integers representing the alpha and beta coefficients for the computation.
        minus_gamma (list[int]): List of integers representing the negated gamma values for the computation.
        minus_delta (list[int]): List of integers representing the negated delta values for the computation
        gradients_pairings (list[list[list[list[int]]]]): list of gradients required to compute the pairings
            in the Groth16 verification equation. The meaning of the lists is:
                - gradients_pairings[0]: gradients required to compute w*(-gamma)
                - gradients_pairings[1]: gradients required to compute w*(-delta)
    """

    alpha_beta: list[int]
    minus_gamma: list[int]
    minus_delta: list[int]
    gradients_pairings: list[list[list[list[int]]]]
