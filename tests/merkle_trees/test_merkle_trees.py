from dataclasses import dataclass

import pytest
from tx_engine import Context

from src.zkscript.merkle_trees.merkle_tree import MerkleTree as MerkleTreeScript
from src.zkscript.merkle_trees.merkle_tree import MerkleTreeUnlockingKey
from tests.fields.util import save_scripts


@dataclass
class MerkleTree:
    filename = "merkle_tree"
    test_data = {
        "test_merkle_proof_with_bit_flags": [
            {
                "root": "06e2b4a68e27b8661515e80856f646822b484031",
                "hash_function": "OP_SHA1",
                "depth": 3,
                "d": "31",
                "aux": ["8f3a69f10ebffc2653e861222f16b178f583005f", "da4b9237bacccdf19c0760cab7aec4a8359010b0"],
                "bit": [True, True],
            },
            {
                "root": "308c48313fb1f8ebaca4328e4f527034c2f1199f",
                "hash_function": "OP_RIPEMD160",
                "depth": 3,
                "d": "34",
                "aux": ["5ab77c5820a082a8915ad180fb83bb256a7c090e", "792c23ea284363927133cd009cf2c08937265d11"],
                "bit": [False, False],
            },
            {
                "root": "cd53a2ce68e6476c29512ea53c395c7f5d8fbcb4614d89298db14e2a5bdb5456",
                "hash_function": "OP_SHA256",
                "depth": 3,
                "d": "31",
                "aux": [
                    "20ab747d45a77938a5b84c2944b8f5355c49f21db0c549451c6281c91ba48d0d",
                    "d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35",
                ],
                "bit": [True, True],
            },
            {
                "root": "a372c01ebadf339a8fed4b8e825bdd849e851ada",
                "hash_function": "OP_HASH160",
                "depth": 3,
                "d": "32",
                "aux": ["d59e71d16c79d58f5323604af61867f999f73a56", "431ecec94e0a920a7972b084dcfabbd69f616912"],
                "bit": [True, False],
            },
            {
                "root": "8b186d4723474e69fd14c28384063e2031d5da66b97844d5973a9e9bf7dcfeeb",
                "hash_function": "OP_HASH256",
                "depth": 3,
                "d": "34",
                "aux": [
                    "7de236613dd3d9fa1d86054a84952f1e0df2f130546b394a4d4dd7b76997f607",
                    "80903da4e6bbdf96e8ff6fc3966b0cfd355c7e860bdd1caa8e4722d9230e40ac",
                ],
                "bit": [False, False],
            },
            {
                "root": "c7fa76d92d71dfc73c568f967e63426b27513a18dad91e5d2e300079496404bf",
                "hash_function": "OP_HASH160 OP_HASH256",
                "depth": 3,
                "d": "31",
                "aux": [
                    "fb057c3128e1d9b34629644de47e54d3bc667fb88e92a728bc3bd22733365f1e",
                    "5c3520446f1dfaf360f094a6e15ed666d256713b34f9119d6f11353a4a64c71a",
                ],
                "bit": [True, True],
            },
        ],
        "test_merkle_proof_with_two_aux": [
            {
                "root": "06e2b4a68e27b8661515e80856f646822b484031",
                "hash_function": "OP_SHA1",
                "depth": 3,
                "d": "34",
                "aux_left": ["58c6912831df431a52af3cd818caa352f60d8db0", "77de68daecd823babbb58edb1c8e14d7106e83bb"],
                "aux_right": ["", ""],
            },
            {
                "root": "308c48313fb1f8ebaca4328e4f527034c2f1199f",
                "hash_function": "OP_RIPEMD160",
                "depth": 3,
                "d": "33",
                "aux_left": ["5ab77c5820a082a8915ad180fb83bb256a7c090e", ""],
                "aux_right": ["", "4b7a392369bdfb8f763a4d6093486e7cafb5cddc"],
            },
            {
                "root": "cd53a2ce68e6476c29512ea53c395c7f5d8fbcb4614d89298db14e2a5bdb5456",
                "hash_function": "OP_SHA256",
                "depth": 3,
                "d": "34",
                "aux_left": [
                    "4295f72eeb1e3507b8461e240e3b8d18c1e7bd2f1122b11fc9ec40a65894031a",
                    "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce",
                ],
                "aux_right": ["", ""],
            },
            {
                "root": "a372c01ebadf339a8fed4b8e825bdd849e851ada",
                "hash_function": "OP_HASH160",
                "depth": 3,
                "d": "34",
                "aux_left": ["518ec376428ad28b030b548011fd8456b549aae7", "2cf943e7720652c2924a0737761377ccc679ab57"],
                "aux_right": ["", ""],
            },
            {
                "root": "8b186d4723474e69fd14c28384063e2031d5da66b97844d5973a9e9bf7dcfeeb",
                "hash_function": "OP_HASH256",
                "depth": 3,
                "d": "31",
                "aux_left": ["", ""],
                "aux_right": [
                    "16b141879dbef5730ce48f085b786780c2ab8bbe20ac6ae6d8c7c679668ec545",
                    "0c08173828583fc6ecd6ecdbcca7b6939c49c242ad5107e39deb7b0a5996b903",
                ],
            },
            {
                "root": "c7fa76d92d71dfc73c568f967e63426b27513a18dad91e5d2e300079496404bf",
                "hash_function": "OP_HASH160 OP_HASH256",
                "depth": 3,
                "d": "33",
                "aux_left": ["275c62341955b76d710a4fab32313c75a105135adfbdb586553b7f12d876389f", ""],
                "aux_right": ["", "9d78aac6d93dc8f7ef9ddb98bf05f24623d7d697e2ae2fe901f0f8ae330894c4"],
            },
        ],
    }


