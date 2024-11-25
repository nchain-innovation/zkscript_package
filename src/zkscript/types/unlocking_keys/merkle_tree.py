import string
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from tx_engine import Script

from src.zkscript.merkle_tree.merkle_tree import MerkleTree


@dataclass
class MerkleTreeBitFlagsUnlockingKey:
    """Class for generating unlocking scripts to verify Merkle paths using bit flags.

    Attributes:
        data: The data being verified, as a hexadecimal string.
        aux: The list of labels used in the Merkle path.
        bit: A list of booleans representing the position of the nodes in the Merkle path.
        path_data: The Merkle path for the data, containing auxiliary data and bit flags.

    """

    data: str
    aux: Optional[List[str]] = field(default=None)
    bit: Optional[List[bool]] = field(default=None)
    path_data: Optional[List[Tuple[str, bool]]] = field(init=False)

    def __post_init__(self):
        """Validate inputs and initialize path_data.

        Raises:
            AssertionError: Raised if
                - `aux` is not provided.
                - `bit` is not provided.
                - The length of `bit` does not match the length of `aux`.
                - `aux` elements are not hexadecimal strings.
                - `data` is not an hexadecimal sting.

        """
        assert self.aux is not None, f"{self.aux} should be a list of strings"
        assert self.bit is not None, f"{self.bit} should be a list of strings"
        assert len(self.bit) == len(self.aux), f"{self.bit} and {self.aux} should have the same lenght"
        assert all(
            c in string.hexdigits for node in self.aux for c in node
        ), f"{self.aux} is not a valid list of hexadecimal strings"
        assert all(c in string.hexdigits for c in self.data)

        # Initialize path_data
        self.path_data = list(zip(self.aux, self.bit))

    def to_unlocking_script(self, merkle_tree: MerkleTree) -> Script:
        """Generate the unlocking script for a Merkle proof verification using bit flags.

        Stack input:
            stack:    []
            altstack: []

        Stack output:
            stack:   [aux_{depth - 1}, bit_{depth - 1}, ..., aux_1, bit_1, d]
            altstack:[]

        Args:
            merkle_tree (MerkleTree): The MerkleTree instance containing the depth information.

        Returns:
            An unlocking script corresponding to the locking script generated by `locking_merkle_proof_with_bit_flags`.

        Raises:
            AssertionError: Raised if
                - the lengths of `self.path_data[0]` or `self.path_data[1]` do not match `merkle_tree.depth - 1`.

        """
        assert (
            len(self.path_data[0]) == merkle_tree.depth - 1
        ), f"{self.path_data[0]} must be of lenght {merkle_tree.depth - 1}."
        assert (
            len(self.path_data[1]) == merkle_tree.depth - 1
        ), f"{self.path_data[1]} must be of lenght {merkle_tree.depth - 1}."

        out = Script()

        for aux_, bit_ in self.path_data:
            out.append_pushdata(bytes.fromhex(aux_))
            out += Script.parse_string("OP_1" if bit_ else "OP_0")

        out.append_pushdata(bytes.fromhex(self.data))

        return out


@dataclass
class MerkleTreeTwoAuxUnlockingKey:
    """Class implementing methods to generate unlocking scripts verifying Merkle paths using two auxiliary values.

    Attributes:
        data: the data being verified.
        aux_left: list of node labels. If the a right node is required in the Merkle path, an empty string is used.
        aux_right: list of node labels. If the a left node is required in the Merkle path, an empty string is used.
        path_data: the Merkle path of the data, formatted accordingly to the locking script.

    """

    data: str
    aux_left: Optional[List[str]] = field(default=None)
    aux_right: Optional[List[str]] = field(default=None)
    path_data: Optional[List[Tuple[str, str]]] = field(init=False)

    def __post_init__(self):
        """Validate inputs and initialize path_data.

        Raises:
            AssertionError: Raised if
                - `aux_left` is not provided.
                - `aux_right` is not provided.
                - The length of `aux_left` does not match the length of `aux_right`.
                - `aux_left` elements are not hexadecimal strings.
                - `aux_right` elements are not hexadecimal strings.
                - `data` is not an hexadecimal sting.

        """
        assert self.aux_left is not None, f"{self.aux_left} should be a list of strings"
        assert self.aux_right is not None, f"{self.aux_right} should be a list of strings"
        assert len(self.aux_left) == len(
            self.aux_right
        ), f"{self.aux_left} and {self.aux_right} should have the same lenght"
        assert all(
            c in string.hexdigits for node in self.aux_left for c in node
        ), f"{self.aux_left} is not a valid list of hexadecimal strings"
        assert all(
            c in string.hexdigits for node in self.aux_right for c in node
        ), f"{self.aux_left} is not a valid list of hexadecimal strings"
        assert all(c in string.hexdigits for c in self.data)

        # Initialize path_data
        self.path_data = list(zip(self.aux_left, self.aux_right))

    def to_unlocking_script(self, merkle_tree: MerkleTree) -> Script:
        """Generate the unlocking script for a Merkle proof verification using two auxiliary values.

        Stack input:
            stack:    []
            altstack: []

        Stack output:
            stack:   [aux_{0, depth - 1}, aux_{1, depth - 1}, ..., aux_{0,1}, aux_{1,1}, d]
            altstack:[]

        Args:
            merkle_tree (MerkleTree): The MerkleTree instance containing the depth information.

        Returns:
            An unlocking script corresponding to the locking script generated by `locking_merkle_proof_with_two_aux`.

        Raises:
            AssertionError: Raised if
                - the lengths of `self.path_data[0]` or `self.path_data[1]` do not match `merkle_tree.depth - 1`.

        """
        assert (
            len(self.path_data[0]) == merkle_tree.depth - 1
        ), f"{self.path_data[0]} must be of lenght {merkle_tree.depth - 1}."
        assert (
            len(self.path_data[1]) == merkle_tree.depth - 1
        ), f"{self.path_data[1]} must be of lenght {merkle_tree.depth - 1}."

        out = Script()

        for aux_l, aux_r in self.path_data:
            out.append_pushdata(bytes.fromhex(aux_l))
            out.append_pushdata(bytes.fromhex(aux_r))

        out.append_pushdata(bytes.fromhex(self.data))

        return out
