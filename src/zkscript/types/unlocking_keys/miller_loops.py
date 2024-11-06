from dataclasses import dataclass
from typing import List

from tx_engine import Script

from src.zkscript.bilinear_pairings.model.model_definition import PairingModel
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class MillerLoopUnlockingKey:
    P: List[int]
    Q: List[int]
    gradients: List[List[int]]
    """
    Class encapsulating the data required to generate an unlocking script for the Miller loop.

    Attributes:
        P (List[int]): The point P for which the script computes miller(P,Q)
        Q (List[int]): The point Q for which the script computes miller(P,Q)
        gradients (List[List[int]]): The list of gradients required to compute w * Q, where
            w is the integer defining the Miller function f_w s.t. miller(P,Q) = f_{w,Q}(P)
    """

    def to_unlocking_script(self, pairing_model: PairingModel) -> Script:
        """Return the unlocking script required by the miller_loop script.

        Args:
            pairing_model (PairingModel): The pairing model over which the Miller loop is computed.

        """
        out = nums_to_script([pairing_model.MODULUS])
        for i in range(len(self.gradients) - 1, -1, -1):
            for j in range(len(self.gradients[i]) - 1, -1, -1):
                out += nums_to_script(self.gradients[i][j])

        out += nums_to_script(self.P)
        out += nums_to_script(self.Q)

        return out


@dataclass
class TripleMillerLoopUnlockingKey:
    P: List[List[int]]
    Q: List[List[int]]
    gradients: List[List[List[int]]]
    r"""
    Class encapsulating the data required to generate an unlocking script for the triple Miller loop.

    Attributes:
        P (List[List[int]]): The points P for which the script computes \prod_i miller(P[i],Q[i])
        Q (List[List[int]]): The points Q for which the script computes \prod_i miller(P[i],Q[i])
        gradients (List[List[List[int]]]): The list of gradients required to compute w * Q[i], where
            w is the integer defining the Miller function f_w s.t. miller(P[i],Q[i]) = f_{w,Q[i]}(P[i]),
            gradients[i] is the list of gradients needed to compute w*Q[i].
    """

    def to_unlocking_script(self, pairing_model: PairingModel) -> Script:
        """Return the unlocking script required by the triple_miller_loop script.

        Args:
            pairing_model (PairingModel): The pairing model over which the Miller loop is computed.

        """

        out = nums_to_script([pairing_model.MODULUS])
        # Load gradients
        for i in range(len(self.gradients[0]) - 1, -1, -1):
            for j in range(len(self.gradients[0][i]) - 1, -1, -1):
                for k in range(3):
                    out += nums_to_script(self.gradients[k][i][j])

        for i in range(3):
            out += nums_to_script(self.P[i])
        for i in range(3):
            out += nums_to_script(self.Q[i])

        return out