@pytest.mark.parametrize(
    ("root", "hash_function", "depth", "d", "aux", "bit"),
    [
        (
            test_case["root"],
            test_case["hash_function"],
            test_case["depth"],
            test_case["d"],
            test_case["aux"],
            test_case["bit"],
        )
        for test_case in MerkleTree.test_data["test_merkle_proof_with_bit_flags"]
    ],
)
def test_merkle_proof_with_bit_flags(root, hash_function, depth, d, aux, bit, save_to_json_folder):
    merkle_tree = MerkleTreeScript(root=root, hash_function=hash_function, depth=depth)
    unlocking_key = MerkleTreeUnlockingKey(algorithm="bit_flag", data=d, aux=aux, bit=bit)
    lock = merkle_tree.locking_merkle_proof_with_bit_flags()
    unlock = unlocking_key.to_unlocking_script(merkle_tree=merkle_tree)
    context = Context(script=unlock + lock)
    assert context.evaluate()

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, MerkleTree.filename, "merkle_proof_with_bit_flags")


@pytest.mark.parametrize(
    ("root", "hash_function", "depth", "d", "aux_left", "aux_right"),
    [
        (
            test_case["root"],
            test_case["hash_function"],
            test_case["depth"],
            test_case["d"],
            test_case["aux_left"],
            test_case["aux_right"],
        )
        for test_case in MerkleTree.test_data["test_merkle_proof_with_two_aux"]
    ],
)
def test_merkle_proof_with_two_aux(root, hash_function, depth, d, aux_left, aux_right, save_to_json_folder):
    merkle_tree = MerkleTreeScript(root=root, hash_function=hash_function, depth=depth)
    unlocking_key = MerkleTreeUnlockingKey(algorithm="two_aux", data=d, aux_left=aux_left, aux_right=aux_right)

    lock = merkle_tree.locking_merkle_proof_with_two_aux()
    unlock = unlocking_key.to_unlocking_script(merkle_tree=merkle_tree)
    context = Context(script=unlock + lock)
    assert context.evaluate()

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, MerkleTree.filename, "merkle_proof_with_two_aux")
