"""Groth16 locking key."""

from dataclasses import dataclass


@dataclass
class Groth16LockingKey:
    """Groth16 locking key."""

    alpha_beta: list[int]
    minus_gamma: list[int]
    minus_delta: list[int]
    gamma_abc: list[list[int]]
    r"""
    Class encapsulating the data required to generate a locking script for a Groth16 verifier.

    Attributes:
        alpha_beta (list[int]): List of integers representing the alpha and beta coefficients for the computation.
            minus_gamma (list[int]): List of integers representing the negated gamma values for the computation.
            minus_delta (list[int]): List of integers representing the negated delta values for the computation
            gamma_abc (list[list[int]]): List of points given in the Common Reference String for which the verifier
                must compute
                    gamma_abc[0] + \sum_{i >= 1} pub[i-1] * gamma_abc[i]
                where pub[i] is is i-th public statement.
    """
