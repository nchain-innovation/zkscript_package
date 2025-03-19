 # Proof-of-Burn with recursive Groth16

This folder provides a Proof-of-Concept implementation of Proof-of-Burn using recursive Groth16.
The folder contains a subfolder:
- [`proof_of_burn`](./proof_of_burn/): This folder contains:
    - [`burn_proof_system`](./proof_of_burn/burn_proof_system/): A Rust crate containing the application that can be used to generate and verify proofs related to the Proof-of-Burn.
    - ['tcp_proof_system](./proof_of_burn/tcp_proof_system/): A Rust crate containing the application that can be used to generate and verify proofs releated to the transaction chain that we want to burn. See the [README](./proof_of_burn/tcp_proof_system/README.md) for more information.
    - [`proof_of_brun.ipynb`](./nft/tcp.ipynb): A Jupyter notebook containing a step-by-step guide on how to publish a proof of burn.
    - [`utils.py`](./nft/tcp_utils.py): Utilites used in the Jupyter notebook