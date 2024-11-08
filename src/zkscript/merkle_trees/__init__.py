"""Merkle tree package.

The `MerkleTree` class implements locking and unlocking scripts to verify Merkle paths.
A MerkleTree instance is initialized by the root, the depth, and the hash function of the tree.
The class provides two pair of methods to generate pairs of locking/unlocking scripts

- `locking_merkle_proof_with_two_aux` and `unlocking_merkle_proof_with_two_aux`
    The locking script checks the validity of a Merkle path for a root `r`, where the Merkle path for an element `d` is defined as a sequence:
            `(d, "", "") (aux_{0,1}, h_1, aux_{1,1}) ... (aux_{0,depth-1}, h_{depth-1}, aux_{1,depth-1})`
    So that:
        - `h_1 = hash(d)`
        - `aux_{0,i}` and `aux_{1,i}` are auxiliary values appended to the left and right of `h_i` so that
            `h_i = hash(aux_{0,i-1} || h_{i-1} || aux_{1,i-1})`
        - `r = hash(aux_{0,depth-1} || h_{depth-1} || aux_{1,depth-1})`

- `locking_merkle_proof_with_bit_flags` and `unlocking_merkle_proof_with_bit_flags`
    The locking script checks the validity of a Merkle path for a root `r`, where the Merkle path for an element `d` is defined as a sequence:
            `(d, "", "") (h_1, aux_1, bit_1) ... (h_{depth-1}, aux_{depth-1}, bit_{depth-1})`
    So that:
        - `h_1 = sef.hash(d)`
        - `bit_i` are values determining if the node is a left or right node, so that
            `h_i = hash(h_{i-1} || aux_{i-1})` if `bit_{i-1} == 0` else `hash(aux_{i-1} || h_{i-1})`
        - `r = hash(h_{depth-1} || aux_{depth-1})` if `bit_{depth-1} == 0` else `hash(aux_{depth-1} || h_{depth-1})`

# Import the MerkleTree class
from src.zkscript.merkle_trees.merkle_tree import MerkleTree

# A Merkle tree whose leaves are defined as OP_HASH160 0x00 = 9f7fd096d37ed2c0e3f7f0cfc924beef4ffceb68 and OP_HASH160 0x01 = c51b66bced5e4491001bd702669770dccf440982
tree = MerkleTree(
    root= "e1154e815712cd04b9c856c4318d3674e2b2bb91",
    hash_function= "OP_HASH160",
    depth= 1
)

# The following is the script that generates a locking script
lock = tree.locking_merkle_proof_with_two_aux()

# The following is the script that generates the unlocking script for each of the leaves
unlock0 = tree.unlocking_merkle_proof_with_two_aux(d= "00", aux_left = [""], aux_right = ["c51b66bced5e4491001bd702669770dccf440982"])
unlock1 = tree.unlocking_merkle_proof_with_two_aux(d= "01", aux_left = ["9f7fd096d37ed2c0e3f7f0cfc924beef4ffceb68"], aux_right = [""])

"""
