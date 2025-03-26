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


def tx_to_input(tx: Tx, index: int, unlocking_script: Script, sequence=0) -> TxIn:
    """Turn (tx, index, unlocking_script) into a TxIn."""
    return TxIn(prev_tx=tx.id(), prev_index=index, script=unlocking_script, sequence=sequence)


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


def bytes_to_script(data: list[bytes]):
    """Convert a list of bytes into a script."""
    out = Script()
    out.append_pushdata(data)
    return out


def prepend_signature(
    prev_tx: Tx,
    tx: Tx,
    index: int,
    public_key: Wallet,
    flag: SIGHASH = SIGHASH.ALL_FORKID,
) -> Tx:
    """Prepend signature to a the input at position `index` in `tx`."""
    sig = sign_tx_with_random_k(prev_tx, tx, index, public_key, flag)
    while len(sig) != SIG_LEN:
        sig = sign_tx_with_random_k(prev_tx, tx, index, public_key, flag)
    new_tx_ins = []
    for i, txin in enumerate(tx.tx_ins):
        new_tx_ins.append(
            TxIn(
                prev_tx=txin.prev_tx,
                prev_index=txin.prev_index,
                script=txin.script_sig if i != index else bytes_to_script(sig) + txin.script_sig,
                sequence=txin.sequence,
            )
        )

    return Tx(version=tx.version, tx_ins=new_tx_ins, tx_outs=tx.tx_outs, locktime=tx.locktime)


def spend_utxo(
    tx: Tx,
    index: int,
    unlocking_script: Script,
    outputs: list[TxOut],
    index_output: int,
    fee_rate: int,
    network: BlockchainInterface,
):
    """Spend the output at position `index` in `tx` to the `outputs`.

    NOTE: It requires knowledge of the unlocking script needed to spend tx.tx_outs[index].
    """
    spending_tx = Tx(version=1, tx_ins=[tx_to_input(tx, index, unlocking_script)], tx_outs=outputs, locktime=0)

    spending_tx = update_tx_balance(
        spending_tx,
        index_output,
        fee_rate,
    )

    return spending_tx, network.broadcast_tx(spending_tx.serialize().hex())


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
    """Spend a list of P2PK UTXOs specified as a list of transactions and indices.

    Args:
        txs (list[Tx]): The list of transactions from which to get the UTXOs.
        indices (list[int]): indices[i] is the index of the output that should be spent from txs[i].
        outputs (list[TxOut]): List of output to which to spend the UTXOs.
        index_output (int): Index of the output that is paying the transaction fee.
        public_keys (list[Wallet]): public_keys[i] is the public required to spend txs[i].tx_outs[indices[i]].
        fee_rate (int): The fee rate.
        network (BlockchainInterface): The connection to the blockchain.
        flag (SIGHASH): The sighash flag used to create the signatures. Defaults to `SIGHASH.ALL_FORKID`.
    """
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
    """Spend a list of P2PKH UTXOs specified as a list of transactions and indices.

    Args:
        txs (list[Tx]): The list of transactions from which to get the UTXOs.
        indices (list[int]): indices[i] is the index of the output that should be spent from txs[i].
        outputs (list[TxOut]): List of output to which to spend the UTXOs.
        index_output (int): Index of the output that is paying the transaction fee.
        public_keys (list[Wallet]): public_keys[i] is the public required to spend txs[i].tx_outs[indices[i]].
        fee_rate (int): The fee rate.
        network (BlockchainInterface): The connection to the blockchain.
        flag (SIGHASH): The sighash flag used to create the signatures. Defaults to `SIGHASH.ALL_FORKID`.
    """
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


def p2pk_script(public_key: Wallet) -> Script:
    """Generate the P2PK locking script for `public_key`."""
    out = Script()
    out.append_pushdata(bytes.fromhex(public_key.get_public_key_as_hexstr()))
    out += Script.parse_string("OP_CHECKSIG")

    return out


def p2pk(public_key: Wallet, amount: int) -> TxOut:
    """Turn `public_key` and `amount` into a P2PK TxOut."""
    return TxOut(amount=amount, script_pubkey=p2pk_script(public_key))


def p2pkh(public_key: Wallet, amount: int) -> TxOut:
    """Turn `public_key` and `amount` into a P2PKH TxOut."""
    return TxOut(amount=amount, script_pubkey=public_key.get_locking_script())


def tx_from_id(txid: str, network: BlockchainInterface) -> Tx:
    """Retrieve `txid` from the Blockchain and convert it to an instance of `Tx`."""
    return Tx.parse_hexstr(network.get_raw_transaction(txid))


def sign_tx_with_random_k(
    prev_tx: Tx, tx: Tx, index: int, public_key: Wallet, flag: SIGHASH = SIGHASH.ALL_FORKID
) -> list[bytes]:
    """Sign `tx.tx_ins[index]` with a random ephemeral key.

    Args:
        prev_tx (Tx): The transaction generating the output being spent by `tx.tx_ins[index]`.
        tx (Tx): The transaction to be signed.
        index (int): The index of the input of `tx` to be signed.
        public_key (Wallet): The key required to sign `tx.tx_ins[index]`.
        flag (SIGHASH): The sighash flag used to sign `tx.tx_ins[index]`. Defaults to `SIGHASH.ALL_FORKID`.
    """
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
    random_k = randint(2, GROUP_ORDER - 1)  # noqa: S311
    sig = priv_key.sign(msg, random_k)
    der = ecdsa.util.sigencode_der_canonize(sig.r, sig.s, GROUP_ORDER)
    return der + flag.to_bytes()
