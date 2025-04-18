"""transaction_introspection package.

This package provides modules for constructing Bitcoin scripts for transaction introspection.

Modules:
    - transaction_introspection: Contains the TransactionIntrospection class for scripts that achieve
        transaction introspection. Reference for implementation: https://hackmd.io/@federicobarbacovi/By6zkFmfyl

Usage example:
    >>> from tx_engine import SIGHASH
    >>> from src.zkscript.transaction_introspection.transaction_introspection import TransactionIntrospection
    >>>
    >>> pushtx_script = TransactionIntrospection.pushtx(sighash_value=SIGHASH.ALL_FORKID)
"""
