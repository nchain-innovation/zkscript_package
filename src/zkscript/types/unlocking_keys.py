from dataclasses import dataclass
from typing import List


@dataclass
class MillerLoopUnlockingKey:
    P: List[int]
    Q: List[int]
    gradients: List[List[int]]

    """
    Class encapsulating the data required to generate an unlocking script for the Miller loop.

    Args:
        P (List[int]): The point P for which the script computes miller(P,Q)
        Q (List[int]): The point Q for which the script computes miller(P,Q)
        gradients (List[List[int]]): The list of gradients required to compute w * Q, where
            w is the integer defining the Miller function f_w s.t. miller(P,Q) = f_{w,Q}(P)
    """


@dataclass
class TripleMillerLoopUnlockingKey:
    P: List[List[int]]
    Q: List[List[int]]
    gradients: List[List[List[int]]]

    r"""
    Class encapsulating the data required to generate an unlocking script for the triple Miller loop.

    Args:
        P (List[List[int]]): The points P for which the script computes \prod_i miller(Pi,Qi)
        Q (List[List[int]]): The points Q for which the script computes \prod_i miller(Pi,Qi)
        gradients (List[List[List[int]]]): The list of gradients required to compute w * Qi, where
            w is the integer defining the Miller function f_w s.t. miller(Pi,Qi) = f_{w,Qi}(Pi)
    """


@dataclass
class SinglePairingUnlockingKey:
    P: List[int] | None
    Q: List[int] | None
    gradients: List[List[int]] | None
    inverse_miller_output: List[int] | None

    r"""
    Class encapsulating the data required to generate an unlocking script for the calculation of a single pairing.

    Args:
        P (List[int] | None): the point P over which to compute the pairing. If P is the point
            at infinity, it is passed as None.
        Q (List[int] | None): the point Q over which to compute the pairing. If Q is the point
            at infinity, it is passed as None.
        gradients (List[List[int]] | None): the gradients needed to compute w*Q. If Q is the point
            at infinity, it is passed as None.
        inverse_miller_loop (List[int]): the inverse of miller(P,Q). If P or Q are the point at
            at infinity, it is passed as None.
    """


@dataclass
class TriplePairingUnlockingKey:
    P: List[List[int]]
    Q: List[List[int]]
    gradients: List[List[List[int]]]
    inverse_miller_output: List[int] | None

    r"""
    Class encapsulating the data required to generate an unlocking script for the calculation of a triple pairing.

    Args:
        P (List[List[int]]): The points P for which the script computes \prod_i pairing(Pi,Qi)
        Q (List[List[int]]): The points Q for which the script computes \prod_i pairing(Pi,Qi)
        gradients (List[List[List[int]]]): The list of gradients required to compute w * Qi, where
            w is the integer defining the Miller function f_w s.t. miller(Pi,Qi) = f_{w,Qi}(Pi)
        inverse_miller_loop (List[int]): the inverse of \prod_i miller(Pi,Qi).
    """
