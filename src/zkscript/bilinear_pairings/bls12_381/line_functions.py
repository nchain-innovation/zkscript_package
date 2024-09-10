from tx_engine import Script

# Fq2 Script implementation
from src.zkscript.bilinear_pairings.bls12_381.fields import fq2_script
from src.zkscript.util.utility_scripts import nums_to_script, pick


class LineFunctions:
    """Line evaluation for BLS12_381."""

    def __init__(self, fq2):
        self.MODULUS = fq2.MODULUS
        self.FQ2 = fq2

    def line_evaluation(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Evaluate line through T and Q at P.

        If T = Q, then the line is the one tangent at T.
        Inputs:
            - Stack: q .. lambda Q P
            - Altstack: []
        Output:
            - ev_(l_(T,Q)(P))
        Assumption on data:
            - lambda is the gradient through T and Q
            - Q = (x2,y2) is passed as an affine point in E'(F_q^2), the sextic twist
            - P = (xP,yP) is passed as an affine point in E(F_q)
        Variables:
            - If take_modulo is set to True, the outputs are returned as constants in Z_q.
        REMARK:
            - lambda is NOT checked in this function, it is assumed to be the gradient.
            - the ev_(l_(T,Q)(P)) does NOT include the zero in the second component, this is to optimise the script size
            - ev_(l_(T,Q))(P) is an element in Fq12Cubic
        """
        # Fq2 implementation
        fq2 = self.FQ2

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # Compute third component -----------------------------------------------------

        # After this, the stack is: lambda xQ yQ yP, altstack = [-lambda*xP]
        third_component = Script.parse_string("OP_SWAP OP_NEGATE")  # Roll xP and negate
        third_component += pick(position=7, nElements=2)  # Pick lambda
        third_component += Script.parse_string("OP_ROT")  # Roll -xP
        third_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # -----------------------------------------------------------------------------

        # Compute second component ----------------------------------------------------

        # After this, the stack is: lambda xQ yQ, altstack = [third_component, yP]
        second_component = Script.parse_string("OP_TOALTSTACK")
        # -----------------------------------------------------------------------------

        # Compute first component ----------------------------------------------------

        # After this, the stack is: -yQ + lambda*xQ, altsack = [third_component, yP]
        first_component = Script.parse_string("OP_2ROT OP_2ROT")  # Roll lambda and xQ
        first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        first_component += Script.parse_string("OP_2SWAP")  # Roll yQ
        if take_modulo:
            first_component += fq2.subtract(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            first_component += fq2.subtract(take_modulo=False, check_constant=False, clean_constant=False)

        # ----------------------------------------------------------------------------

        out += third_component + second_component + first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            if is_constant_reused:
                out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            else:
                out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD")
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")

        return out


line_functions = LineFunctions(fq2=fq2_script)
