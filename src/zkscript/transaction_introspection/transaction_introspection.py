from typing import Union

from tx_engine import SIGHASH, Script, Tx, encode_num, hash256d
from tx_engine import sig_hash_preimage as tx_to_sig_hash_preimage
from tx_engine.engine.util import GROUP_ORDER_INT, Gx, Gx_bytes

from src.zkscript.types.stack_elements import StackBaseElement
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    bytes_to_unsigned,
    int_sig_to_s_component,
    move,
    nums_to_script,
    pick,
    reverse_endianness,
    roll,
)

pushtx_bit_shift_data = {
    2: {
        "signature_prefix": bytes.fromhex("3045022100"),
        # R = 2^2 * G
        "R": bytes.fromhex("02e493dbf1c10d80f3581e4904930b1404cc6c13900ee0758474fa94abe8c4cd13"),
        # P = a * G s.t. a * R_x = -1 mod GROUP_ORDER_INT
        "P": bytes.fromhex("034218426b38c75b706db9010aad7795fd05b872060921c048d9a679d8878c7660"),
    },
    3: {
        "signature_prefix": bytes.fromhex("30440220"),
        # R = 2^2 * G
        "R": bytes.fromhex("022f01e5e15cca351daff3843fb70f3c2f0a1bdd05e5af888a67784ef3e10a2a01"),
        # P = a * G s.t. a * R_x = -1 mod GROUP_ORDER_INT
        "P": bytes.fromhex("03ad36fad55727ebf76f8af96c7c2df9a298dc21d6c15269fdedfd47a70b327637"),
    },
}


