from tx_engine import Script


class MerkleTree:
    """Class representing a Merkle Tree.

    This class takes a root hash and a specified hash function to create the Merkle Tree
    structure.

    Attributes:
        root (str): The root hash of the Merkle Tree. Must be a valid hexadecimal value.
        hash_function (str): The hash function used in the Merkle Tree. This must be a valid opcode hash function or a
            combination of valid opcode hash functions.
        depth (int): The depth (number of levels) of the Merkle tree.

    Methods:
        __init__(root: str, hash_function: str): Initializes the Merkle Tree. An assertion is
            performed to ensure the hash function is valid and the root is hexadecimal.

    """

    def __init__(self, root: str, hash_function: str, depth: int):
        assert all(c in "0123456789abcdefABCDEF" for c in root), f"{root} is not a valid hexadecimal string."

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
        """Generate a locking script to verify a Merkle path.

        The locking script returned by this function checks the validity of a Merkle path. For a root r, the
        Merkle path for an element d is defined as a sequence:
            (d, "", "") (h_1, aux_1, bit_1) ... (h_{self.depth-1}, aux_{self.depth-1}, bit_{self.depth-1})
        So that:
            - h_1 = sef.hash(d)
            - h_i = self.hash(h_{i-1} || aux_{i-1}) if bit_{i-1} == 0 else self.hash(aux_{i-1} || h_{i-1})
            - r = self.hash(h_{self.depth-1} || aux_{self.depth-1}) if bit_{self.depth-1} == 0
                    else self.hash(aux_{self.depth-1} || h_{self.depth-1})

        Args:
            is_equal_verify: a boolean variable to choose between `OP_EQUAL` or `OP_EQUALVERIFY` as final opcode in the
                script. Default to `False`.

        Returns:
            A locking script verifying a Merkle path.

        Note:
            - `self.hash_function` must be a combination of valid Bitcoin Script hash functions (e.g., `OP_SHA256`).
            - `self.root` must be set to the expected Merkle root to verify against.
            - the Merkle path is assumed to be passed as unlocking script in the following way:
                stack = [h_{self.depth-1} aux_{self.depth-1} bit_{self.depth-1} ... aux_1 bit_1 d]
        """

        out = Script()

        # stack in: [h_{self.depth-1} aux_{self.depth-1} bit_{self.depth-1} ... h_1 aux_1 bit_1 d]
        # stack out: [<purported r>]
        out += Script.parse_string(self.hash_function)
        out += Script.parse_string(" ".join(
            [f"OP_SWAP OP_IF OP_SWAP OP_ENDIF OP_CAT {self.hash_function}"] * (self.depth-1)
            ))

        # stack in: [<purported r>]
        # stack out: [fail if <purported r> != self.root else 1/""]
        out.append_pushdata(bytes.fromhex(self.root))
        out += Script.parse_string("OP_EQUALVERIFY") if is_equal_verify else Script.parse_string("OP_EQUAL")

        return out

    def locking_merkle_proof_with_two_aux(
        self,
        is_equal_verify: bool = False,
    ) -> Script:
        """Generate a script to verify a Merkle path with two auxiliary inputs per level.

        The locking script returned by this function checks the validity of a Merkle path. For a root r, the
        Merkle path for an element d is defined as a sequence:
            (d, "", "") (aux_{0,1}, h_1, aux_{1,1}) ... (aux_{0,self.depth-1}, h_{self.depth-1}, aux_{1,self.depth-1})
        So that:
            - h_1 = sef.hash(d)
            - h_i = self.hash(aux_{0,i-1} || h_{i-1} || aux_{1,i-1})
            - r = self.hash(aux_{0,self.depth-1} || h_{self.depth-1} || aux_{1,self.depth-1})

        Args:
            is_equal_verify: a boolean variable to choose between `OP_EQUAL` or `OP_EQUALVERIFY` as final opcode in the
                script. Default to `False`.

        Returns:
            A locking script verifying any valid path to the Merkle root.

        Note:
            - `self.hash_function` must be a combination of valid Bitcoin Script hash functions (e.g., `OP_SHA256`).
            - `self.root` must be set to the expected Merkle root to verify against.
            - the Merkle path is assumed to be passed as unlocking script in the following way:
                stack = [aux_{0,self.depth-1} h_{self.depth-1} aux_{1,self.depth-1} ... aux_{0,1} aux_{1,1} d]

        """
        out = Script()

        # stack in: [aux_{0,self.depth-1} h_{self.depth-1} aux_{1,self.depth-1} ... aux_{0,1} aux_{1,1} d]
        # stack out: <purported r>
        out += Script.parse_string(self.hash_function)
        out += Script.parse_string(" ".join(
            [f"OP_SWAP OP_CAT OP_CAT {self.hash_function}"] * (self.depth-1)
            ))

        # stack in: [<purported r>]
        # stack out: [fail if <purported r> != self.root else 1/""]
        out.append_pushdata(bytes.fromhex(self.root))
        out += Script.parse_string("OP_EQUALVERIFY") if is_equal_verify else Script.parse_string("OP_EQUAL")

        return out

    def unlocking_merkle_proof_with_bit_flags(
        self,
        d: str,
        aux: list[str],
        bit: list[bool],
    ) -> Script:
        """Generate the unlocking script to verify a Merkle path.

        Args:
            d (str): The data we are proving aggregation of in the Merkle root.
            aux (list[str]): A list of hexadecimal strings representing the auxiliary data aux_i.
            bit (list[bool]): A list of boolean representing the bit flags.

        Returns:
            The unlocking script for the script generated by `locking_merkle_proof_with_bit_flags`.

        Note:
            - `self.hash_function` must be a combination of valid Bitcoin Script hash functions (e.g., `OP_SHA256`).
            - `self.root` must be set to the expected Merkle root to verify against.

        """
        assert all( c in "0123456789abcdefABCDEF" for c in d)
        assert all(
            c in "0123456789abcdefABCDEF" for aux_ in aux for c in aux_
            ), f"{aux} is not a valid list of hexadecimal strings."

        out = Script()

        for aux_, bit_ in zip(aux, bit):
            out.append_pushdata(bytes.fromhex(aux_))
            out += Script.parse_string("OP_1" if bit_ else "OP_0")

        out.append_pushdata(bytes.fromhex(d))

        return out

    def unlocking_merkle_proof_with_two_aux(
        self,
        d: str,
        aux_left: list[str],
        aux_right: list[str],
    ) -> Script:
        """Generate the unlocking script to verify a Merkle path with two auxiliary inputs per level.

        Args:
            d (str): The data we are proving aggregation of in the Merkle root.
            aux_left (list[str]): A list of hexidecimal strings representing the elements aux_{0,i} in the Merkle path.
            aux_right (list[str]): A list of hexidecimal strings representing the elements aux_{1,i} in the Merkle path.

        Returns:
            The unlocking script for the script generated by `locking_merkle_proof_with_two_aux`.

        Note:
            - `self.hash_function` must be a combination of valid Bitcoin Script hash functions (e.g., `OP_SHA256`).
            - `self.root` must be set to the expected Merkle root to verify against.

        """
        assert all(
            c in "0123456789abcdefABCDEF" for node in aux_left for c in node
        ), f"{aux_left} is not a valid list of hexadecimal strings."

        assert all(
            c in "0123456789abcdefABCDEF" for node in aux_right for c in node
        ), f"{aux_right} is not a valid list of hexadecimal strings."

        assert len(aux_left) == len(aux_right), f"{aux_left} and {aux_right} have different lenghts."

        out = Script()

        for aux_l, aux_r in zip(aux_left, aux_right):
            out.append_pushdata(bytes.fromhex(aux_l))
            out.append_pushdata(bytes.fromhex(aux_r))

        out.append_pushdata(bytes.fromhex(d))

        return out
