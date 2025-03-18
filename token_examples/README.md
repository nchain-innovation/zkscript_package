 # NFT with recursive Groth16

This folder provides a Proof-of-Concept implementation of an NFT protocol based on recursive Groth16.
The folder contains a subfolder:
- [`nft`](./nft/): This folder contains:
    - [`nft_proof_system`](./nft/nft_proof_system/): A Rust crate containing the application that can be used to generate and verify proofs related to the NFTs.
    See the [README](./nft_proof_system/README.md) for more information.
    - [`tcp.ipynb`](./nft/tcp.ipynb): A Jupyter notebook containing a step-by-step guide on how to publish and transfer the NFTs on-chain.
    - [`tcp_utils.py`](./nft/tcp_utils.py): Utilites used in the Jupyter notebook