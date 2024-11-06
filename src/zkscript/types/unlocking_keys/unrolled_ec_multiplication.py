from dataclasses import dataclass
from math import log2
from typing import List

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq_unrolled import EllipticCurveFqUnrolled
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class EllipticCurveFqUnrolledUnlockingKey:
    P: List[int]
    a: int
    gradients: List[List[int]] | None
    max_multiplier: int
    """
    Class encapsulating the data required to generate an unlocking script for unrolled_multiplication.

    Attributes:
        P (List[int]): The point P for which the script computes a*P
        a (int): The multiplier for which the script computes a*P
        gradients (List[List[int]] | None): The list of gradients required to compute a*P, computed according
            to the following algorithm:
                gradients = []
                for i in range(len(bin(a)[2:])-2,-1,-1):
                    to_add = []
                    to_add.append(gradient of line tangent at T)
                    T = T + T
                    if bin(a)[2:][i] == 1:
                        to_add.append(gradient of line through T and P)
                    gradients.append(to_add)
            If a = 0, it is passed as None.
        max_multiplier (int): The max multiplier n for which unrolled_multiplication can compute n*P
    """

    def to_unlocking_script(self, unrolled_ec_over_fq: EllipticCurveFqUnrolled, load_modulus=True) -> Script:
        """Return the unlocking script required by unrolled_multiplication script.

        Args:
            unrolled_ec_over_fq (EllipticCurveFqUnrolled): The instantiation of unrolled ec arithmetic
                over Fq used to construct the unrolled_multiplication locking script.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.

        """
        M = int(log2(self.max_multiplier))

        out = nums_to_script([unrolled_ec_over_fq.MODULUS]) if load_modulus else Script()

        # Add the gradients
        if self.a == 0:
            out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * M))
        else:
            exp_a = [int(bin(self.a)[j]) for j in range(2, len(bin(self.a)))][::-1]

            N = len(exp_a) - 1

            # Marker marker_a_equal_zero
            out += Script.parse_string("OP_0")

            # Load the gradients and the markers
            for j in range(len(self.gradients) - 1, -1, -1):
                if exp_a[-j - 2] == 1:
                    out += nums_to_script(self.gradients[j][1]) + Script.parse_string("OP_1")
                    out += nums_to_script(self.gradients[j][0]) + Script.parse_string("OP_1")
                else:
                    out += Script.parse_string("OP_0")
                    out += nums_to_script(self.gradients[j][0])
                    out += Script.parse_string("OP_1")
            out += Script.parse_string(" ".join(["OP_0"] * (M - N)))

        # Load P
        out += nums_to_script(self.P)

        return out
