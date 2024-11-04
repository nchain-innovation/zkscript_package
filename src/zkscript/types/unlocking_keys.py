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
