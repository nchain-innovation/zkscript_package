from dataclasses import dataclass
from typing import List


@dataclass
class Groth16LockingKey:
    alpha_beta: List[int]
    minus_gamma: List[int]
    minus_delta: List[int]
    gamma_abc: List[List[int]]
    r"""
    Class encapsulating the data required to generate a locking script for a Groth16 verifier.

    Attributes:
        alpha_beta (List[int]): The value of the pairing pairing(alpha,beta)
        minus_gamma (List[int]): The point -gamma from the CRS.
        minus_delta (List[int]): The point -delts from the CRS.
        gamma_abc (List[List[int]]): The points from the CRS for which the verifier must compute
                gamma_abc[0] + \sum_{i >= 1} pub[i-1] * gamma_abc[i]
            where pub[i] is is i-th public statement.
    """
