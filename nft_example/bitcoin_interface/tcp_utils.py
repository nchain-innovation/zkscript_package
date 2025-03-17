import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from elliptic_curves.instantiations.mnt4_753.mnt4_753 import MNT4_753, ProofMnt4753, VerifyingKeyMnt4753
from tx_engine import SIGHASH, Script, Tx, TxOut, Wallet
from tx_engine.interface.blockchain_interface import BlockchainInterface

from nft_example.bitcoin_interface.tx_engine_utils import (
    p2pk,
    prepend_signature,
    spend_p2pk,
    tx_from_id,
    tx_to_input,
    update_tx_balance,
)
from src.zkscript.groth16.mnt4_753.mnt4_753 import mnt4_753 as mnt4_753_script
from src.zkscript.types.locking_keys.groth16 import Groth16LockingKeyWithPrecomputedMsm
from src.zkscript.types.unlocking_keys.groth16 import Groth16UnlockingKeyWithPrecomputedMsm
from src.zkscript.util.utility_scripts import nums_to_script


def load_vk(path: str):
    """Load VerifyingKey."""
    with open(path,"rb") as f:
        vk_bytes = list(f.read())
    return VerifyingKeyMnt4753.deserialise(vk_bytes[8:])

def load_proof(path: str):
    """Load Proof."""
    with open(path,"rb") as f:
        proof_bytes = list(f.read())
    return ProofMnt4753.deserialise(proof_bytes[8:])

def load_processed_input(path: str):
    """Load input for ZKP, pre-hashed for PCD."""
    with open(path,"rb") as f:
        processed_input_bytes = list(f.read())
    length = (MNT4_753.scalar_field.get_modulus().bit_length() + 8) // 8

    index=8
    n = int.from_bytes(bytes=bytearray(processed_input_bytes[index:index+8]),byteorder='little')
    index +=8

    inputs = []
    for _ in range(n):
        inputs.append(
            MNT4_753.scalar_field.deserialise(processed_input_bytes[index:index+length])
        )
        index += length

    return [input.to_int() for input in inputs]


def proof_to_unlocking_script(path_proof: str, path_input: str, path_vk: str):
    """Turn a zk proof into an unlocking script."""
    proof = load_proof(path_proof)
    vk = load_vk(path_vk)
    inputs = load_processed_input(path_input)
    prepared_vk = vk.prepare()
    prepared_proof = proof.prepare_for_zkscript(prepared_vk, inputs)

    return Groth16UnlockingKeyWithPrecomputedMsm(
        A=prepared_proof.a,
        B=prepared_proof.b,
        C=prepared_proof.c,
        gradients_pairings=[
            prepared_proof.gradients_b,
            prepared_proof.gradients_minus_gamma,
            prepared_proof.gradients_minus_delta,
        ],
        inverse_miller_output=prepared_proof.inverse_miller_loop,
        precomputed_msm=[]
    ).to_unlocking_script(mnt4_753_script)

def vk_and_input_to_script(path_input: str, path_vk: str):
    """Turn VerifyingKey and input into a locking script."""
    processed_input = load_processed_input(path_input)
    vk = load_vk(path_vk)
    assert len(vk.gamma_abc) == len(processed_input) + 1

    precomputed_msm = vk.gamma_abc[0]
    for base, input in zip(vk.gamma_abc[1:],processed_input):
        precomputed_msm += base.multiply(input)

    prepared_vk = vk.prepare_for_zkscript()

    vk_for_script = Groth16LockingKeyWithPrecomputedMsm(
        alpha_beta = prepared_vk.alpha_beta,
        minus_gamma= prepared_vk.minus_gamma,
        minus_delta= prepared_vk.minus_delta,
        gradients_pairings=[
            prepared_vk.gradients_minus_gamma,
            prepared_vk.gradients_minus_delta
        ],
    )

    return nums_to_script(precomputed_msm.to_list()) + mnt4_753_script.groth16_verifier_with_precomputed_msm(
        locking_key=vk_for_script,
        modulo_threshold=200*8,
        check_constant=True,
        clean_constant=True
    )

# Execute the swap between a token transaction and a BSV output
def execute_swap(
    token_txid: str,
    bsv_txid: str,
    bsv_index: int,
    token_pub_key: Wallet,
    bsv_pub_key: Wallet,
    network: BlockchainInterface,
) -> list[str]:
    token_tx = tx_from_id(token_txid, network)
    bsv_tx = tx_from_id(bsv_txid, network)

    token_input = tx_to_input(token_tx,0,Script())
    bsv_input = tx_to_input(bsv_tx,bsv_index,Script())

    token_output = p2pk(bsv_pub_key,0)
    bsv_output = p2pk(token_pub_key,bsv_tx.tx_outs[bsv_index].amount)

    swap_tx = Tx(
        version=1,
        tx_ins=[token_input, bsv_input],
        tx_outs=[token_output, bsv_output],
        locktime=0
    )

    swap_tx = update_tx_balance(
        swap_tx,
        1,
        10,
    )

    swap_tx = prepend_signature(
        token_tx,
        swap_tx,
        0,
        token_pub_key,
        SIGHASH.ALL_FORKID
    )

    swap_tx = prepend_signature(
        bsv_tx,
        swap_tx,
        1,
        bsv_pub_key,
        SIGHASH.ALL_FORKID
    )

    return swap_tx, network.broadcast_tx(swap_tx.serialize().hex())

# Spend a Groth16 verifier to a P2PK
def spend_zkp_to_output(
    tx: Tx,
    index: int,
    funding_tx: Tx,
    funding_index: int,
    path_proof: str,
    path_input: str,
    path_vk: str,
    public_key: Wallet,
    fee_rate: int,
    network: BlockchainInterface
):
    unlocking_script_zkp = proof_to_unlocking_script(path_proof, path_input, path_vk)
    input_zkp = tx_to_input(tx, index, unlocking_script_zkp)

    input_funding = tx_to_input(
        funding_tx,
        funding_index,
        Script(),
    )

    amount=funding_tx.tx_outs[funding_index].amount

    spending_tx = Tx(
        version=1,
        tx_ins=[input_zkp, input_funding],
        tx_outs=[p2pk(public_key=public_key,amount=amount)],
    )

    spending_tx = update_tx_balance(
        tx=spending_tx,
        index=0,
        fee_rate=fee_rate
    )

    spending_tx = prepend_signature(
        funding_tx,
        spending_tx,
        1,
        public_key,
    )

    return spending_tx, network.broadcast_tx(spending_tx.serialize().hex())

# Spend a P2PK to a Groth16 verifier with precomputed msm
def p2pk_to_groth16(
    tx: Tx,
    index: int,
    path_input: str,
    path_vk: str,
    public_key: Wallet,
    fee_rate: int,
    network: BlockchainInterface
):
    locking_script = vk_and_input_to_script(path_input, path_vk)
    amount = tx.tx_outs[index].amount
    return spend_p2pk(
        txs=[tx],
        indices=[index],
        outputs=[
            TxOut(0,locking_script),
            p2pk(public_key,amount),
        ],
        index_output=1,
        public_keys=[public_key],
        fee_rate=fee_rate,
        network=network,
    )
