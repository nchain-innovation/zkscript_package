import string

from tx_engine import Script


class MerkleTree:
    """Class implementing methods to generate locking/unlocking scripts verifying Merkle paths."""

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

    def unlocking_merkle_proof_with_bit_flags(
        self,
        d: str,
        aux: list[str],
        bit: list[bool],
    ) -> Script:
        """Generate unlocking scripts for Merkle path verification using a bit flag to identify the right and left path.

        The unlocking script loads the data on the stack, sorthing them as following:

        Stack input:
            - stack:    []
            - altstack: []

        Stack output:
            - stack:    [aux_{depth - 1} bit_{depth-1} ... aux_1 bit_1 d]
            - altstack: []

        Args:
            d (str): Data for which the Merkle root is being proved, as a hexadecimal string.
            aux (list[str]): List of hexadecimal strings representing auxiliary data.
            bit (list[bool]): List of boolean values specifying if the current node is a left or right child.

        Returns:
            Unlocking script for use with `locking_merkle_proof_with_bit_flags`.

        Raises:
            AssertionError: If `d`, `aux`, or `bit` have invalid formats or incorrect lengths.

        """

        assert all(c in string.hexdigits for c in d)
        assert all(
            c in string.hexdigits for aux_ in aux for c in aux_
        ), f"{aux} is not a valid list of hexadecimal strings."
        assert len(bit) == self.depth - 1, f"{aux} must be of lenght {self.depth - 1}."
        assert len(aux) == self.depth - 1, f"{aux} must be of lenght {self.depth - 1}."

        out = Script()

        for aux_, bit_ in zip(aux, bit):
            out.append_pushdata(bytes.fromhex(aux_))
            out += Script.parse_string("OP_1" if bit_ else "OP_0")

        out.append_pushdata(bytes.fromhex(d))

        return out

    def locking_merkle_proof_with_bit_flags(
        self,
        is_equal_verify: bool = False,
    ) -> Script:
        """Generate locking scripts for Merkle path verification using a bit flag to identify right and left nodes.

        Stack input:
            - stack:    [aux_{depth - 1} bit_{depth-1} ... aux_1 bit_1 d]
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

        # stack in: [... aux_i bit_i ... d]
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

    def unlocking_merkle_proof_with_two_aux(
        self,
        d: str,
        aux_left: list[str],
        aux_right: list[str],
    ) -> Script:
        """Generate unlocking scripts to verify a Merkle path with two auxiliary inputs per level.

        Stack input:
            - stack:    []
            - altstack: []

        Stack output:
            - stack:    [aux_{0, depth - 1} aux_{1, depth - 1} ... aux_{0,1} aux_{1,1} d]
            - altstack: []

        Args:
            d (str): Data being verified in the Merkle root, as a hexadecimal string.
            aux_left (list[str]): List of hexadecimal strings for the left-side auxiliary data per level.
            aux_right (list[str]): List of hexadecimal strings for the right-side auxiliary data per level.

        Returns:
            Unlocking script for use with `locking_merkle_proof_with_two_aux`.

        Raises:
            AssertionError: If `d`, `aux_left`, or `aux_right` have invalid formats or incorrect lengths.

        """

        assert all(
            c in string.hexdigits for node in aux_left for c in node
        ), f"{aux_left} is not a valid list of hexadecimal strings."
        assert all(
            c in string.hexdigits for node in aux_right for c in node
        ), f"{aux_right} is not a valid list of hexadecimal strings."
        assert len(aux_right) == self.depth - 1, f"{aux_right} must be of lenght {self.depth - 1}."
        assert len(aux_left) == self.depth - 1, f"{aux_left} must be of lenght {self.depth - 1}."

        out = Script()

        for aux_l, aux_r in zip(aux_left, aux_right):
            out.append_pushdata(bytes.fromhex(aux_l))
            out.append_pushdata(bytes.fromhex(aux_r))

        out.append_pushdata(bytes.fromhex(d))

        return out

    def locking_merkle_proof_with_two_aux(
        self,
        is_equal_verify: bool = False,
    ) -> Script:
        """Generate locking scripts for Merkle path verification with two auxiliary inputs per level.

        Stack input:
            - stack:    [aux_{depth - 1} bit_{depth-1} ... aux_1 bit_1 d]
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

        # stack in: [... aux_{0,i} aux_{1,i} ... d]
        # stack out: <purported r>
        out += Script.parse_string(self.hash_function)
        out += Script.parse_string(" ".join([f"OP_SWAP OP_CAT OP_CAT {self.hash_function}"] * (self.depth - 1)))

        # stack in: [<purported r>]
        # stack out: [fail if <purported r> != self.root else 1]
        out.append_pushdata(bytes.fromhex(self.root))
        out += Script.parse_string("OP_EQUALVERIFY") if is_equal_verify else Script.parse_string("OP_EQUAL")

        return out
