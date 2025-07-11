"""Implementation of RefTx Bitcoin Script."""

from tx_engine import SIGHASH, Script

from src.zkscript.groth16.model.groth16 import Groth16
from src.zkscript.script_types.locking_keys.reftx import RefTxLockingKey
from src.zkscript.script_types.unlocking_keys.msm_with_fixed_bases import MsmWithFixedBasesUnlockingKey
from src.zkscript.script_types.unlocking_keys.msm_with_fixed_bases_projective import (
    MsmWithFixedBasesProjectiveUnlockingKey,
)
from src.zkscript.transaction_introspection.transaction_introspection import TransactionIntrospection
from src.zkscript.util.utility_scripts import nums_to_script

BYTES_32 = 32
BYTES_16 = 16
BYTES_8 = 8
BYTES_4 = 4
BYTES_2 = 2
BYTES_1 = 1


class RefTx:
    """RefTx Bitcoin Script.

    This class is used to generate the locking script required by RefTx, which is a circuit that enforces arbitrary
    conditions (specified by a circuit C) on the spending transaction. The circuit C looks as follows:
        C(l_out, u_stx, s_stx)
    where `l_out` is fixed in the locking script, and `u_stx` is specified by the spender.
    The circuit C' encapsulates C, and looks as follows:
        C'(l_out, sighash(stx), u_stx)
    """

    def __init__(self, groth16_model: Groth16):
        """Initialize the RefTx class.

        Args:
            groth16_model (Groth16): The Groth16 script model used to construct the groth16_verifier script
                inside the RefTx locking script.
        """
        self.groth16_model = groth16_model

    def __bytes_sighash_chunks(self) -> int:
        """Compute the number of bytes of each chunk of the sighash."""
        # Compute the byte size of self.groth_model.r
        byte_size_r = self.groth16_model.r.bit_length() // 8
        # Compute the max multiplier for the chunks in which sighash is split
        if byte_size_r > BYTES_32:
            return BYTES_32
        if byte_size_r > BYTES_16:
            return BYTES_16
        if byte_size_r > BYTES_8:
            return BYTES_8
        if byte_size_r > BYTES_4:
            return BYTES_4
        if byte_size_r > BYTES_2:
            return BYTES_2
        return BYTES_1

    def __multipliers(
        self,
        locking_key: RefTxLockingKey,
        max_multipliers: list[int] | None = None,
    ) -> list[int]:
        """Compute the max multipliers for Groth16.

        Args:
            locking_key (RefTxLockingKey): Locking key used to generate the locking script.
            max_multipliers (list[int]):  List where each element max_multipliers[i] is the max value of the i-th public
                statement, disregarding the sighash.
        """
        bytes_sighash_chunks = self.__bytes_sighash_chunks()
        n_chunks = 32 // bytes_sighash_chunks
        max_multipliers = (
            max_multipliers
            if max_multipliers is not None
            else [self.groth16_model.r] * (len(locking_key.gamma_abc_without_l_out) - n_chunks)
        )
        return [*[2 ** (bytes_sighash_chunks * 8)] * n_chunks, *max_multipliers]

    def locking_script(
        self,
        sighash_flags: SIGHASH,
        locking_key: RefTxLockingKey,
        modulo_threshold: int,
        max_multipliers: list[int] | None = None,
        check_constant: bool | None = None,
    ) -> Script:
        """Return the locking script required by RefTx.

        Args:
            locking_key (RefTxLockingKey): Locking key used to generate the locking script.
            sighash_flags (SIGHASH): Sighash flags used to construct the sighash.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo
                `self.groth16_model.pairing_model.q`.
            max_multipliers (list[int]):  List where each element max_multipliers[i] is the max value of the i-th public
                statement, disregarding the sighash. If None, it is computed automatically.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.

        Returns:
            The locking script required by RefTx.

        Note:
            The public inputs to the RefTx circuit are (l_out, sighash(stx), u_stx). When we talk about
            public inputs above (in the max_multipliers), we only consider u_stx. The max_multipliers for
            sighash(stx) are computed automatically, and l_out is hard-coded in the locking script.
        """
        # Compute bytes sighash chunks and number of chunks
        bytes_sighash_chunks = self.__bytes_sighash_chunks()
        n_chunks = 32 // bytes_sighash_chunks
        # Append the multipliers for the sighash
        max_multipliers = self.__multipliers(locking_key=locking_key, max_multipliers=max_multipliers)

        out = Script()

        # Extract the sighash from the unlocking script
        # msm_data(**) is the data required to execute the multi scalar multiplication on **
        # chunks(sighash(stx)) are the chunks in which the sighash is split when supplied in
        # the unlocking script of RefTx
        #
        # stack in:     [.., msm_data(u_stx), msm_data(sighash(stx))]
        # stack out:    [.., msm_data(u_stx), msm_data(sighash(stx))]
        # altstack out: [chunks(sighash(stx))]
        for i in range(n_chunks):
            if locking_key.use_proj_coordinates:
                out += MsmWithFixedBasesProjectiveUnlockingKey.extract_scalar_as_unsigned(
                    max_multipliers=max_multipliers, index=i, rolling_option=False
                )
            else:
                out += MsmWithFixedBasesUnlockingKey.extract_scalar_as_unsigned(
                    max_multipliers=max_multipliers, index=i, rolling_option=False
                )
            out += nums_to_script([bytes_sighash_chunks]) + Script.parse_string("OP_SPLIT OP_DROP")
            out += Script.parse_string("OP_TOALTSTACK")

        # stack in:     [.., q, .., msm_data(u_stx), msm_data(sighash(stx))]
        # altstack in:  [chunks(sighash(stx))]
        # stack out:    [..] of fail
        # altstack out: [chunks(sighash(stx))]
        if locking_key.use_proj_coordinates:
            out += self.groth16_model.groth16_verifier_proj(
                locking_key=locking_key.to_groth16_key(),
                modulo_threshold=modulo_threshold,
                extractable_inputs=n_chunks,
                max_multipliers=max_multipliers,
                check_constant=check_constant,
                clean_constant=True,
            )
        else:
            out += self.groth16_model.groth16_verifier(
                locking_key=locking_key.to_groth16_key(),
                modulo_threshold=modulo_threshold,
                extractable_inputs=n_chunks,
                max_multipliers=max_multipliers,
                check_constant=check_constant,
                clean_constant=True,
            )
        out += Script.parse_string("OP_VERIFY")

        # stack in:     [..]
        # altstack in:  [chunks(sighash(stx))]
        # stack out:    [0/1]
        # altstack out: []
        out += Script.parse_string("OP_FROMALTSTACK")
        out += Script.parse_string(" ".join(["OP_FROMALTSTACK OP_SWAP OP_CAT"] * (n_chunks - 1)))
        out += TransactionIntrospection.pushtx(
            sighash_flags=sighash_flags,
            is_sig_hash_preimage=False,
            is_opcodeseparator=True,
            is_checksigverify=False,
        )

        return out
