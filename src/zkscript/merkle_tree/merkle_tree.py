import string

from tx_engine import Script


class MerkleTree:
    """Class implementing methods to generate locking for Merkle paths verification."""

    def __init__(self, root: str, hash_function: str, depth: int):
        """Initialize a MerkleTree instance.

        Args:
            root (str): The root hash of the Merkle Tree, provided as a hexadecimal string.
            hash_function (str): Hash function used in the Merkle Tree, the hash function must be a valid hash opcode or
                a sequence of valid hash opcodes. Valid hash opcodes are `OP_RIPEMD160, OP_SHA1, OP_SHA256, OP_HASH160,`
                `OP_HASH256`
            depth (int): Number of levels in the Merkle tree.

        Raises:
            AssertionError: If `root` is not a hexadecimal or `hash_function` contains invalid opcodes.

        """
        assert all(c in string.hexdigits for c in root), f"{root} is not a valid hexadecimal string."

        assert set(hash_function.split(" ")).issubset(
            {"OP_RIPEMD160", "OP_SHA1", "OP_SHA256", "OP_HASH160", "OP_HASH256"}
        ), f"{hash_function} is not a valid hash function."

        assert depth > 0

        self.root = root
        self.hash_function = hash_function
        self.depth = depth

    def locking_merkle_proof_with_bit_flags(
        self,
        is_equal_verify: bool = False,
    ) -> Script:
        """Generate locking scripts for Merkle path verification using a bit flag to identify right and left nodes.

        Stack input:
            - stack:    [aux_{depth - 1}, bit_{depth-1}, ..., aux_1, bit_1, d]
            - altstack: []

        Stack output:
            - stack:    ([1] if not is_equal_verify, else []) if the Merkle proof is valid
                        ([0] if not is_equalverify, else stack evaluation error) if the Merkle proof is not valid
            - altstack: []

        Args:
            is_equal_verify (bool): If `True`, use `OP_EQUALVERIFY` in the final verification step, otherwise
                `OP_EQUAL`. Default to `False`.

        Returns:
            Locking script for verifying a Merkle path using a bit flag to identify right and left nodes.

        Notes:
            - Assumes `self.hash_function` is a valid Bitcoin Script hash function (e.g., `OP_SHA256`).
            - `self.root` should be set to the expected Merkle root.

        """

        out = Script()

        # stack in: [..., aux_i, bit_i, ..., d]
        # stack out: [<purported r>]
        out += Script.parse_string(self.hash_function)
        out += Script.parse_string(
            " ".join([f"OP_SWAP OP_IF OP_SWAP OP_ENDIF OP_CAT {self.hash_function}"] * (self.depth - 1))
        )

        # stack in: [<purported r>]
        # stack out: [fail if <purported r> != self.root else 1]
        out.append_pushdata(bytes.fromhex(self.root))
        out += Script.parse_string("OP_EQUALVERIFY") if is_equal_verify else Script.parse_string("OP_EQUAL")

        return out

    def locking_merkle_proof_with_two_aux(
        self,
        is_equal_verify: bool = False,
    ) -> Script:
        """Generate locking scripts for Merkle path verification with two auxiliary inputs per level.

        Stack input:
            - stack:    [aux_{0, depth - 1}, aux_{1, depth - 1}, ..., aux_{0,1}, aux_{1,1}, d]
            - altstack: []

        Stack output:
            - stack:    ([1] if not is_equal_verify, else []) if the Merkle proof is valid
                        ([0] if not is_equalverify, else stack evaluation error) if the Merkle proof is not valid
            - altstack: []

        Args:
            is_equal_verify (bool): If `True`, use `OP_EQUALVERIFY` in the final verification step, otherwise
                `OP_EQUAL`.

        Returns:
            Locking script for verifying a Merkle path using pairs of auxiliary values.

        Notes:
            - Requires `self.hash_function` to be a valid Bitcoin Script hash function (e.g., `OP_SHA256`).
            - `self.root` must be set to the expected Merkle root.

        """
        out = Script()

        # stack in: [..., aux_{0,i}, aux_{1,i}, ..., d]
        # stack out: <purported r>
        out += Script.parse_string(self.hash_function)
        out += Script.parse_string(" ".join([f"OP_SWAP OP_CAT OP_CAT {self.hash_function}"] * (self.depth - 1)))

        # stack in: [<purported r>]
        # stack out: [fail if <purported r> != self.root else 1]
        out.append_pushdata(bytes.fromhex(self.root))
        out += Script.parse_string("OP_EQUALVERIFY") if is_equal_verify else Script.parse_string("OP_EQUAL")

        return out
