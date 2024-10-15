from dataclasses import dataclass

import pytest
from tx_engine import Context

from src.zkscript.merkle_trees.merkle_tree import MerkleTree as MerkleTreeScript
from tests.fields.util import save_scripts


@dataclass
class MerkleTree:
    filename = "merkle_tree"
    test_data = {
        "test_merkle_proof_one_path": [
            {
                "root": "DF2B71F6EB25B9768FF32A8105911D193A350EB8",
                "hash_function": "OP_SHA1",
                "nodes": ["01"],
                "is_nodes_left": [True],
                "expected": "03",
            },
            {
                "root": "DF2B71F6EB25B9768FF32A8105911D193A350EB8",
                "hash_function": "OP_SHA1",
                "nodes": ["03"],
                "is_nodes_left": [False],
                "expected": "01",
            },
            {
                "root": "F2E62A6673C82C23F28E53DEF8BE321601ECA0CE",
                "hash_function": "OP_RIPEMD160",
                "nodes": ["01"],
                "is_nodes_left": [True],
                "expected": "03",
            },
            {
                "root": "F2E62A6673C82C23F28E53DEF8BE321601ECA0CE",
                "hash_function": "OP_RIPEMD160",
                "nodes": ["03"],
                "is_nodes_left": [False],
                "expected": "01",
            },
            {
                "root": "C79B932E1E1DA3C0E098E5AD2C422937EB904A76CF61D83975A74A68FBB04B99",
                "hash_function": "OP_SHA256",
                "nodes": ["01"],
                "is_nodes_left": [True],
                "expected": "03",
            },
            {
                "root": "C79B932E1E1DA3C0E098E5AD2C422937EB904A76CF61D83975A74A68FBB04B99",
                "hash_function": "OP_SHA256",
                "nodes": ["03"],
                "is_nodes_left": [False],
                "expected": "01",
            },
            {
                "root": "E1E6277712F9ED0E1FBD550923F2F65B7F27C1BA",
                "hash_function": "OP_HASH160",
                "nodes": ["01"],
                "is_nodes_left": [True],
                "expected": "03",
            },
            {
                "root": "E1E6277712F9ED0E1FBD550923F2F65B7F27C1BA",
                "hash_function": "OP_HASH160",
                "nodes": ["03"],
                "is_nodes_left": [False],
                "expected": "01",
            },
            {
                "root": "6F7AE8621A432300884F6F8042FDDFF01FC887B045D314E6C5932D7DD3A01C56",
                "hash_function": "OP_HASH256",
                "nodes": ["01"],
                "is_nodes_left": [True],
                "expected": "03",
            },
            {
                "root": "6F7AE8621A432300884F6F8042FDDFF01FC887B045D314E6C5932D7DD3A01C56",
                "hash_function": "OP_HASH256",
                "nodes": ["03"],
                "is_nodes_left": [False],
                "expected": "01",
            },
            {
                "root": "5FC030E11BE8E1685B845A2D1357FE8F63B88FF3",
                "hash_function": "OP_HASH256 OP_HASH160",
                "nodes": ["01"],
                "is_nodes_left": [True],
                "expected": "03",
            },
            {
                "root": "5FC030E11BE8E1685B845A2D1357FE8F63B88FF3",
                "hash_function": "OP_HASH256 OP_HASH160",
                "nodes": ["03"],
                "is_nodes_left": [False],
                "expected": "01",
            },
            {
                "root": "65998769A2DF355E9D0C55BDB7794C5ECA8F53D4",
                "hash_function": "OP_HASH160",
                "nodes": ["01", "0DA2D4860836BC7D2B446AE90DC158735C3666A2"],
                "is_nodes_left": [True, False],
                "expected": "03",
            },
            {
                "root": "65998769A2DF355E9D0C55BDB7794C5ECA8F53D4",
                "hash_function": "OP_HASH160",
                "nodes": ["03", "0DA2D4860836BC7D2B446AE90DC158735C3666A2"],
                "is_nodes_left": [False, False],
                "expected": "01",
            },
            {
                "root": "65998769A2DF355E9D0C55BDB7794C5ECA8F53D4",
                "hash_function": "OP_HASH160",
                "nodes": ["05", "E1E6277712F9ED0E1FBD550923F2F65B7F27C1BA"],
                "is_nodes_left": [True, True],
                "expected": "07",
            },
            {
                "root": "65998769A2DF355E9D0C55BDB7794C5ECA8F53D4",
                "hash_function": "OP_HASH160",
                "nodes": ["07", "E1E6277712F9ED0E1FBD550923F2F65B7F27C1BA"],
                "is_nodes_left": [False, True],
                "expected": "05",
            },
        ],
        # "test_merkle_proof_any_path": [{"root": a, "hash_function": a, "depth": a, "left_path": a, "right_path": a}],
    }


def extract_test_case(config, data):
    is_one_path = "nodes" in data and "is_nodes_left" in data

    test = None

    if is_one_path:
        test = (config, data["root"], data["hash_function"], data["nodes"], data["is_nodes_left"], data["expected"])
    else:
        test = (config, data["root"], data["hash_function"], data["depth"], data["expected"])

    return test


def generate_test_cases(test_name):
    # Parse and return config and the test_data for each config
    configurations = [MerkleTree]

    test_cases = [
        extract_test_case(config, test_data)
        for config in configurations
        if test_name in config.test_data
        for test_data in config.test_data[test_name]
    ]

    # Remove any None values returned by extract_test_case
    return [case for case in test_cases if case]


@pytest.mark.parametrize(
    ("config", "root", "hash_function", "nodes", "is_nodes_left", "expected"),
    generate_test_cases("test_merkle_proof_one_path"),
)
def test_merkle_proof_one_path(config, root, hash_function, nodes, is_nodes_left, expected, save_to_json_folder):
    merkle_tree = MerkleTreeScript(root=root, hash_function=hash_function)
    lock = merkle_tree.locking_merkle_proof_one_path(nodes=nodes, is_nodes_left=is_nodes_left)
    unlock = merkle_tree.unlocking_merkle_proof_one_path(node=expected)
    context = Context(script=unlock + lock)
    assert context.evaluate()

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "merkle_proof_one_path")


@pytest.mark.parametrize(
    ("config", "root", "hash_function", "depth", "expected"), generate_test_cases("test_merkle_proof_any_path")
)
def test_merkle_proof_any_path(config, root, hash_function, depth, expected, save_to_json_folder):
    merkle_tree = MerkleTreeScript(root=root, hash_function=hash_function)
    lock = merkle_tree.locking_merkle_proof_any_path(depth=depth)
    unlock = merkle_tree.unlocking_merkle_proof_any_path(node=expected)
    context = Context(script=unlock + lock)
    assert context.evaluate()

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "merkle_proof_one_path")
