"""Export size estimate function for MNT4-753."""

from math import ceil, log2
from typing import Union

from src.zkscript.util.utility_functions import base_function_size_estimation_miller_loop

r"""
P + Q:
    x_(P+Q) = gradient^2 - x_P - x_Q
    y_(P+Q) = gradient * (x_(P+Q) - x_P)
If gradient, x_P, y_P \in F_q then the worst calculation for P+Q is:
    |y_(P+Q)| <= |gradient| * max(|x_(P+Q)|,|x_P|) <= |gradient| * 2 * |x_(P+Q)| <= 6 * |gradient| * |x_Q|

f <-- f^2:
    f = a + b r, r^2 = s
    f^2 = (a^2 + b^2s) + 2ab r
Worst calculation is: b^2v: |f^2| <= 2|b^2s|
    b = b_0 + b_1 s
    b^2 = (b_0^2 + b_1^2 13) + 2b_0b_1 s
Worst calculation is: (b_0^2 + b_1^2 13), 2|b^2s| <= 52 |b_1^2|
Finally: |f^2| <= 52 |b_1^2|

f <-- f^2 * element
    |f^2 * element| <= 52 |bit_size(f^2)| * |bit_size(element)| <= 52^2 * |bit_size(f)|^2 * |bit_size(element)|
"""


def size_estimation_miller_loop(
    modulus,
    modulo_threshold: int,
    ix: int,
    exp_miller_loop: list[int],
    current_size_miller_output: int,
    current_size_point_multiplication: int,
    is_triple_miller_loop: bool,
) -> Union[bool, int]:
    """Estimate size of elements computed while executing the Miller loop.

    Args:
        modulus (int): the modulus of MNT4-753
        modulo_threshold (int): the size after which to take a modulo in the script (in bytes).
        ix (int): the index of the Miller loop.
        exp_miller_loop (list[int]): the binary expansion of the value for which the Miller loop is computed.
        current_size_miller_output (int): the current size of the Miller output.
        current_size_point_multiplication (int): the current size of the calculation of w*Q, where w is the
            value over which the Miller loop is computed.
        is_triple_miller_loop (bool): whether the function is used to estimate the sizes for the triple Miller
            loop or a single one.

    Returns:
        take_modulo_miller_loop_output (bool): whether to take a modulo after the update of the Miller loop
            output.
        take_modulo_point_multiplication (bool): whether to take a modulo after the update of the intermediate
            value of w*Q.
        out_size_miller_loop (int): the new size of the Miller loop output (in bytes).
        out_size_point_miller_loop (int): the new size of the intermediate value of w*Q (in bytes).
    """
    return base_function_size_estimation_miller_loop(
        modulus=modulus,
        modulo_threshold=modulo_threshold,
        ix=ix,
        n=ceil(log2(52)),
        exp_miller_loop=exp_miller_loop,
        current_size_miller_output=current_size_miller_output,
        current_size_point_multiplication=current_size_point_multiplication,
        is_triple_miller_loop=is_triple_miller_loop,
    )
