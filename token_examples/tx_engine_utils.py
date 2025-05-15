"""Utilies to facilitate interaction with the blockchain."""

from random import randint

import ecdsa
from tx_engine import SIGHASH, Script, Tx, TxIn, TxOut, Wallet, sig_hash
from tx_engine.interface.blockchain_interface import BlockchainInterface
from tx_engine.interface.interface_factory import InterfaceFactory

GROUP_ORDER = ecdsa.curves.SECP256k1.order

SIG_LEN = 0x48


def setup_network_connection(network):
    """Setup network connection."""
    return InterfaceFactory().set_config({"interface_type": "woc", "network_type": network})


# Turns a transaction into a TxIn
def tx_to_input(tx: Tx, index: int, unlocking_script: Script, sequence=0) -> TxIn:
    return TxIn(prev_tx=tx.id(), prev_index=index, script=unlocking_script, sequence=sequence)


# Update amount of tx.tx_outs[index] based on fee rate
def update_tx_balance(
    tx: Tx,
    index: int,
    fee_rate: int,  # Quoted in satoshis / kB
) -> Tx:
    """Update the amount of tx.tx_outs[index] according to the fee rate."""
    tx_size = len(tx.serialize())
    fee = (tx_size * fee_rate // 1024) + 1

    assert tx.tx_outs[index].amount > fee, f"Not enough funds. Fee: {fee}, amount: {tx.tx_outs[index].amount}"

    new_tx_outs = []
    for i, output in enumerate(tx.tx_outs):
        new_tx_outs.append(
            TxOut(
                amount=output.amount - fee * (i == index),
                script_pubkey=output.script_pubkey,
            )
        )

    return Tx(version=tx.version, tx_ins=tx.tx_ins, tx_outs=new_tx_outs, locktime=tx.locktime)


# Convert a list of bytes into a script
def bytes_to_script(bytes: list[bytes]):
    out = Script()
    out.append_pushdata(bytes)
    return out


# Prepend signature to a TxIn
def prepend_signature(
    prev_tx: Tx,
    tx: Tx,
    index: int,
    public_key: Wallet,
    flag: SIGHASH = SIGHASH.ALL_FORKID,
) -> Tx:
    sig = sign_tx_with_random_k(prev_tx, tx, index, public_key, flag)
    while len(sig) != SIG_LEN:
        sig = sign_tx_with_random_k(prev_tx, tx, index, public_key, flag)
    new_tx_ins = []
    for i, input in enumerate(tx.tx_ins):
        new_tx_ins.append(
            TxIn(
                prev_tx=input.prev_tx,
                prev_index=input.prev_index,
                script=input.script_sig if i != index else bytes_to_script(sig) + input.script_sig,
                sequence=input.sequence,
            )
        )

    return Tx(version=tx.version, tx_ins=new_tx_ins, tx_outs=tx.tx_outs, locktime=tx.locktime)


# Spend a UTXO to a list of inputs
# Requires knowledge of the unlocking script
def spend_utxo(
    tx: Tx,
    index: int,
    unlocking_script: Script,
    outputs: list[TxOut],
    index_output: int,
    fee_rate: int,
    network: BlockchainInterface,
):
    spending_tx = Tx(version=1, tx_ins=[tx_to_input(tx, index, unlocking_script)], tx_outs=outputs, locktime=0)

    spending_tx = update_tx_balance(
        spending_tx,
        index_output,
        fee_rate,
    )

    return spending_tx, network.broadcast_tx(spending_tx.serialize().hex())


# Spend a series of P2PK UTXOs specified as a list of txs and indices
def spend_p2pk(
    txs: list[Tx],
    indices: list[int],
    outputs: list[TxOut],
    index_output: int,
    public_keys: list[Wallet],
    fee_rate: int,
    network: BlockchainInterface,
    flag: SIGHASH = SIGHASH.ALL_FORKID,
):
    inputs = [tx_to_input(tx, index, Script()) for (index, tx) in zip(indices, txs)]
    spending_tx = Tx(version=1, tx_ins=inputs, tx_outs=outputs, locktime=0)
    spending_tx = update_tx_balance(
        tx=spending_tx,
        index=index_output,
        fee_rate=fee_rate,
    )

    for i, (tx, pub_key) in enumerate(zip(txs, public_keys)):
        spending_tx = prepend_signature(
            prev_tx=tx,
            tx=spending_tx,
            index=i,
            public_key=pub_key,
            flag=flag,
        )

    return spending_tx, network.broadcast_tx(spending_tx.serialize().hex())


# Spend a series of P2PK UTXOs specified as a list of txs and indices
def spend_p2pkh(
    txs: list[Tx],
    indices: list[int],
    outputs: list[TxOut],
    index_output: int,
    public_keys: list[Wallet],
    fee_rate: int,
    network: BlockchainInterface,
    flag: SIGHASH = SIGHASH.ALL_FORKID,
):
    inputs = [
        tx_to_input(tx, index, bytes_to_script(bytes.fromhex(pub_key.get_public_key_as_hexstr())))
        for (index, tx, pub_key) in zip(indices, txs, public_keys)
    ]
    spending_tx = Tx(version=1, tx_ins=inputs, tx_outs=outputs, locktime=0)
    spending_tx = update_tx_balance(
        spending_tx,
        index_output,
        fee_rate,
    )

    for i, (tx, pub_key) in enumerate(zip(txs, public_keys)):
        spending_tx = prepend_signature(
            prev_tx=tx,
            tx=spending_tx,
            index=i,
            public_key=pub_key,
            flag=flag,
        )

    return spending_tx, network.broadcast_tx(spending_tx.serialize().hex())


# Generates P2PK script
def p2pk_script(public_key: Wallet) -> Script:
    out = Script()
    out.append_pushdata(bytes.fromhex(public_key.get_public_key_as_hexstr()))
    out += Script.parse_string("OP_CHECKSIG")

    return out


# Generates P2PK output
def p2pk(public_key: Wallet, amount: int) -> TxOut:
    out = TxOut(amount=amount, script_pubkey=p2pk_script(public_key))

    return out


# Generates P2PK output
def p2pkh(public_key: Wallet, amount: int) -> TxOut:
    out = TxOut(amount=amount, script_pubkey=public_key.get_locking_script())

    return out


# Get transaction from the chain
def tx_from_id(txid: str, network: BlockchainInterface) -> Tx:
    return Tx.parse_hexstr(network.get_raw_transaction(txid))


# Sign a transaction
def sign_tx_with_random_k(
    prev_tx: Tx, tx: Tx, index: int, public_key: Wallet, flag: SIGHASH = SIGHASH.ALL_FORKID
) -> list[bytes]:
    # Convert private key
    priv_key_int = public_key.to_int()
    generator = ecdsa.SECP256k1.generator
    pub_key = ecdsa.ecdsa.Public_key(generator, generator * priv_key_int)
    priv_key = ecdsa.ecdsa.Private_key(pub_key, priv_key_int)
    # Generate sighash
    prev_locking_script = prev_tx.tx_outs[tx.tx_ins[index].prev_index].script_pubkey
    prev_amount = prev_tx.tx_outs[tx.tx_ins[index].prev_index].amount
    msg = int.from_bytes(sig_hash(tx, index, prev_locking_script, prev_amount, sighash_flags=flag))
    # Generate signature
    random_k = randint(2, GROUP_ORDER - 1)
    sig = priv_key.sign(msg, random_k)
    der = ecdsa.util.sigencode_der_canonize(sig.r, sig.s, GROUP_ORDER)
    return der + flag.to_bytes()
