"""Opening key for Pedersen commitment scheme."""

from dataclasses import dataclass

from tx_engine import Script, encode_num
from tx_engine.engine.util import GROUP_ORDER_INT, PRIME_INT, Gx, Gx_bytes

from src.zkscript.types.unlocking_keys.secp256k1 import Secp256k1PointMultiplicationUnlockingKey
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class PedersenCommitmentSecp256k1UnlockingKey:
    """Class encapsulating the data required to open a Pedersen commitment.

    The commitment is purportedly of the form: Q + R, where Q = mG, R = rH.

    Attributes:
        sig_hash_preimage (bytes): The preimage of the sighash of the transaction in which the unlocking
            script is used.
        h (bytes): The sighash of the transaction in which the unlocking script is used.
        gradients (int): The gradient through `Q` and `R`.
        base_point_opening_data (Secp256k1PointMultiplicationUnlockingKey): The unlocking key needed to execute
            the method `Secp256k1.verify_point_multiplication` to prove Q = mG.
        randomness_opening_data (Secp256k1PointMultiplicationUnlockingKey): The unlocking key needed to execute
            the method `Secp256k1.verify_point_multiplication` to prove R = rH.
    """

    sig_hash_preimage: bytes
    h: bytes
    gradient: int
    base_point_opening_data: Secp256k1PointMultiplicationUnlockingKey
    randomness_opening_data: Secp256k1PointMultiplicationUnlockingKey

    def __post_init__(self):
        """Post initilisation checks."""
        assert self.base_point_opening_data.sig_hash_preimage == b""
        assert self.base_point_opening_data.h == b""
        assert self.randomness_opening_data.sig_hash_preimage == b""
        assert self.randomness_opening_data.h == b""

    def to_unlocking_script(self, append_constants: bool = True) -> Script:
        """Generate the unlocking script for the commitment Commit(m,r) = mG + rH.

        Args:
            append_constants (bool): If `True`, the constants needed to execute the method
                PedersenCommitmentSecp256k1.commit are appended at the beginning of the unlocking
                script.
        """
        out = Script()

        if append_constants:
            out += nums_to_script([GROUP_ORDER_INT, Gx])
            out.append_pushdata(bytes.fromhex("0220") + Gx_bytes + bytes.fromhex("02"))
            out += nums_to_script([PRIME_INT])

        out.append_pushdata(self.sig_hash_preimage)
        out.append_pushdata(encode_num(int.from_bytes(self.h)))
        out += nums_to_script([self.gradient])
        out += self.base_point_opening_data.to_unlocking_script(append_constants=False)
        out += self.randomness_opening_data.to_unlocking_script(append_constants=False)

        return out
