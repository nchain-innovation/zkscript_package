"""Unlocking keys for transaction introspection."""

from dataclasses import dataclass
from typing import Union

from tx_engine import SIGHASH, Script, Tx, hash256d
from tx_engine import sig_hash_preimage as tx_to_sig_hash_preimage
from tx_engine.engine.util import GROUP_ORDER_INT, Gx, Gx_bytes

from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class PushTxUnlockingKey:
    """Class encapsulating the data required for unlocking PUSHTX.

    Attributes:
        tx (Tx): The transaction for which we want to construct the unlocking script.
        index (int): The index of the UTXO for which we want to construct the unlocking script.
        script_pubkey (Script): The script_pubkey of the outpoint we want to construct the unlocking
            script for.
        prev_amount (int): The amount of the outpoint we want to construct the unlocking
            script for.
    """

    tx: Tx
    index: int
    script_pubkey: Script
    prev_amount: int

    def to_unlocking_script(self, sighash_flags: SIGHASH, is_sig_hash_preimage: bool, append_constants: bool) -> Script:
        """Construct unlocking script for the `pushtx` method.

        Args:
            sighash_flags (SIGHASH): The sighash flag with which the PUSHTX locking script was constructed.
            is_sig_hash_preimage (bool): If `True`, it loads on the stack the sig_hash_preimage. Else,
                it loads sha256(sha256(sig_hash_preimage)) (as a number).
            append_constants (bool): Whether or not to append the required constants at the beginning of the script.
        """
        sig_hash_preimage = tx_to_sig_hash_preimage(
            self.tx,
            self.index,
            self.script_pubkey,
            self.prev_amount,
            sighash_flags,
        )

        out = Script()
        if append_constants:
            out += nums_to_script([GROUP_ORDER_INT, Gx])
            out.append_pushdata(Gx_bytes)
        if is_sig_hash_preimage:
            out.append_pushdata(sig_hash_preimage)
        else:
            out.append_pushdata(hash256d(sig_hash_preimage))

        return out


@dataclass
class PushTxBitShiftUnlockingKey:
    """Class encapsulating the data required for unlocking PUSHTX_BIT_SHIFT.

    Attributes:
        tx (Tx): The transaction for which we want to construct the unlocking script.
        index (int): The index of the UTXO for which we want to construct the unlocking script.
        script_pubkey (Script): The script_pubkey of the outpoint we want to construct the unlocking
            script for.
        prev_amount (int): The amount of the outpoint we want to construct the unlocking
            script for.
    """

    tx: Tx
    index: int
    script_pubkey: Script
    prev_amount: int

    def to_unlocking_script(
        self, sighash_flags: SIGHASH, is_sig_hash_preimage: bool, security: int
    ) -> Union[Tx, Script]:
        """Construct unlocking script for the `pushtx_bit_shift` method.

        Args:
            sighash_flags (SIGHASH): The sighash flag with which the PUSHTX_BIT_SHIFT locking script was constructed.
            is_sig_hash_preimage (bool): If `True`, it loads on the stack the sig_hash_preimage. Else,
                it loads sha256(sha256(sig_hash_preimage))
            security (int): The security value with which the PUSHTX_BIT_SHIFT locking script was constructed.
        """
        assert security in [2, 3], f"Security parameter must be 2 or 3, security: {security}"

        tx_in = self.tx.tx_ins[0]
        sig_hash_preimage = tx_to_sig_hash_preimage(
            self.tx,
            self.index,
            self.script_pubkey,
            self.prev_amount,
            sighash_flags,
        )
        sig_hash = hash256d(sig_hash_preimage)
        sig_hash_int = int.from_bytes(sig_hash)

        while sig_hash_int % 2**security != 1 or sig_hash_int // 2**security < 2 ** (31 * 8):
            tx_in.sequence = (tx_in.sequence + 1) % 0xFFFFFFFF
            self.tx.tx_ins = [tx_in]
            sig_hash_preimage = tx_to_sig_hash_preimage(
                self.tx,
                self.index,
                self.script_pubkey,
                self.prev_amount,
                sighash_flags,
            )
            sig_hash = hash256d(sig_hash_preimage)
            sig_hash_int = int.from_bytes(sig_hash)

        out = Script()
        out.append_pushdata(sig_hash_preimage if is_sig_hash_preimage else sig_hash)

        return out
