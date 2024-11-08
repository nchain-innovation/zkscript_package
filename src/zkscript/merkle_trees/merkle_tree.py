import string
from typing import Literal, Union

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

    def locking_merkle_proof_with_two_aux(
        self,
        is_equal_verify: bool = False,
    ) -> Script:
        """Generate locking scripts for Merkle path verification with two auxiliary inputs per level.

        Stack input:
            - stack:    [aux_{0, depth - 1} aux_{1, depth - 1} ... aux_{0,1} aux_{1,1} d]
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


class MerkleTreeUnlockingKey:
    """Class implementing methods to generate unlocking scripts verifying Merkle paths."""

    def __init__(
        self,
        algorithm: Union[Literal["two_aux", "bit_flag"]],
        data: str,
        aux_left: list[str] | None = None,
        aux_right: list[str] | None = None,
        aux: list[str] | None = None,
        bit: list[bool] | None = None,
    ):
        """Initialize a MerkleTree instance.

        Args:
            algorithm (str): A flag determining which Merkle proof algorithm is used. Can be "two_aux" or "bit_flag".
            data (str): Data being verified, passed as a hexadecimal string.
            aux_left (list[str], optional): List of left auxiliary strings in hexadecimal format for the "two_aux"
                algorithm.
            aux_right (list[str], optional): List of right auxiliary strings in hexadecimal format for the "two_aux"
                algorithm.
            aux (list[str], optional): List of auxiliary data in hexadecimal format for the "bit_flag" algorithm.
            bit (list[bool], optional): List of boolean values for the "bit_flag" algorithm.

        Raises:
            AssertionError: Raised if input conditions are not met based on the following conditions:
                - For `algorithm == "two_aux"`:
                    - aux_left (list[str]): Must be provided and contain strings only in hexadecimal format.
                    - aux_right (list[str]): Must be provided and contain strings only in hexadecimal format.
                    - Length of aux_left and aux_right must be the same, ensuring balanced auxiliary inputs.
                - For other algorithms:
                    - aux_left and aux_right (list[str]): Must be provided and contain hexadecimal format strings.
                    - `aux` (list[str]): All elements must be hexadecimal strings.
                    - Length of `bit` and `aux` lists must match, ensuring consistency between bit flags and auxiliary
                        data.

        """
        if algorithm == "two_aux":
            assert aux_left is not None, f"{aux_left} should be a list of strings"
            assert aux_right is not None, f"{aux_right} should be a list of strings"
            assert len(aux_left) == len(aux_right), f"{aux_left} and {aux_right} should have the same lenght"
            assert all(
                c in string.hexdigits for node in aux_left for c in node
            ), f"{aux_left} is not a valid list of hexadecimal strings"
            assert all(
                c in string.hexdigits for node in aux_right for c in node
            ), f"{aux_left} is not a valid list of hexadecimal strings"
            path_data = [aux_left, aux_right]
        else:
            assert aux is not None, f"{aux_left} should be a list of strings"
            assert bit is not None, f"{aux_right} should be a list of strings"
            assert len(bit) == len(aux), f"{bit} and {aux} should have the same lenght"
            assert all(
                c in string.hexdigits for node in aux for c in node
            ), f"{aux} is not a valid list of hexadecimal strings"
            path_data = [aux, bit]

        self.algortihm = algorithm
        self.data = data
        self.path_data = path_data

    def to_unlocking_script(self, merkle_tree: MerkleTree) -> Script:
        """Generate the unlocking script for a Merkle proof verification.

        This method generates an unlocking script to verify a Merkle path against a Merkle root. The unlocking script
        is configured based on the chosen algorithm (either `"two_aux"` or `"bit_flag"`) and produces the necessary
        script commands to validate the data's membership in the Merkle tree.

        For `"two_aux"`, it generates the path using two auxiliary nodes per level:
            - Stack input:    []
            - Stack output:   [aux_{0, depth - 1}, aux_{1, depth - 1}, ..., aux_{0,1}, aux_{1,1}, d]


        For `"bit_flag"`, it generates the path using a bit flags to identify the position of the node:
            - Stack input:    [aux_{depth - 1}, bit_{depth - 1}, ..., aux_1, bit_1, d]
            - Stack output:   []

        Args:
            merkle_tree (MerkleTree): The MerkleTree instance containing the depth information.

        Returns:
            An unlocking script corresponding to the locking script generated by `locking_merkle_proof_with_two_aux` or
            `locking_merkle_proof_with_bit_flags`.

        Raises:
            AssertionError: Raised if
                - the lengths of `self.path_data[0]` or `self.path_data[1]` do not match `merkle_tree.depth - 1`.
                - `self.data` must be a valid hexadecimal string for successful execution.

        """

        assert (
            len(self.path_data[0]) == merkle_tree.depth - 1
        ), f"{self.path_data[0]} must be of lenght {merkle_tree.depth - 1}."
        assert (
            len(self.path_data[1]) == merkle_tree.depth - 1
        ), f"{self.path_data[1]} must be of lenght {merkle_tree.depth - 1}."

        out = Script()

        if self.algortihm == "two_aux":
            for aux_l, aux_r in zip(self.path_data[0], self.path_data[1]):
                out.append_pushdata(bytes.fromhex(aux_l))
                out.append_pushdata(bytes.fromhex(aux_r))
        else:
            for aux_, bit_ in zip(self.path_data[0], self.path_data[1]):
                out.append_pushdata(bytes.fromhex(aux_))
                out += Script.parse_string("OP_1" if bit_ else "OP_0")

        out.append_pushdata(bytes.fromhex(self.data))

        return out
