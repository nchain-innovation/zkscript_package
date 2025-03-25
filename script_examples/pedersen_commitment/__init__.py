"""Pedersen commitment package.

This package provides scripts that implement the Pedersen commitment scheme over secp256k1.

Modules:
    - pedersen_commitment: Implements the class PedersenCommitmentSecp256k1 which has the method
        `commit` that allows to commitment to a certain commitment.
    - pedersen_unlocking_key: Implements the class PedersenCommitmentSecp256k1UnlockingKey which encapsulates
        the data needed to open a commitment to a value `m`.
"""
