from tx_engine import Script

from src.zkscript.fields.fq4 import Fq4
from src.zkscript.util.utility_scripts import nums_to_script, pick


class Fq2Over2ResidueEqualU(Fq4):
    """Represents F_q^4 = F_q^2[v] / (v^2 - u).

    This class constructs F_q^4 as a quadratic extension of
    F_q^2 = F_q[u] / (u^2 - NON_RESIDUE), with residue equal to u.
    """

    def square(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Perform squaring in Fq4 = F_q^2[v] / (v^2 - u).

        Args:
            take_modulo (bool): Whether to take modulo after the operation.
            check_constant (bool | None): Whether to check the modulo constant.
            clean_constant (bool | None): Whether to delete the modulo constant after the operation.
            is_constant_reused (bool | None, optional): Whether the modulo constant is reused after the current operation.

        Returns:
            Script: Locking script performing squaring in Fq4 = F_q^2[v] / (v^2 - u).

        """

        # Check the modulo constant
        # stack in:    [modulo, ..., x0, x1, x2, x3]
        # altstack in: []
        # stack out:    [modulo, ..., x0, x1, x2, x3]
        # altstack out: []

        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Compute the coefficient of uv in (x0 + x1*u + x2*v + x3*uv)^2
        # stack out:    [..., x0, x1, x2, x3]
        # altstack out: [uv coefficient := 2*(x1*x2 + x0*x3)]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += Script.parse_string("OP_TOALTSTACK")
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_SWAP OP_FROMALTSTACK OP_MUL")
        out += Script.parse_string("OP_ADD OP_2 OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK")

        # Compute the coefficient of v in (x0 + x1*u + x2*v + x3*uv)^2
        # stack out:    [..., x0, x1, x2, x3]
        # altstack out: [uv coefficient, v coefficient := 2*(x0*x2 + x1*x3*NON_RESIDUE)]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += Script.parse_string("OP_ROT")
        out += Script.parse_string("OP_MUL")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_ROT OP_ROT OP_MUL")
        out += Script.parse_string("OP_ADD OP_2 OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK")

        # Compute the coefficient of u in (x0 + x1*u + x2*v + x3*uv)^2
        # stack out:    [..., x0, x1, x2, x3]
        # altstack out: [uv coefficient, v coefficient, u coefficient := 2*x0*x1 + x2^2 + x3^2*NON_RESIDUE]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += Script.parse_string("OP_DUP OP_MUL")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_SWAP")
        out += Script.parse_string("OP_DUP OP_MUL")
        out += Script.parse_string("OP_ADD")
        out += Script.parse_string("OP_ROT OP_ROT")
        out += Script.parse_string("OP_2 OP_MUL OP_MUL")
        out += Script.parse_string("OP_ADD")
        out += Script.parse_string("OP_TOALTSTACK")

        # Compute the zero term in (x0 + x1*u + x2*v + x3*uv)^2
        # stack out:    [..., x0, x1, x2, x3, zero term := x0^2 + (x1^2 + 2*x2*x3)*NON_RESIDUE]
        # altstack out: [uv coefficient, v coefficient, u coefficient]
        out += Script.parse_string("OP_2 OP_MUL OP_MUL")
        out += Script.parse_string("OP_SWAP")
        out += Script.parse_string("OP_DUP OP_MUL OP_ADD")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_SWAP")
        out += Script.parse_string("OP_DUP OP_MUL OP_ADD")

        # Take the modulo of the computed terms or not and move them to the stack
        # stack out:    [..., x0, x1, x2, x3, zero term, uv coefficient, v coefficient, u coefficient]
        # altstack out: []
        if take_modulo:
            batched_modulo = Script()

            if clean_constant is None and is_constant_reused is None:
                msg = (
                    f"If take_modulo is set, both clean_constant: {clean_constant} "
                    f"and is_constant_reused: {is_constant_reused} must be set."
                )
                raise ValueError(msg)

            fetch_q = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
                if clean_constant
                else Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            )
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")

            if is_constant_reused:
                batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            else:
                batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD")

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def mul(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Perform multiplication in Fq4 = F_q^2[v] / (v^2 - u).

        Args:
            take_modulo (bool): Whether to take modulo after the operation.
            check_constant (bool | None): Whether to check the modulo constant.
            clean_constant (bool | None): Whether to delete the modulo constant after the operation.
            is_constant_reused (bool | None, optional): Whether the modulo constant is reused after the current operation.

        Returns:
            Script: Locking script performing multiplication in Fq4 = F_q^2[v] / (v^2 - u).

        """

        # Check the modulo constant
        # stack in:    [modulo, ..., x0, x1, x2, x3, y0, y1, y2, y3]
        # altstack in: []
        # stack out:    [modulo, ..., x0, x1, x2, x3, y0, y1, y2, y3]
        # altstack out: []
        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Compute the coefficient of uv in (x0 + x1*u + x2*v + x3*uv)*(y0 + y1*u + y2*v + y3*uv)
        # stack out:    [..., x0, x1, x2, x3, y0, y1, y2, y3]
        # altstack out: [uv coefficient := x0*y3 + x1*y2 + x2*y1 + x3*y0]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += pick(position=11, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ROT")
        out += pick(position=9, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD OP_ROT")
        out += pick(position=7, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD OP_SWAP")
        out += pick(position=8, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD")
        out += Script.parse_string("OP_TOALTSTACK")

        # Compute the coefficient of v in (x0 + x1*u + x2*v + x3*uv)*(y0 + y1*u + y2*v + y3*uv)
        # stack out:    [..., x0, x1, x2, x3, y0, y1, y2, y3]
        # altstack out: [uv coefficient, v coefficient := x2*y0 + x0*y2 + (x1*y3 + x3*y1)*NON_RESIDUE]
        out += Script.parse_string("OP_3DUP")
        out += pick(position=9, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ROT")
        out += pick(position=7, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL OP_SWAP")
        out += pick(position=9, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD")
        out += pick(position=6, n_elements=1)
        out += pick(position=5, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD")
        out += Script.parse_string("OP_TOALTSTACK")

        # Compute the coefficient of u in (x0 + x1*u + x2*v + x3*uv)*(y0 + y1*u + y2*v + y3*uv)
        # stack out:    [..., x0, x1, x2, x3, y0, y1, y2, y3]
        # altstack out: [uv coefficient, v coefficient, u coefficient := x0*y1 + x1*y0 + x2*y2 + x3*y3*NON_RESIDUE]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += pick(position=8, n_elements=1)
        out += Script.parse_string("OP_MUL")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL OP_SWAP")
        out += pick(position=9, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD OP_SWAP")
        out += pick(position=10, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD OP_SWAP")
        out += pick(position=8, n_elements=1)
        out += Script.parse_string("OP_MUL OP_ADD")
        out += Script.parse_string("OP_TOALTSTACK")

        # Compute the zero term in (x0 + x1*u + x2*v + x3*uv)*(y0 + y1*u + y2*v + y3*uv)
        # stack out:    [..., x0, x1, x2, x3, y0, y1, y2, y3, zero term := x0*y0 + (x1*y1 + x2*y3 + x3*y2)*NON_RESIDUE]
        # altstack out: [uv coefficient, v coefficient, u coefficient]
        out += Script.parse_string("OP_2ROT OP_TOALTSTACK OP_MUL OP_SWAP OP_FROMALTSTACK OP_MUL OP_ADD OP_TOALTSTACK")
        out += Script.parse_string("OP_ROT OP_MUL OP_TOALTSTACK")
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_ADD")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL OP_ADD")

        # Take the modulo of the computed terms or not and move them to the stack
        # stack out:    [..., x0, x1, x2, x3, zero term, uv coefficient, v coefficient, u coefficient]
        # altstack out: []
        if take_modulo:
            batched_modulo = Script()

            if clean_constant is None and is_constant_reused is None:
                msg = (
                    f"If take_modulo is set, both clean_constant: {clean_constant} "
                    f"and is_constant_reused: {is_constant_reused} must be set."
                )
                raise ValueError(msg)

            fetch_q = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
                if clean_constant
                else Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            )
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")

            if is_constant_reused:
                batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            else:
                batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD")

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")

        return out
