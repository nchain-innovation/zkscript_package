"""Bitcoin scripts that achieve transaction introspection."""

from tx_engine import SIGHASH, Script, encode_num, hash256d
from tx_engine.engine.util import GROUP_ORDER_INT, Gx, Gx_bytes

from src.zkscript.script_types.stack_elements import StackBaseElement
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    bytes_to_unsigned,
    int_sig_to_s_component,
    move,
    nums_to_script,
    pick,
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
        # R = 2^3 * G
        "R": bytes.fromhex("022f01e5e15cca351daff3843fb70f3c2f0a1bdd05e5af888a67784ef3e10a2a01"),
        # P = a * G s.t. a * R_x = -1 mod GROUP_ORDER_INT
        "P": bytes.fromhex("03ad36fad55727ebf76f8af96c7c2df9a298dc21d6c15269fdedfd47a70b327637"),
    },
}


class TransactionIntrospection:
    """Class generating Bitcoin scripts that achieve transaction introspection."""

    @staticmethod
    def pushtx(
        sighash_flags: SIGHASH,
        data: StackBaseElement = StackBaseElement(0),  # noqa: B008
        rolling_option: bool = True,
        clean_constants: bool = True,
        verify_constants: bool = True,
        is_sig_hash_preimage: bool = True,
        is_checksigverify: bool = True,
        is_opcodeseparator: bool = False,
    ) -> Script:
        """Construct PUSHTX locking script.

        Stack input:
            - stack:    [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..]
            - altstack: []
        Stack output:
            - stack:    [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..] or fail (
                `clean_constants = False`, `rolling_option = False`, `is_checksigverify = True`)
            - altstack: []

        Args:
            sighash_flags (SIGHASH): Sighash flag with which the message should be constructed
            data (StackBaseElement): Position in the stack of the `data`.
                Defaults to StackBaseElement(0) (on top of the stack).
            rolling_option (int): Whether to roll or pick `data`. Defaults to `True` (roll).
            clean_constants (bool): If `True`, the costants GROUP_ORDER_INT, Gx, Gx_bytes are removed
                from the stack after execution. Defaults to `True`.
            verify_constants (bool): Whether or not to verify the constants used for the script.
            is_sig_hash_preimage (bool): If `True`, the script expects `data` to be the sig_hash_preimage.
                Else, it expects it to be the double sha256 digest of the sig_hash_preimage.
            is_checksigverify (bool): Whether to execute OP_CHECKSIGVERIFY or OP_CHECKSIG. Defaults
                to `True` (OP_CHECKSIGVERIFY).
            is_opcodeseparator (bool): Whether to prepend the signature verification with an
                OP_CODESEPARATOR (so that the code of pushtx is not signed). Defaults to `False`.

        Returns:
            The Bitcoin Script of PUSHTX.

        Note:
            The script fails unless:
                - `is_sig_hash_preimage` is `True` and `data` is is the message digest of the transaction
                    in which the script is executed. The message digest of a transaction is defined here:
                    https://github.com/bitcoin-sv/bitcoin-sv/blob/master/doc/abc/replay-protected-sighash.md#digest-algorithm
                - `is_sig_hash_preimage` is `False` and `data` is the double sha256 digest of the message
                    digest of the transaction in which the script is executed.
        """
        out = Script()

        if verify_constants:
            out.append_pushdata(
                hash256d(
                    hash256d(bytes.fromhex("0220") + Gx_bytes + bytes.fromhex("02"))
                    + hash256d(encode_num(Gx))
                    + hash256d(encode_num(GROUP_ORDER_INT))
                )
            )
            for i in range(3, 0, -1):
                out += pick(position=-i, n_elements=1) + Script.parse_string("OP_HASH256")
            out += Script.parse_string("OP_CAT OP_CAT OP_HASH256 OP_EQUALVERIFY")

        # stack in:  [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..]
        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02]
        out.append_pushdata(bytes.fromhex("0220"))
        out += roll(position=-3, n_elements=1) if clean_constants else pick(position=-3, n_elements=1)  # Move Gx_bytes
        out += Script.parse_string("OP_TUCK OP_2 OP_CAT OP_CAT")

        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02, h]
        out += move(data.shift(2), bool_to_moving_function(rolling_option))
        out += Script.parse_string("OP_HASH256") if is_sig_hash_preimage else Script()
        out += bytes_to_unsigned(32)

        # Compute the s part of the signature
        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02, GROUP_ORDER_INT, (h + Gx) % GROUP_ORDER_INT]
        out += roll(position=-2, n_elements=1) if clean_constants else pick(position=-2, n_elements=1)  # Move Gx
        out += Script.parse_string("OP_ADD")
        out += (
            roll(position=-1, n_elements=1) if clean_constants else pick(position=-1, n_elements=1)
        )  # Move GROUP_ORDER_INT
        out += Script.parse_string("OP_TUCK OP_MOD")

        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..,
        #               Gx_bytes, 0x0220||Gx_bytes||02, s]
        out += int_sig_to_s_component(add_prefix=False)

        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..,
        #               Gx_bytes, Der(Gx,s)]
        out += Script.parse_string(
            "OP_SIZE OP_TUCK OP_TOALTSTACK OP_CAT OP_CAT"
        )  # Construct 0x0220||Gx||02||len(s)||s and put len(s) on the altstack
        out += Script.parse_string("0x30 OP_FROMALTSTACK")
        out += nums_to_script([36])
        out += Script.parse_string("OP_ADD OP_CAT OP_SWAP OP_CAT")  # Construct DER(Gx,s)
        out.append_pushdata(sighash_flags.to_bytes())
        out += Script.parse_string("OP_CAT")  # Append SIGHASH

        # stack out: [GROUP_ORDER_INT, Gx, Gx_bytes, .., data, ..,
        #               Der(Gx,s), Gx_bytes]
        out += Script.parse_string("OP_2 OP_ROT OP_2 OP_SPLIT OP_NIP 32 OP_SPLIT OP_DROP OP_CAT")

        out += Script.parse_string("OP_CODESEPARATOR" if is_opcodeseparator else "")
        out += Script.parse_string("OP_CHECKSIGVERIFY" if is_checksigverify else "OP_CHECKSIG")

        return out

    @staticmethod
    def pushtx_bit_shift(
        sighash_flags: SIGHASH,
        data: StackBaseElement = StackBaseElement(0),  # noqa: B008
        rolling_option: bool = True,
        is_sig_hash_preimage: bool = True,
        is_checksigverify: bool = True,
        is_opcodeseparator: bool = False,
        security: int = 2,
    ) -> Script:
        """Construct PUSHTX (with bit shift) locking script.

        Stack input:
            - stack:    [.. data ..]
            - altstack: []
        Stack output:
            - stack:    [.. data ..] or fail
            - altstack: []

        Args:
            sighash_flags (SIGHASH): Sighash flag with which the message should be constructed
            data (StackBaseElement): Position in the stack of the `data`.
                Defaults to StackBaseElement(0) (on top of the stack).
            rolling_option (int): Whether to roll or pick `data`. Defaults to `True` (roll).
            is_sig_hash_preimage (bool): If `True`, the script expects `data` to be the sig_hash_preimage.
                Else, it expects it to be the double sha256 digest of the sig_hash_preimage.
            is_checksigverify (bool): Whether to execute OP_CHECKSIGVERIFY or OP_CHECKSIG. Defaults
                to `True` (OP_CHECKSIGVERIFY).
            is_opcodeseparator (bool): Whether to prepend the signature verification with an
                OP_CODESEPARATOR (so that the code of PUSHTX is not signed). Defaults to `False`.
            security (int): Which integer used to construct the script (2 or 3). Defaults to 2.

        Returns:
            The Bitcoin Script of PUSHTX with bit shift.

        Note:
            The script fails unless:
                - `is_sig_hash_preimage` is `True` and:
                    - `data` is the message digest of the transaction in which the script is executed.
                        The message digest of a transaction is defined here:
                        https://github.com/bitcoin-sv/bitcoin-sv/blob/master/doc/abc/replay-protected-sighash.md#digest-algorithm
                    - `sha256(sha256(data))` % 2**security = 1
                    - `sha256(sha256(data))` // 2**security >= 2**(31*8)
                - `is_sig_hash_preimage` is `False` and:
                    - `data` is the double sha256 digest of the message digest of the transaction
                        in which the script is executed.
                    - `data` % 2**security = 1
                    - `data` // 2**security >= 2**(31*8)
        """
        assert security in [2, 3], f"Security parameter must be 2 or 3, security: {security}"

        out = Script()

        # stack in:  [.., data, ..]
        # stack out: [.., data, .., s]
        out += move(data, bool_to_moving_function(rolling_option))
        out += (
            Script.parse_string("OP_HASH256") if is_sig_hash_preimage else Script()
        )  # Compute HASH256(data) if needed
        out += nums_to_script([security]) + Script.parse_string("OP_RSHIFT")  # Compute hash digest // 2^security

        # stack out: [.., data, .., Der(R,s)]
        out.append_pushdata(
            pushtx_bit_shift_data[security]["signature_prefix"]
            + pushtx_bit_shift_data[security]["R"][1:]
            + bytes.fromhex("0220")
        )
        out += Script.parse_string("OP_SWAP OP_CAT")
        out.append_pushdata(sighash_flags.to_bytes())
        out += Script.parse_string("OP_CAT")

        # stack out: [.., data, .., Der(R,s), P]
        out.append_pushdata(pushtx_bit_shift_data[security]["P"])

        out += Script.parse_string("OP_CODESEPARATOR" if is_opcodeseparator else "")
        out += Script.parse_string("OP_CHECKSIGVERIFY" if is_checksigverify else "OP_CHECKSIG")

        return out
