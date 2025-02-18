# NFT with recursive Groth16

This folder provides a Proof-of-Concept implementation of an NFT protocol based on recursive Groth16.
The folder contains two subfolders:
- [nft_proof_system](./nft_proof_system/): A Rust crate containing the application that can be used to generate and verify proofs related to the NFTs.
See the [README](./nft_proof_system/README.md) for more information.
- [bitcoin_interface](./bitcoin_interface/): A subfolder containing the interface between the Rust crate and the blockchain.

Inside the [bitcoin_interface](./bitcoin_interface/) folder there are two `.py` files, which contain some utilities, and a Jupyter notebook.
The jupyter notebook [tcp.ipynb](./bitcoin_interface/tcp.ipynb) provides a step-by-step breakdown of the processes needed to transfer an NFT on-chain.