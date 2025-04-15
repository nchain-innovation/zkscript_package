"""Unlocking keys for Miller loops."""

from dataclasses import dataclass

from tx_engine import Script

from src.zkscript.bilinear_pairings.model.model_definition import PairingModel
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class MillerLoopUnlockingKey:
    """Class encapsulating the data required to generate an unlocking script for the Miller loop.

    Attributes:
        P (list[int]): The point P for which the script computes miller(P,Q)
        Q (list[int]): The point Q for which the script computes miller(P,Q)
        gradients (list[list[list[int]]]): The list of gradients required to compute w * Q, where
            w is the integer defining the Miller function f_w s.t. miller(P,Q) = f_{w,Q}(P)
    """

    P: list[int]
    Q: list[int]
    gradients: list[list[list[int]]]

    def to_unlocking_script(self, pairing_model: PairingModel) -> Script:
        """Return the unlocking script required to execute the `pairing_model.miller_loop` method.

        Args:
            pairing_model (PairingModel): The pairing model over which the Miller loop is computed.

        Returns:
            Script pushing [self.gradients, self.P, self.Q] on the stack.
        """
        out = nums_to_script([pairing_model.modulus])
        for i in range(len(self.gradients) - 1, -1, -1):
            for j in range(len(self.gradients[i]) - 1, -1, -1):
                out += nums_to_script(self.gradients[i][j])

        out += nums_to_script(self.P)
        out += nums_to_script(self.Q)

        return out


@dataclass
class TripleMillerLoopUnlockingKey:
    r"""Class encapsulating the data required to generate an unlocking script for the triple Miller loop.

    Attributes:
        P (list[list[int]]): The points P for which the script computes \prod_i miller(P[i],Q[i])
        Q (list[list[int]]): The points Q for which the script computes \prod_i miller(P[i],Q[i])
        gradients (list[list[list[list[int]]]]): The list of gradients required to compute w * Q[i], where
            w is the integer defining the Miller function f_w s.t. miller(P[i],Q[i]) = f_{w,Q[i]}(P[i]),
            gradients[i] is the list of gradients needed to compute w*Q[i].
    """

    P: list[list[int]]
    Q: list[list[int]]
    gradients: list[list[list[list[int]]]]

    def to_unlocking_script(self, pairing_model: PairingModel) -> Script:
        """Return the unlocking script required to execute the `pairing_model.triple_miller_loop` method.

        Args:
            pairing_model (PairingModel): The pairing model over which the Miller loop is computed.

        Returns:
            Script pushing [self.gradients, self.P, self.Q] on the stack.
        """
        out = nums_to_script([pairing_model.modulus])
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
