"""Merkle tree package.

The `MerkleTree` class implements locking and unlocking scripts to verify Merkle paths.
A MerkleTree instance is initialized by the root, the depth, and the hash function of the tree.
The class provides two pair of methods to generate pairs of locking/unlocking scripts

- `locking_merkle_proof_with_two_aux` and `unlocking_merkle_proof_with_two_aux`
    The locking script checks the validity of a Merkle path for a root `r`, where the Merkle path for an element `d` is
    defined as a sequence:
            `(d, "", "") (aux_{0,1}, h_1, aux_{1,1}) ... (aux_{0,depth-1}, h_{depth-1}, aux_{1,depth-1})`
    So that:
        - `h_1 = hash(d)`
        - `aux_{0,i}` and `aux_{1,i}` are auxiliary values appended to the left and right of `h_i` so that
            `h_i = hash(aux_{0,i-1} || h_{i-1} || aux_{1,i-1})`
        - `r = hash(aux_{0,depth-1} || h_{depth-1} || aux_{1,depth-1})`

- `locking_merkle_proof_with_bit_flags` and `unlocking_merkle_proof_with_bit_flags`
    The locking script checks the validity of a Merkle path for a root `r`, where the Merkle path for an element `d` is
    defined as a sequence:
            `(d, "", "") (h_1, aux_1, bit_1) ... (h_{depth-1}, aux_{depth-1}, bit_{depth-1})`
    So that:
        - `h_1 = sef.hash(d)`
        - `bit_i` are values determining if the node is a left or right node, so that
            `h_i = hash(h_{i-1} || aux_{i-1})` if `bit_{i-1} == 0` else `hash(aux_{i-1} || h_{i-1})`
        - `r = hash(h_{depth-1} || aux_{depth-1})` if `bit_{depth-1} == 0` else `hash(aux_{depth-1} || h_{depth-1})`

Usage example:

    >>> from src.zkscript.merkle_trees.merkle_tree import MerkleTree, MerkleTreeUnlockingKey
    >>> tree = MerkleTree(
    ...     root="e1154e815712cd04b9c856c4318d3674e2b2bb91",
    ...     hash_function="OP_HASH160",
    ...     depth=1
    ... )
    >>> unlocking_key = MerkleTreeUnlockingKey(
    ...     algorithm="two_aux",
    ...     data="00",
    ...     aux_left=[""],
    ...     aux_right=["c51b66bced5e4491001bd702669770dccf440982"]
    ... )
"""
