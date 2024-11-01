import json
from pathlib import Path

import pytest
from tx_engine import SIGHASH, Context, Tx, TxIn, hash256d, sig_hash_preimage

from src.zkscript.transaction_introspection.transaction_introspection import TransactionIntrospection
from src.zkscript.types.stack_elements import StackBaseElement

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
    "sighash_value",
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
@pytest.mark.parametrize("is_opcodeseparator", [True, False])
def test_pushtx_bit_shift(sighash_value, security, is_opcodeseparator, save_to_json_folder):
    lock = TransactionIntrospection.pushtx_bit_shift(
        sighash_value=sighash_value,
        sig_hash_preimage=StackBaseElement(0),
        rolling_option=1,
        is_checksigverify=False,
        is_opcodeseparator=is_opcodeseparator,
        security=security,
    )

    tx_in = TxIn(prev_tx=prev_txid, prev_index=0, sequence=0)
    tx = Tx(version=1, tx_ins=[tx_in], tx_outs=[], locktime=0)

    tx, tx_in.script_sig = TransactionIntrospection.pushtx_bit_shift_unlock(
        tx=tx, index=0, script_pubkey=lock, prev_amount=prev_amount, sighash_value=sighash_value, security=security
    )

    message = sig_hash_preimage(
        tx=tx, index=0, script_pubkey=lock, prev_amount=prev_amount, sighash_value=sighash_value
    )

    context = Context(tx_in.script_sig + lock, z=hash256d(message))
    assert context.evaluate()
    assert len(context.get_stack()) == 1
    assert len(context.get_altstack()) == 0

    if save_to_json_folder:
        save_scripts(
            str(lock), str(tx_in.script_sig), save_to_json_folder, "transaction_introspection", "pushtx_bit_shift"
        )


@pytest.mark.parametrize(
    "sighash_value",
    [
        SIGHASH.ALL_FORKID,
        SIGHASH.SINGLE_FORKID,
        SIGHASH.NONE_FORKID,
        SIGHASH.ALL_ANYONECANPAY_FORKID,
        SIGHASH.NONE_ANYONECANPAY_FORKID,
        SIGHASH.SINGLE_ANYONECANPAY_FORKID,
    ],
)
@pytest.mark.parametrize("is_opcodeseparator", [True, False])
def test_pushtx(sighash_value, is_opcodeseparator, save_to_json_folder):
    lock = TransactionIntrospection.pushtx(
        sighash_value=sighash_value,
        sig_hash_preimage=StackBaseElement(0),
        rolling_option=1,
        clean_constants=True,
        verify_constants=True,
        is_checksigverify=False,
        is_opcodeseparator=is_opcodeseparator,
    )

    tx_in = TxIn(prev_tx=prev_txid, prev_index=0, sequence=0)
    tx = Tx(version=1, tx_ins=[tx_in], tx_outs=[], locktime=0)

    tx_in.script_sig = TransactionIntrospection.pushtx_unlock(
        tx=tx, index=0, script_pubkey=lock, prev_amount=prev_amount, sighash_value=sighash_value, append_constants=True
    )

    message = sig_hash_preimage(
        tx=tx, index=0, script_pubkey=lock, prev_amount=prev_amount, sighash_value=sighash_value
    )

    context = Context(tx_in.script_sig + lock, z=hash256d(message))
    assert context.evaluate()
    assert len(context.get_stack()) == 1
    assert len(context.get_altstack()) == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(tx_in.script_sig), save_to_json_folder, "transaction_introspection", "pushtx")