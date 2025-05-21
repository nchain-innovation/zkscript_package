import sys
from pathlib import Path

sys.path.append(str(Path().resolve().parent.parent))

from elliptic_curves.data_structures.vk import PreparedVerifyingKey
from elliptic_curves.data_structures.zkscript import ZkScriptVerifyingKey
from elliptic_curves.instantiations.mnt4_753.mnt4_753 import MNT4_753, ProofMnt4753, VerifyingKeyMnt4753
from tx_engine import SIGHASH, Tx, TxOut, Wallet
from tx_engine.interface.blockchain_interface import BlockchainInterface

from src.zkscript.groth16.mnt4_753.mnt4_753 import mnt4_753
from src.zkscript.reftx.reftx import RefTx
from src.zkscript.types.locking_keys.reftx import RefTxLockingKey
from src.zkscript.types.unlocking_keys.reftx import RefTxUnlockingKey
from token_examples.tx_engine_utils import bytes_to_script, prepend_signature, tx_to_input

ScalarFieldMNT4 = MNT4_753.scalar_field


def load_and_process_vk(genesis_txid: int) -> list[VerifyingKeyMnt4753, PreparedVerifyingKey, ZkScriptVerifyingKey]:
    with open(str(Path().cwd() / "burn_proof_system/data/keys/vk.bin"), "rb") as f:
        vk_bytes = list(f.read())
        vk = VerifyingKeyMnt4753.deserialise(vk_bytes[8:])

        # Precompute locking data
        precomputed_l_out = vk.gamma_abc[0] + vk.gamma_abc[1].multiply(genesis_txid)
        # Modified gamma_abc
        gamma_abc_mod = [precomputed_l_out, *vk.gamma_abc[2:]]
        # Modified vk
        vk_mod = VerifyingKeyMnt4753(vk.alpha, vk.beta, vk.gamma, vk.delta, gamma_abc_mod)
        # Prepare the vk
        cache_vk = vk_mod.prepare()
        prepared_vk = vk_mod.prepare_for_zkscript(cache_vk)

        return vk_mod, cache_vk, prepared_vk


def generate_pob_utxo(
    vk: PreparedVerifyingKey, prepared_vk: ZkScriptVerifyingKey, issuer_funds: Tx, issuer_pub_key: Wallet
) -> list[TxOut]:
    # Generate PoB locking script
    locking_key = RefTxLockingKey(
        alpha_beta=prepared_vk.alpha_beta,
        minus_gamma=prepared_vk.minus_gamma,
        minus_delta=prepared_vk.minus_delta,
        precomputed_l_out=vk.gamma_abc[0].to_list(),
        gamma_abc_without_l_out=[element.to_list() for element in vk.gamma_abc[1:]],
        gradients_pairings=[
            prepared_vk.gradients_minus_gamma,
            prepared_vk.gradients_minus_delta,
        ],
        sighash_flags=SIGHASH.ALL_FORKID,
    )

    lock = RefTx(mnt4_753).locking_script(
        sighash_flags=SIGHASH.ALL_FORKID,
        locking_key=locking_key,
        modulo_threshold=200 * 8,
        max_multipliers=None,
        check_constant=True,
    )

    proof_of_burn_utxo = TxOut(amount=1, script_pubkey=lock)
    change_utxo = TxOut(amount=issuer_funds.tx_outs[0].amount, script_pubkey=issuer_pub_key.get_locking_script())

    return proof_of_burn_utxo, change_utxo


def spend_proof_of_burn(
    outputs: list[TxOut],
    cache_vk: PreparedVerifyingKey,
    token_tx: Tx,
    pob_tx: Tx,
    token_pub_key: Wallet,
    pob_pub_key: Wallet,
    network: BlockchainInterface,
):
    with open(str(Path().cwd() / "burn_proof_system/data/proofs/proof_of_burn.bin"), "rb") as f:
        proof_bytes = list(f.read())
        proof = ProofMnt4753.deserialise(proof_bytes[8:])
    with open(str(Path().cwd() / "burn_proof_system/data/proofs/input_proof_of_burn.bin"), "rb") as f:
        processed_input_bytes = list(f.read())
        # Bit length of a single input
        length = (MNT4_753.scalar_field.get_modulus().bit_length() + 8) // 8
        # Fetch the second input (the first one is the genesis_txid, which we hard-coded)
        input = [ScalarFieldMNT4.deserialise(processed_input_bytes[16 + length :]).to_int()]

    # Prepare the proof
    prepared_proof = proof.prepare_for_zkscript(cache_vk, input)

    # Generate unlocking script
    unlock_key = RefTxUnlockingKey.from_data(
        groth16_model=mnt4_753,
        pub=input,
        A=prepared_proof.a,
        B=prepared_proof.b,
        C=prepared_proof.c,
        gradients_pairings=[
            prepared_proof.gradients_b,
            prepared_proof.gradients_minus_gamma,
            prepared_proof.gradients_minus_delta,
        ],
        gradients_multiplications=prepared_proof.gradients_multiplications,
        max_multipliers=None,
        gradients_additions=prepared_proof.gradients_additions,
        inverse_miller_output=prepared_proof.inverse_miller_loop,
        gradient_precomputed_l_out=prepared_proof.gradient_gamma_abc_zero,
    )
    unlock = unlock_key.to_unlocking_script(mnt4_753)

    # Prepare burning transaction
    inputs = [
        tx_to_input(token_tx, 0, bytes_to_script(bytes.fromhex(token_pub_key.get_public_key_as_hexstr()))),
        tx_to_input(pob_tx, 0, unlock),
        tx_to_input(pob_tx, 1, bytes_to_script(bytes.fromhex(pob_pub_key.get_public_key_as_hexstr()))),
    ]

    spending_tx = Tx(
        version=1,
        tx_ins=inputs,
        tx_outs=outputs,
        locktime=0,
    )

    spending_tx = prepend_signature(
        token_tx,
        spending_tx,
        0,
        token_pub_key,
    )

    spending_tx = prepend_signature(
        pob_tx,
        spending_tx,
        2,
        pob_pub_key,
    )

    return spending_tx, network.broadcast_tx(spending_tx.serialize().hex())
