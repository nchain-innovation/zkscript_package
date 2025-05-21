# NFT

This crate provides an interface to use the PCD predicate [`UniversalTransactionChainProofPredicate`](https://github.com/nchain-innovation/transaction_chain_proof/blob/638e0467fdfe364183d6268ee89bf5b83379d011/src/predicates/universal_tcp.rs#L57) to generate proofs that certain UTXOs are part of a transaction chain.<sup><a href="#footnote1">1</a></sup>

## Getting started

The library compiles on the nightly toolchain of the Rust compiler.
To install the latest version of Rust, first install rustup by following the instructions here, or via your platform's package manager.
Once rustup is installed, install the Rust toolchain by invoking:

```bash
rustup install nightly
```

## Workflow

We utilise the following terminology:
- An NFT is _minted_ at transaction `genesis_txid` and index `chain_index` if the minting process links the NFT to the UTXO `(genesis_txid, chain_index)`.
- We refer to the NFT minted at transaction `genesis_txid` and index `chain_index` as the NFT `(genesis_txid, chain_index)`.
- A _token UTXO_ for the NFT `(genesis_txid, chain_index)` is a UTXO which is part of a transaction chain<sup><a href="#footnote1">1</a></sup> at index `chain_index` originating at `genesis_txid`.
- A _token transaction_ is a transaction that involves a token UTXO.
- A token transaction for a token UTXO that is part of a transaction chain at index `chain_index` is _valid_ if the token is transferred to the output at index `chain_index`.

### Alice and Bob

The situation is the following: Alice holds a UTXO `utxo` and want to prove to Bob that it is token UTXO for the NFT `(genesis_txid, chain_index)`.
To do so, Alice uses a PCD predicate: [`UniversalTransactionChainProofPredicate`](https://github.com/nchain-innovation/transaction_chain_proof/blob/638e0467fdfe364183d6268ee89bf5b83379d011/src/predicates/universal_tcp.rs#L57).
That is, Alice shows to Bob a zero-knowledge proof that proves that `utxo` is linked to `(genesis_txid, chain_index)` via a transaction chain at index `chain_index`.

To prove such a statement, Alice needs:
- A proving key `pk`
- The purported token utxo `utxo`
- The origin of the chain `(genesis_txid, chain_index)`
- Some other stuff..

To verify a proof, Bob needs:
- A verifying key `vk`
- The purported token utxo `utxo`
- The origin of the chain `(genesis_txid, chain_index)`

### Setup

To generate proving/verifying key, we need to choose a `chain_index`.
Then, the keys can be used to prove/verify statements about _any_ NFT generated at index `chain_index` (that is, the `genesis_txid` is not hard-coded in the keys).

To perform the setup, create a file `setup.toml` and fill it as follows<sup><a href="#footnote2">2</a></sup>

```toml
[chain_parameters]
chain_index = 0
```

Then, execute with `FILE_PATH` equal to the path for `setup.toml`

```zsh
cargo run --release -- --setup --file FILE_PATH
```

This will generate proving and verifying keys in the folder `data/keys` (which will be created if it doesn't exist).

### Prove

To prove that `utxo` at transaction `Tx` and index `chain_index` is a token UTXO for the NFT `(genesis_txid, chain_index)`, create a file `prove.toml` and fill it as follows:

```toml
proof_name = "PROOF_NAME"

[chain_parameters]
chain_index = "CHAIN_INDEX"

[public_inputs]
outpoint_txid = "TX_TXID"
genesis_txid = "GENESIS_TXID"

[witness]
tx = "OPTION<TX>"
prior_proof_path = "OPTION<PRIOR_PROOF_PATH>"
```

where:
- `"PROOF_NAME"` is the name you wish the proof to be saved with.
- `"CHAIN_INDEX"` is equal to `chain_index`.
- `"TX_TXID"` is the txid of `Tx`.
- `"GENESIS_TXID"` is `genesis_txid`.
- `"OPTION<TX>"` and `"OPTION<PRIOR_PROOF_PATH>"` depend on whethere `utxo` is a child of `genesis_txid` or not:
    - If yes, then `"OPTION<TX>" = ""` and `"OPTION<PRIOR_PROOF_PATH>" = ""` (we don't need anything)
    - If no, then `"OPTION<TX>" = <Tx.serialize()>`, where `Tx.serialize()` is the hex serialization of `Tx`, and `"OPTION<PRIOR_PROOF_PATH>"= "PRIOR_PROOF_PATH`, where `PRIOR_PROOF_PATH` is the path of the prior proof (which Alice received when she got the token UTXO<sup><a href="#footnote3">3</a></sup>)

Then, execute with `FILE_PATH` equal to the path for `prove.toml`

```zsh
cargo run --release -- --prove --file FILE_PATH
```

This will generate proving and verifying keys in the folder `data/proofs` (which will be created if it doesn't exist).

Example `prove.toml` files are provided in the folder `/configs/`.

### Verify

To verify that a proof `proof` asserts that `utxo` is a token UTXO for the NFT `(genesis_txid, chain_index)`, create a file `verify.toml` and fill it as follows:

```toml
proof_path = "PROOF_NAME"

[chain_parameters]
chain_index = "CHAIN_INDEX"

[public_inputs]
outpoint_txid = "UTXO_TXID"
genesis_txid = "GENESIS_TXID"
```

where:
- `"PROOF_NAME"` is the name you wish the proof to be saved with.
- `"CHAIN_INDEX"` is equal to `chain_index`.
- `"UTXO_TXID"` is the txid of the transaction containing `utxo`.
- `"GENESIS_TXID"` is `genesis_txid`.

Then, execute with `FILE_PATH` equal to the path for `verify.toml`

```zsh
cargo run --release -- --verify --file FILE_PATH
```

This will generate either output `Valid proof.` if the proof is valid, or `Proof not valid.` if it is not.

Example `verify.toml` files are provided in the folder `/configs/`.

## Footnotes

[<a name="footnote1">1</a>]: See [`transaction_chain_proof`](https://github.com/nchain-innovation/transaction_chain_proof/) for the definition of a transaction chain.

[<a name="footnote2">2</a>]: We use `chain_index = 0` for simplicity. You can change this to `1` without any problem. If you wish to change it to something else, you will need to modify the [transaction configuration](./src/nft/groth16_nft.rs#L57)

[<a name="footnote3">3</a>]: Alice must have received such a proof, as the person holding the token before her either generated the proof without needing a prior base (they held the `(genesis_txid, chain_index)`) or they themselves received a proof of validity for the token UTXO, and then generated a proof.