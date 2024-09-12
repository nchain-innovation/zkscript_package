from tx_engine import Script

from src.zkscript.fields.fq4 import Fq4
from src.zkscript.util.utility_scripts import nums_to_script


class Fq2Over2ResidueEqualU(Fq4):
    r"""F_q^4 = F_q^2[v] / (v^2 - u).

    Build F_q^4 as quadratic extension of F_q^2 = F_q[u] / (u^2 - NON_RESIDUE) with residue equal to u.
    """

    def square(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring in Fq4 = F_q^2[v] / (v^2 - u)."""

        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Fourth component ------

        # After this, the stack is: x0 x1 x2 x3, altstack = [2*(x1*x2 + x0*x3)]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += Script.parse_string("OP_TOALTSTACK")
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_SWAP OP_FROMALTSTACK OP_MUL")
        out += Script.parse_string("OP_ADD OP_2 OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK")

        # Third component -------

        # After this, the stack is: x0 x1 x2 x3, altstack = [fourth_component, 2*(x0*x2 + x1*x3*NON_RESIDUE)]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += Script.parse_string("OP_ROT")
        out += Script.parse_string("OP_MUL")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_ROT OP_ROT OP_MUL")
        out += Script.parse_string("OP_ADD OP_2 OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK")

        # Second component ------

        # After this, the stack is: x0 x1 x2 x3,
        # altstack = [fourth_component, third_component, 2*x0*x1 + x2^2 + x3^2 * NON_RESIDUE]
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

        # First component -------

        # After this, the stack is: x0^2 + (x1^2 + 2*x2*x3)*NON_RESIDUE,
        # altstack = [fourth_component, third_component, second_component]
        out += Script.parse_string("OP_2 OP_MUL OP_MUL")
        out += Script.parse_string("OP_SWAP")
        out += Script.parse_string("OP_DUP OP_MUL OP_ADD")
        out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
        out += Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_SWAP")
        out += Script.parse_string("OP_DUP OP_MUL OP_ADD")

        if take_modulo:
            batched_modulo = Script()

            if clean_constant is None and is_constant_reused is None:
                raise ValueError(
                    f"If take_modulo is set, both clean_constant: {clean_constant} \
                        and is_constant_reused: {is_constant_reused} must be set."
                )

            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

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
