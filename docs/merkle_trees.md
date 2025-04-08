# Merkle trees

The class [`MerkleTree`](https://github.com/nchain-innovation/zkscript_package/blob/2aff19f031700c8a773cae3d16b48d427f44c2fc/src/zkscript/merkle_tree/merkle_tree.py#L8) implements methods to generate scripts for Merkle path verification.

The initialisation method requires three arguments, which define the Merkle tree:
- The Merkle root `root`
- The hash function `hash_function`, which can be any combination of the hash functions available in Bitcoin Script: `OP_SHA1`, `OP_SHA256`, `OP_HASH256`, `OP_RIPEMD160`, `OP_HASH160`
- The depth `depth` of the Merkle tree

The class `MerkleTree` implements two scripts for Merkle path verification:
- [`locking_merkle_proof_with_two_bit_flags`](https://github.com/nchain-innovation/zkscript_package/blob/2aff19f031700c8a773cae3d16b48d427f44c2fc/src/zkscript/merkle_tree/merkle_tree.py#L37)
- [`locking_merkle_proof_with_two_aux`](https://github.com/nchain-innovation/zkscript_package/blob/2aff19f031700c8a773cae3d16b48d427f44c2fc/src/zkscript/merkle_tree/merkle_tree.py#L80)

The scripts differ for the type of data that the spender must supply to satisfy the locking script.
We refer the reader to the documentation and to the blogpost [Merkle trees in Bitcoin Script](https://hackmd.io/@federicobarbacovi/BybFoBplJx) for a detailed explanation.

The unlocking scripts for the methods contained in the class  `MerkleTree` can be generated using the unlocking keys found in [src/zkscript/script_types/unlocking_keys/merkle_tree](../src/zkscript/script_types/unlocking_keys/merkle_tree.py).