class TransactionIntrospection:
    @staticmethod
    def pushtx(
        sighash_value: SIGHASH,
        sig_hash_preimage: StackBaseElement = StackBaseElement(0),  # noqa: B008
        rolling_option: bool = True,
        clean_constants: bool = True,
        verify_constants: bool = True,
        is_checksigverify: bool = True,
        is_opcodeseparator: bool = False,
    ) -> Script:
        """Construct PUSHTX locking script.

        Stack input:
            - stack:    [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..]
            - altstack: []
        Stack output:
            - stack:    [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..] or fail
            - altstack: []

        Args:
            sighash_value (SIGHASH): Sighash flag with which the message should be constructed
            sig_hash_preimage (StackBaseElement): Position in the stack of the sig_hash_preimage.
                Defaults to StackBaseElement(0) (on top of the stack).
            rolling_option (int): Whether to roll or pick sig_hash_preimage. Defaults to `True` (roll).
            clean_constants (bool): Whether to clean the constants needed for the script:
                GROUP_ORDER_INT, Gx, Gx_bytes. Defaults to `True`.
            verify_constants (bool): Whether or not to verify the constants used for the script.
            is_checksigverify (bool): Whether to execute OP_CHECKSIGVERIFY or OP_CHECKSIG. Defaults
                to `True` (OP_CHECKSIGVERIFY).
            is_opcodeseparator (bool): Whether to prepend the signature verification with an
                OP_CODESEPARATOR (so that the code of pushtx is not signed). Defaults to `False`.

        Returns:
            The Bitcoin Script of PUSHTX, which fails unless sig_hash_preimage is the message digest of the
            transaction in which the script is executed. The message digest of a transaction is defined here:
            https://github.com/bitcoin-sv/bitcoin-sv/blob/master/doc/abc/replay-protected-sighash.md#digest-algorithm

        """

        out = Script()

        if verify_constants:
            out.append_pushdata(hash256d(Gx_bytes + encode_num(Gx) + encode_num(GROUP_ORDER_INT)))
            for i in range(3, 0, -1):
                out += pick(position=-i, n_elements=1)
            out += Script.parse_string("OP_CAT OP_CAT OP_HASH256 OP_EQUALVERIFY")

        # stack in:  [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..]
        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02]
        out.append_pushdata(bytes.fromhex("0220"))
        out += roll(position=-3, n_elements=1) if clean_constants else pick(position=-3, n_elements=1)  # Move Gx_bytes
        out += Script.parse_string("OP_TUCK 0x02 OP_CAT OP_CAT")

        # stack in:  [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02]
        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02, h]
        out += move(sig_hash_preimage.shift(2), bool_to_moving_function(rolling_option))
        out += Script.parse_string("OP_HASH256") + reverse_endianness(32) + bytes_to_unsigned()

        # Compute the s part of the signature
        # stack in:  [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02, h]
        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02, GROUP_ORDER_INT, (h + Gx) % GROUP_ORDER_INT]
        out += roll(position=-2, n_elements=1) if clean_constants else pick(position=-2, n_elements=1)  # Move Gx
        out += Script.parse_string("OP_ADD")
        out += (
            roll(position=-1, n_elements=1) if clean_constants else pick(position=-1, n_elements=1)
        )  # Move GROUP_ORDER_INT
        out += Script.parse_string("OP_TUCK OP_MOD")

        # stack in:  [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02 GROUP_ORDER_INT, (h + Gx) % GROUP_ORDER_INT]
        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02, s]
        out += int_sig_to_s_component(add_prefix=False)

        # stack in: [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02, s]
        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, Der(Gx,s)]
        out += Script.parse_string(
            "OP_SIZE OP_TUCK OP_TOALTSTACK OP_CAT OP_CAT"
        )  # Construct 0x0220||Gx||02||len(s)||s and put len(s) on the altstack
        out += Script.parse_string("0x30 OP_FROMALTSTACK")
        out += nums_to_script([36])
        out += Script.parse_string("OP_ADD OP_CAT OP_SWAP OP_CAT")  # Construct DER(Gx,s)
        out.append_pushdata(sighash_value.to_bytes())
        out += Script.parse_string("OP_CAT")  # Append SIGHASH

        # stack in:  [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Gx_bytes, Der(Gx,s)]
        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., sig_hash_preimage, ..,
        #               Der(Gx,s), Gx_bytes]
        out += Script.parse_string("0x02 OP_ROT OP_CAT")

        if is_checksigverify and not is_opcodeseparator:
            out += Script.parse_string("OP_CHECKSIGVERIFY")
        elif is_checksigverify and is_opcodeseparator:
            out += Script.parse_string("OP_CODESEPARATOR OP_CHECKSIGVERIFY")
        elif not is_checksigverify and is_opcodeseparator:
            out += Script.parse_string("OP_CODESEPARATOR OP_CHECKSIG")
        else:
            out += Script.parse_string("OP_CHECKSIG")

        return out

    @staticmethod
    def pushtx_bit_shift(
        sighash_value: SIGHASH,
        sig_hash_preimage: StackBaseElement = StackBaseElement(0),  # noqa: B008
        rolling_option: bool = True,
        is_checksigverify: bool = True,
        is_opcodeseparator: bool = False,
        security: int = 2,
    ) -> Script:
        """Construct PUSHTX (with bit shift) locking script.

        Stack input:
            - stack:    [.. sig_hash_preimage ..]
            - altstack: []
        Stack output:
            - stack:    [.. sig_hash_preimage ..] or fail
            - altstack: []

        Args:
            sighash_value (SIGHASH): Sighash flag with which the message should be constructed
            sig_hash_preimage (StackBaseElement): Position in the stack of the sig_hash_preimage.
                Defaults to StackBaseElement(0) (on top of the stack).
            rolling_option (int): Whether to roll or pick sig_hash_preimage. Defaults to `True` (roll).
            is_checksigverify (bool): Whether to execute OP_CHECKSIGVERIFY or OP_CHECKSIG. Defaults
                to `True` (OP_CHECKSIGVERIFY).
            is_opcodeseparator (bool): Whether to prepend the signature verification with an
                OP_CODESEPARATOR (so that the code of pushtx is not signed). Defaults to `False`.
            security (int): Which integer used to construct the script (2 or 3). Defaults to 2.

        Returns:
            The Bitcoin Script of PUSHTX with bit shift, which fails unless:
                - sig_hash_preimage is the message digest of the transaction in which the script is executed.
                    The message digest of a transactionis defined here:
                    https://github.com/bitcoin-sv/bitcoin-sv/blob/master/doc/abc/replay-protected-sighash.md#digest-algorithm
                - sig_hash_preimage % 2**security = 1
                - sig_hash_preimage // 2**security >= 2**(31*8)

        """

        assert security in [2, 3], f"Security parameter must be 2 or 3, security: {security}"

        out = Script()

        # stack in:  [.. sig_hash_preimage ..]
        # stack out: [.. sig_hash_preimage .. s]
        out += move(sig_hash_preimage, bool_to_moving_function(rolling_option))
        out += (
            Script.parse_string("OP_HASH256") + nums_to_script([security]) + Script.parse_string("OP_RSHIFT")
        )  # Compute HASH256(sig_hash_preimage) // 2^security

        # stack out: [.. sig_hash_preimage .. s]
        # stack out: [.. sig_hash_preimage .. Der(R,s)]
        out.append_pushdata(
            pushtx_bit_shift_data[security]["signature_prefix"]
            + pushtx_bit_shift_data[security]["R"][1:]
            + bytes.fromhex("0220")
        )
        out += Script.parse_string("OP_SWAP OP_CAT")
        out.append_pushdata(sighash_value.to_bytes())
        out += Script.parse_string("OP_CAT")

        # stack in:  [.. sig_hash_preimage .. Der(R,s)]
        # stack out: [.. sig_hash_preimage .. Der(R,s) P]
        out.append_pushdata(pushtx_bit_shift_data[security]["P"])

        if is_checksigverify and not is_opcodeseparator:
            out += Script.parse_string("OP_CHECKSIGVERIFY")
        elif is_checksigverify and is_opcodeseparator:
            out += Script.parse_string("OP_CODESEPARATOR OP_CHECKSIGVERIFY")
        elif not is_checksigverify and is_opcodeseparator:
            out += Script.parse_string("OP_CODESEPARATOR OP_CHECKSIG")
        else:
            out += Script.parse_string("OP_CHECKSIG")

        return out

    @staticmethod
    def pushtx_unlock(
        tx: Tx, index: int, script_pubkey: Script, prev_amount: int, sighash_value: SIGHASH, append_constants: bool
    ) -> Script:
        """Construct unlocking script for pushtx.

        Args:
            tx (Tx): The transaction for which we want to construct the unlocking script.
            index (int): The index of the UTXO for which we want to construct the unlocking script.
            script_pubkey (Script): The script_pubkey of the outpoint we want to construct the unlocking
                script for.
            prev_amount (int): The amount of the outpoint we want to construct the unlocking
                script for.
            sighash_value (SIGHASH): The sighash flag with which the pushtx locking script was constructed.
            append_constants (bool): Whether or not to append the required constants at the beginning of the script.

        """

        sig_hash_preimage = tx_to_sig_hash_preimage(
            tx,
            index,
            script_pubkey,
            prev_amount,
            sighash_value,
        )

        out = Script()
        if append_constants:
            out += nums_to_script([GROUP_ORDER_INT, Gx])
            out.append_pushdata(Gx_bytes)
        out.append_pushdata(sig_hash_preimage)

        return out

    @staticmethod
    def pushtx_bit_shift_unlock(
        tx: Tx, index: int, script_pubkey: Script, prev_amount: int, sighash_value: SIGHASH, security: int
    ) -> Union[Tx, Script]:
        """Construct PUSHTX bit shift unlocking script, it assumes that we can tweak the nSequence of the input.

        Args:
            tx (Tx): The transaction for which we want to construct the unlocking script.
            index (int): The index of the UTXO for which we want to construct the unlocking script.
            script_pubkey (Script): The script_pubkey of the outpoint we want to construct the unlocking
                script for.
            prev_amount (int): The amount of the outpoint we want to construct the unlocking
                script for.
            sighash_value (SIGHASH): The sighash flag with which the pushtx locking script was constructed.
            security (int): The security value with which the pushtx_bit_shift locking script was constructed.

        """

        assert security in [2, 3], f"Security parameter must be 2 or 3, security: {security}"

        tx_in = tx.tx_ins[0]
        sig_hash_preimage = tx_to_sig_hash_preimage(
            tx,
            index,
            script_pubkey,
            prev_amount,
            sighash_value,
        )
        sig_hash = hash256d(sig_hash_preimage)
        sig_hash_int = int.from_bytes(sig_hash)

        while sig_hash_int % 2**security != 1 or sig_hash_int // 2**security < 2 ** (31 * 8):
            tx_in.sequence += 1
            tx_in.sequence = tx_in.sequence % 0xFFFFFFFF
            tx.tx_ins = [tx_in]
            sig_hash_preimage = tx_to_sig_hash_preimage(
                tx,
                index,
                script_pubkey,
                prev_amount,
                sighash_value,
            )
            sig_hash = hash256d(sig_hash_preimage)
            sig_hash_int = int.from_bytes(sig_hash)

        out = Script()
        out.append_pushdata(sig_hash_preimage)

        return tx, out
