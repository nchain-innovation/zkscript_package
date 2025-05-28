"""Unlocking keys for Pairings."""

from dataclasses import dataclass

from tx_engine import Script

from src.zkscript.bilinear_pairings.model.model_definition import PairingModel
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class SinglePairingUnlockingKey:
    """Class encapsulating the data required to generate an unlocking script for the calculation of a single pairing.

    Attributes:
        P (list[int] | None): the point P over which to compute the pairing. If P is the point
            at infinity, it is passed as None.
        Q (list[int] | None): the point Q over which to compute the pairing. If Q is the point
            at infinity, it is passed as None.
        gradients (list[list[list[int]]] | None): the gradients needed to compute w*Q. If Q is the point
            at infinity, it is passed as None.
        inverse_miller_loop (list[int]): the inverse of miller(P,Q). If P or Q are the point at
            at infinity, it is passed as None.
    """

    P: list[int] | None
    Q: list[int] | None
    gradients: list[list[list[int]]] | None
    inverse_miller_output: list[int] | None

    def to_unlocking_script(self, pairing_model: PairingModel, load_modulus: bool = True) -> Script:
        """Returns a script containing the data required to execute the `pairing_model.single_pairing` method.

        Args:
            pairing_model (PairingModel): The pairing model over which the Miller loop is computed.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.

        Returns:
            Script pushing [miller(P,Q)^-1, self.gradients, self.P, self.Q] on the stack.
        """
        out = nums_to_script([pairing_model.modulus]) if load_modulus else Script()

        # P is infinity, Q is not
        if self.P is None and self.Q is not None:
            out += Script.parse_string(" ".join(["0x00"] * pairing_model.N_POINTS_CURVE))
            out += nums_to_script(self.Q)
        # Q is infinity, P is not
        elif self.P is not None and self.Q is None:
            out += nums_to_script(self.P)
            out += Script.parse_string(" ".join(["0x00"] * pairing_model.N_POINTS_TWIST))
        # Both P and Q are infinity
        elif self.P is None and self.Q is None:
            out += Script.parse_string(
                " ".join(["0x00"] * (pairing_model.N_POINTS_TWIST + pairing_model.N_POINTS_CURVE))
            )
        # Neither P or Q is infinity
        else:
            # Load inverse of output of Miller loop
            out += nums_to_script(self.inverse_miller_output)

            # Load the gradients
            for i in range(len(self.gradients) - 1, -1, -1):
                for j in range(len(self.gradients[i]) - 1, -1, -1):
                    out += nums_to_script(self.gradients[i][j])

            # Load P and Q
            out += nums_to_script(self.P)
            out += nums_to_script(self.Q)

        return out


@dataclass
class TriplePairingUnlockingKey:
    r"""Class encapsulating the data required to generate an unlocking script for the calculation of a triple pairing.

    Attributes:
        P (list[list[int]]): The points P for which the script computes \prod_i pairing(P[i],Q[i])
        Q (list[list[int]]): The points Q for which the script computes \prod_i pairing(P[i],Q[i])
        gradients (list[list[list[list[int]]]]): The list of gradients required to compute w * Q[i], where
            w is the integer defining the Miller function f_w s.t. miller(P[i],Q[i]) = f_{w,Q[i]}(P[i]),
            gradients[i] is the list of gradients needed to compute w*Q[i]
        inverse_miller_loop (list[int]): the inverse of \prod_i miller(P[i],Q[i]).
        has_precomputed_gradients (bool): Whether the precomputed gradients are in the unloking key.

    """

    P: list[list[int]]
    Q: list[list[int]]
    gradients: list[list[list[list[int]]]]
    inverse_miller_output: list[int] | None
    has_precomputed_gradients: bool = True

    def to_unlocking_script(self, pairing_model: PairingModel, load_modulus: bool = True) -> Script:
        """Returns a script containing the data required to execute the `pairing_model.single_pairing` method.

        Args:
            pairing_model (PairingModel): The pairing model over which the Miller loop is computed.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.

        Returns:
            Script pushing [miller(P,Q)^-1, self.gradients, self.P, self.Q] on the stack.
        """
        out = nums_to_script([pairing_model.modulus]) if load_modulus else Script()

        # Load inverse_miller_output inverse
        out += nums_to_script(self.inverse_miller_output)

        # Load gradients
        for i in range(len(self.gradients[0]) - 1, -1, -1):
            for j in range(len(self.gradients[0][i]) - 1, -1, -1):
                if self.has_precomputed_gradients:
                    for k in range(3):
                        out += nums_to_script(self.gradients[k][i][j])
                else:
                    out += nums_to_script(self.gradients[0][i][j])

        for i in range(3):
            out += nums_to_script(self.P[i])
        for i in range(3):
            out += nums_to_script(self.Q[i])

        return out
