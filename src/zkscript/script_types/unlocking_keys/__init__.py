"""Classes to generate unlocking keys associated to scripts.

Modules:
    - groth16 - implement class Groth16UnlockingKey, Groth16UnlockingKeyWithPrecomputedMsm.
    - merkle_tree - implement classes MerkleTreeBitFlagsUnlockingKey and MerkleTreeTwoAuxUnlockingKey.
    - miller_loops- implement classes MillerLoopUnlockingKey and TripleMillerLoopUnlockingKey.
    - msm_with_fixed_bases - implement class MsmWithFixedBasesUnlockingKey.
    - pairings - implement classes SinglePairingUnlockingKey and TriplePairingUnlockingKey.
    - unrolled_ec_multiplication - implement class EllipticCurveFqUnrolledUnlockingKey.
    - transaction_introspection - implement classes PushTxUnlockingKey and PushTxBitShiftUnlockingKey.
"""
