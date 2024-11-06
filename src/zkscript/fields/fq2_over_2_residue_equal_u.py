"""Bitcoin scripts that perform arithmetic operations in a quadratic extension of F_q^2."""

from tx_engine import Script

from src.zkscript.fields.fq4 import Fq4
from src.zkscript.util.utility_scripts import mod, nums_to_script, pick, verify_bottom_constant


class Fq2Over2ResidueEqualU(Fq4):
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^4 = F_q^2[v] / (v^2 - u).

    F_q^4 = F_q^2[v] / (v^2 - u) is a quadratic extension of F_q^2 = F_q[u] / (u^2 - non_residue).

    Elements in F_q^4 are of the form `a + b * v`, where `a` and `b` are elements of F_q^2, `v^2` is equal to
    `u`, and `u^2` is equal to the non-residue used to define F_q^2. Elements in F_q^4 can also be written as
    `x0 + x1*u + x2*v + x3*uv`, where `x0`, `x1`, `x2`, `x3` are elements of F_q.
    """

    def square(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring in F_q^4 = F_q^2[v] / (v^2 - u).

        Stack input:
            - stack    = [q, ..., x := (x0, x1, x2, x3)], `x` is a couple of elements of F_q^2
            - altstack = []

        Stack output:
            - stack    = [q, ..., x^2]
            - altstack = []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to square an element in Fq4 = F_q^2[v] / (v^2 - u).

        Raises:
            AssertionError: If `clean_constant` or `check_constant` are not provided when take_modulo is `True`.
        """
        # Check the modulo constant
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

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
        # stack out:    [..., zero term := x0^2 + (x1^2 + 2*x2*x3)*NON_RESIDUE]
        # altstack out: [uv coefficient, v coefficient, u coefficient]
        out += Script.parse_string("OP_2 OP_MUL OP_MUL")
        out += Script.parse_string("OP_SWAP")
        out += Script.parse_string("OP_DUP OP_MUL OP_ADD")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_SWAP")
        out += Script.parse_string("OP_DUP OP_MUL OP_ADD")

        # Take the modulo of the computed terms or not and move them to the stack
        if take_modulo:
            batched_modulo = Script()

            if clean_constant is None or is_constant_reused is None:
                msg = "If take_modulo is True, clean_constant and is_constant_reused must be set."
                raise ValueError(msg)

            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            batched_modulo += mod(stack_preparation="")
            batched_modulo += mod()
            batched_modulo += mod()
            batched_modulo += mod(is_constant_reused=is_constant_reused)

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
        """Multiplication in Fq4 = F_q^2[v] / (v^2 - u).

        Stack input:
            - stack    = [q, ..., x := (x0, x1, x2, x3), y := (y0, y1, y2, y3)], `x`, `y` are couples of elements of
                F_q^2
            - altstack = []

        Stack output:
            - stack    = [q, ..., x * y]
            - altstack = []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply two elements in Fq4 = F_q^2[v] / (v^2 - u).

        Raises:
            AssertionError: If `clean_constant` or `check_constant` are not provided when take_modulo is `True`.
        """
        # Check the modulo constant
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

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
        out += Script.parse_string("OP_MUL OP_ADD OP_TOALTSTACK")

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
        out += Script.parse_string("OP_MUL OP_ADD OP_TOALTSTACK")

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
        out += Script.parse_string("OP_MUL OP_ADD OP_TOALTSTACK")

        # Compute the zero term in (x0 + x1*u + x2*v + x3*uv)*(y0 + y1*u + y2*v + y3*uv)
        # stack out:    [..., zero term := x0*y0 + (x1*y1 + x2*y3 + x3*y2)*NON_RESIDUE]
        # altstack out: [uv coefficient, v coefficient, u coefficient]
        out += Script.parse_string("OP_2ROT OP_TOALTSTACK OP_MUL OP_SWAP OP_FROMALTSTACK OP_MUL OP_ADD OP_TOALTSTACK")
        out += Script.parse_string("OP_ROT OP_MUL OP_TOALTSTACK OP_MUL")
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_ADD")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL OP_ADD")

        # Take the modulo of the computed terms or not and move them to the stack
        if take_modulo:
            batched_modulo = Script()

            if clean_constant is None and is_constant_reused is None:
                msg = (
                    f"If take_modulo is set, both clean_constant: {clean_constant} "
                    f"and is_constant_reused: {is_constant_reused} must be set."
                )
                raise ValueError(msg)

            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            batched_modulo += mod(stack_preparation="")
            batched_modulo += mod()
            batched_modulo += mod()
            batched_modulo += mod(is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo

        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 3))

        return out
