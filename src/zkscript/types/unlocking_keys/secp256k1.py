"""Unlocking keys for secp256k1."""

from dataclasses import dataclass

from tx_engine import Script, encode_num
from tx_engine.engine.util import GROUP_ORDER_INT, PRIME_INT, Gx, Gx_bytes

from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class Secp256k1BasePointMultiplicationUnlockingKey:
    """Class encapsulating the data required to generate an unlocking script for base point multiplication.

    Attributes:
        h (bytes): The sighash of the transaction in which the unlocking script is used.
        a (int): The purported discrete logarithm of the point A.
        A (list[int]): The purported point a * G.
    """

    h: bytes
    a: int
    A: list[int]

    def to_unlocking_script(self, load_constants: bool = True) -> Script:
        """Return the unlocking script required by `self.verify_base_point_multiplication`.

        Args:
            load_constants (bool): If `True`, loads the constant required by
                `self.verify_base_point_multiplication`. Defaults to `True`.
        """
        out = Script()
        if load_constants:
            out += nums_to_script([GROUP_ORDER_INT, Gx])
            out.append_pushdata(bytes.fromhex("0220") + Gx_bytes + bytes.fromhex("02"))
            out += nums_to_script([PRIME_INT])

        out.append_pushdata(encode_num(int.from_bytes(self.h)))
        out += nums_to_script([self.a])
        out += nums_to_script(self.A)

        return out


@dataclass
class Secp256k1PointMultiplicationUpToSignUnlockingKey:
    """Class encapsulating the data required to generate an unlocking script for point multiplication up to sign.

    Attributes:
        h (bytes): The sighash of the transaction in which the unlocking script is used.
        b (int): The purported discrete logarithm of the point Q (up to sign) with respect to P: Q = ± bP.
        x_coordinate_target_times_b_inverse (int): The x coordinate of Q times b inverse: Q_x / b mod GROUP_ORDER_INT.
        h_times_x_coordinate_target_inverse (int): The sighash of the spending transaction times Q_x inverse:
            h / Q_x mod GROUP_ORDER_INT.
        gradient (int): The gradient through P and (h / Q_x)G.
        Q (list[int]): The purported point Q = ± bP.
        P (list[int]): The purported point such that Q = ± bP.
        h_times_x_coordinate_target_inverse_times_G (list[int]): The point (h / Q_x) G.
    """

    h: bytes
    b: int
    x_coordinate_target_times_b_inverse: int
    h_times_x_coordinate_target_inverse: int
    gradient: int
    Q: list[int]
    P: list[int]
    h_times_x_coordinate_target_inverse_times_G: list[int]  # noqa: N815

    def to_unlocking_script(self, load_constants: bool = True) -> Script:
        """Return the unlocking script required by `self.verify_base_point_multiplication`.

        Args:
            load_constants (bool): If `True`, loads the constant required by
                `self.verify_base_point_multiplication`. Defaults to `True`.
        """
        out = Script()
        if load_constants:
            out += nums_to_script([PRIME_INT, GROUP_ORDER_INT, Gx])
            out.append_pushdata(bytes.fromhex("0220") + Gx_bytes + bytes.fromhex("02"))

        out.append_pushdata(encode_num(int.from_bytes(self.h)))
        out += nums_to_script(
            [self.b, self.x_coordinate_target_times_b_inverse, self.h_times_x_coordinate_target_inverse, self.gradient]
        )
        out += nums_to_script(self.Q)
        out += nums_to_script(self.P)
        out += nums_to_script(self.h_times_x_coordinate_target_inverse_times_G)

        return out


@dataclass
class Secp256k1PointMultiplicationUnlockingKey:
    """Class encapsulating the data required to generate an unlocking script for point multiplication.

    Attributes:
        h (bytes): The sighash of the transaction in which the unlocking script is used.
        s (list[int]): The integers such that:
            s[0] = Q_x / b mod GROUP_ORDER, s[1] = (Q + bG)_x / b mod GROUP_ORDER.
        gradients (list[int]): The gradients:
            gradients[0] = The gradient through `P` and `D[0]`
            gradients[1] = The gradient through `P` and `D[1]`
            gradients[2] = The gradient through `P` and `D[2]`
        d (list[int]): The integers such that:
            d[0] = h / Q_x mod GROUP_ORDER, d[1] = h / (Q + bG)_x mod GROUP_ORDER
        D (list[list[int]): The points
            D[0] = (h / Q_x)*G, D[1] = (h / (Q + bG)_x) * G, D[2] = b * G
        Q (list[int]): The purported point Q = bP.
        b (int): The purported discrete logarithm of the point Q with respect to P: Q = bP.
        P (list[int]): The purported point Q = bP.
    """

    h: bytes
    s: list[int]
    gradients: list[list[int]]
    d: list[int]
    D: list[list[int]]
    Q: list[int]
    b: int
    P: list[int]

    def to_unlocking_script(self, load_constants: bool = True) -> Script:
        """Return the unlocking script required by `self.verify_base_point_multiplication`.

        Args:
            load_constants (bool): If `True`, loads the constant required by
                `self.verify_base_point_multiplication`. Defaults to `True`.
        """
        out = Script()
        if load_constants:
            out += nums_to_script([PRIME_INT, GROUP_ORDER_INT, Gx])
            out.append_pushdata(bytes.fromhex("0220") + Gx_bytes + bytes.fromhex("02"))

        out.append_pushdata(encode_num(int.from_bytes(self.h)))
        out += nums_to_script(self.s)
        out += nums_to_script(self.gradients)
        out += nums_to_script(self.d)
        for D_ in self.D:
            out += nums_to_script(D_)
        out += nums_to_script(self.Q)
        out += nums_to_script([self.b])
        out += nums_to_script(self.P)

        return out
