"""secp256k1 package.

This package provides scripts to efficiently compute compute scalar point multiplication on secp256k1.

Modules:
    - secp256k1: Implements the class Secp256k1 which has methods:
        - verify_base_point_multiplication_up_to_epsilon: Verifies that A = (±a + additional_constant + epsilon)G
        - verify_base_point_multiplication: Verifies that A = aG
        - verify_point_multiplication_up_to_sign: Verifies that Q = ± bP
        - verify_point_multiplication: Verifies that Q = bP
"""
