import json
from pathlib import Path

import pytest
from tx_engine import SIGHASH, Context, Tx, TxIn, hash256d, sig_hash_preimage

from src.zkscript.script_types.stack_elements import StackBaseElement
from src.zkscript.script_types.unlocking_keys.transaction_introspection import (
    PushTxBitShiftUnlockingKey,
    PushTxUnlockingKey,
)
from src.zkscript.transaction_introspection.transaction_introspection import TransactionIntrospection

prev_txid = int.to_bytes(34060536512648028283387372577505466741680559421950955299118826044926210663733, length=32).hex()
prev_amount = 100


def save_scripts(lock, unlock, save_to_json_folder, filename, test_name):
    if save_to_json_folder:
        output_dir = Path("data") / save_to_json_folder / "elliptic_curves"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_file = output_dir / f"{filename}.json"

        data = {}

        if json_file.exists():
            with json_file.open("r") as f:
                data = json.load(f)

        data[test_name] = {"lock": lock, "unlock": unlock}

        with json_file.open("w") as f:
            json.dump(data, f, indent=4)


@pytest.mark.parametrize(
    "sighash_flags",
    [
        SIGHASH.ALL_FORKID,
        SIGHASH.SINGLE_FORKID,
        SIGHASH.NONE_FORKID,
        SIGHASH.ALL_ANYONECANPAY_FORKID,
        SIGHASH.NONE_ANYONECANPAY_FORKID,
        SIGHASH.SINGLE_ANYONECANPAY_FORKID,
    ],
)
@pytest.mark.parametrize("security", [2, 3])
@pytest.mark.parametrize("is_sig_hash_preimage", [True, False])
@pytest.mark.parametrize("is_opcodeseparator", [True, False])
def test_pushtx_bit_shift(sighash_flags, security, is_sig_hash_preimage, is_opcodeseparator, save_to_json_folder):
    lock = TransactionIntrospection.pushtx_bit_shift(
        sighash_flags=sighash_flags,
        data=StackBaseElement(0),
        rolling_option=1,
        is_sig_hash_preimage=is_sig_hash_preimage,
        is_checksigverify=False,
        is_opcodeseparator=is_opcodeseparator,
        security=security,
    )

    tx_in = TxIn(prev_tx=prev_txid, prev_index=0, sequence=0)
    tx = Tx(version=1, tx_ins=[tx_in], tx_outs=[], locktime=0)

    unlocking_key = PushTxBitShiftUnlockingKey(tx=tx, index=0, script_pubkey=lock, prev_amount=prev_amount)

    tx_in.script_sig = unlocking_key.to_unlocking_script(
        sighash_flags=sighash_flags, is_sig_hash_preimage=is_sig_hash_preimage, security=security
    )

    message = sig_hash_preimage(
        tx=tx, index=0, script_pubkey=lock, prev_amount=prev_amount, sighash_flags=sighash_flags
    )

    context = Context(tx_in.script_sig + lock, z=hash256d(message))
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(
            str(lock), str(tx_in.script_sig), save_to_json_folder, "transaction_introspection", "pushtx_bit_shift"
        )


@pytest.mark.parametrize(
    "sighash_flags",
    [
        SIGHASH.ALL_FORKID,
        SIGHASH.SINGLE_FORKID,
        SIGHASH.NONE_FORKID,
        SIGHASH.ALL_ANYONECANPAY_FORKID,
        SIGHASH.NONE_ANYONECANPAY_FORKID,
        SIGHASH.SINGLE_ANYONECANPAY_FORKID,
    ],
)
@pytest.mark.parametrize("is_sig_hash_preimage", [True, False])
@pytest.mark.parametrize("is_opcodeseparator", [True, False])
def test_pushtx(sighash_flags, is_sig_hash_preimage, is_opcodeseparator, save_to_json_folder):
    lock = TransactionIntrospection.pushtx(
        sighash_flags=sighash_flags,
        data=StackBaseElement(0),
        rolling_option=1,
        clean_constants=True,
        verify_constants=True,
        is_sig_hash_preimage=is_sig_hash_preimage,
        is_checksigverify=False,
        is_opcodeseparator=is_opcodeseparator,
    )

    tx_in = TxIn(prev_tx=prev_txid, prev_index=0, sequence=0)
    tx = Tx(version=1, tx_ins=[tx_in], tx_outs=[], locktime=0)

    unlocking_key = PushTxUnlockingKey(tx=tx, index=0, script_pubkey=lock, prev_amount=prev_amount)

    tx_in.script_sig = unlocking_key.to_unlocking_script(
        sighash_flags=sighash_flags, is_sig_hash_preimage=is_sig_hash_preimage, append_constants=True
    )

    message = sig_hash_preimage(
        tx=tx, index=0, script_pubkey=lock, prev_amount=prev_amount, sighash_flags=sighash_flags
    )

    context = Context(tx_in.script_sig + lock, z=hash256d(message))
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(tx_in.script_sig), save_to_json_folder, "transaction_introspection", "pushtx")
