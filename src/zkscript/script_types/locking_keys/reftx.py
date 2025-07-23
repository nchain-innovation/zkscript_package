"""RefTx locking key."""

from dataclasses import dataclass

from tx_engine import SIGHASH

from src.zkscript.script_types.locking_keys.groth16 import Groth16LockingKey
from src.zkscript.script_types.locking_keys.groth16_proj import Groth16ProjLockingKey


@dataclass
class RefTxLockingKey:
    r"""Class encapsulating the data required to generate a locking script for RefTx.

    RefTx is a circuit C' that enforces arbitrary conditions (specified by a circuit C) on the spending transaction.
    The circuit C looks as follows:
        C(l_out, u_stx, s_stx)
    where `l_out` is fixed in the locking script, and `u_stx` is specified by the spender.
    The circuit C' encapsulates C, and looks as follows:
        C'(l_out, sighash(stx), u_stx)
    Let vk' be the verification key of C'. As l_out is known at the point of script construction, the msm for
    l_out and vk'.gamma_abc[0] can be precomputed. Let us write vk'' for the verification key defined as follows:
        - vk''.alpha_beta = vk'.alpha_beta
        - vk''.minus_gamma = vk'.minus_gamma
        - vk''.minus_delta = vk'.minus_delta
        - vk''.gamma_abc = [precomputed_l_out, vk'.gamma_abc[n_l_out + 1:]]
    where n_l_out is the number of public inputs pertaining to l_out, and precomputed_lout is the sum
        gamma_abc[0] + \sum_{i=0}^{n_l_out-1} pub[i] * gamma_abc[i+1]
    where pub[i] is the i-th public input.

    The values of `alpha`, `beta`, `gamma`, `delta`, and `gamma_abc` below refer to the verification key vk''.

    Attributes:
        alpha_beta (list[int]): List of integers representing the evaluation of the pairing on (alpha, beta).
        minus_gamma (list[int]): List of integers representing the negated gamma values for the computation.
        minus_delta (list[int]): List of integers representing the negated delta values for the computation.
        precomputed_l_out (list[int]): List of integers representing the precomputed value:
                gamma_abc[0] + \sum_{i=0}^{n_l_out-1} pub[i] * gamma_abc[i+1]
        gamma_abc_without_l_out (list[list[int]]): The subset of the vk'.gamma_abc[n_l_out + 1:].
        gradients_pairings (list[list[list[list[int]]]]): list of gradients required to compute the pairings
            in the Groth16 verification equation. The meaning of the lists is:
                - gradients_pairings[0]: gradients required to compute w*(-gamma)
                - gradients_pairings[1]: gradients required to compute w*(-delta)
        has_precomputed_gradients (bool): Flag indicating whether the precomputed gradients are injected in the locking
            script. Defaults to `False`, meaning that the precomputed gradientes are passed in the unlocking script.
        use_proj_coordinates (bool): Flag indicating whether the groth16 algorithm uses projective coordinates.
    """

    alpha_beta: list[int]
    minus_gamma: list[int]
    minus_delta: list[int]
    precomputed_l_out: list[int]
    gamma_abc_without_l_out: list[list[int]]
    gradients_pairings: list[list[list[list[int]]]] | None
    sighash_flags: SIGHASH
    has_precomputed_gradients: bool = False
    use_proj_coordinates: bool = False

    def to_groth16_key(self) -> Groth16LockingKey | Groth16ProjLockingKey:
        """Turn the RefTxLockingKey into a Groth16LockingKey or Groth16ProjLockingKey."""
        if self.use_proj_coordinates:
            return Groth16ProjLockingKey(
                alpha_beta=self.alpha_beta,
                minus_gamma=self.minus_gamma,
                minus_delta=self.minus_delta,
                gamma_abc=[self.precomputed_l_out, *self.gamma_abc_without_l_out],
            )
        return Groth16LockingKey(
            alpha_beta=self.alpha_beta,
            minus_gamma=self.minus_gamma,
            minus_delta=self.minus_delta,
            gamma_abc=[self.precomputed_l_out, *self.gamma_abc_without_l_out],
            gradients_pairings=self.gradients_pairings,
            has_precomputed_gradients=self.has_precomputed_gradients,
        )
