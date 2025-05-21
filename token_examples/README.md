 # NFT with recursive Groth16

This folder provides a Proof-of-Concept implementation of an NFT protocol based on recursive Groth16, and of Proof-of-Burn using recursive Groth16.
The folder contains two subfolders:
- [`nft`](./nft/): This folder contains:
    - [`nft_proof_system`](./nft/nft_proof_system/): A Rust crate containing the application that can be used to generate and verify proofs related to the NFTs.
    See the [README](./nft/nft_proof_system/README.md) for more information.
    - [`tcp.ipynb`](./nft/tcp.ipynb): A Jupyter notebook containing a step-by-step guide on how to publish and transfer the NFTs on-chain.
    - [`tcp_utils.py`](./nft/tcp_utils.py): Utilites used in the Jupyter notebook
- [`proof_of_burn`](./proof_of_burn/): This folder contains:
    - [`burn_proof_system`](./proof_of_burn/burn_proof_system/): A Rust crate containing the application that can be used to generate and verify proofs related to the Proof-of-Burn.
    - ['tcp_proof_system](./proof_of_burn/tcp_proof_system/): A Rust crate containing the application that can be used to generate and verify proofs releated to the transaction chain that we want to burn. See the [README](./proof_of_burn/tcp_proof_system/README.md) for more information.
    - [`proof_of_brun.ipynb`](./nft/tcp.ipynb): A Jupyter notebook containing a step-by-step guide on how to publish a proof of burn.
    - [`utils.py`](./nft/tcp_utils.py): Utilites used in the Jupyter notebook
