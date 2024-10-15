# Operations between Miller output (of type Fq4) and line evaluations

from tx_engine import Script

from src.zkscript.bilinear_pairings.bls12_381.fields import fq2_script, fq4_script

# Fq2 Script implementation
from src.zkscript.fields.fq12_3_over_2_over_2 import Fq12Cubic as Fq12CubicScriptModel
from src.zkscript.util.utility_scripts import mod, pick, roll, verify_bottom_constant


class MillerOutputOperations(Fq12CubicScriptModel):
    """Implementation of arithmetic for Miller loop of BLS12_381.

    Output of line evaluations are sparse elements in Fq12Cubic, i.e., they are of the form:
    Output of product of two line evaluations are somewhat sparse elements in Fq12Cubic
    """

    def line_eval_times_eval(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of sparse by sparse in Fq^12 as a cubic extension.

        Sparse (M twist) means: a + bs + cr^2 in Fq^12 = Fq^4[r] / (r^3 - s) = F_q^2[s,r] / (r^3 - s, s^2 - xi),
        a,c are in Fq^2, b is in Fq
        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y (somewhat sparse, which means: a + b s + c rs + d r^2 + e r^2*s)
        Assumption on data:
            - X and Y are passed as a sparse elements in Fq^12 (elements in Fq2).
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq2 implementation
        fq2 = self.FQ2

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Computation of fifth component ---------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 (b2*c1)
        compute_fifth_component = pick(position=6, n_elements=2)  # Pick c1
        compute_fifth_component += pick(position=4, n_elements=1)  # Pick b2
        compute_fifth_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2, altstack = [b2*c1 + b1*c2]
        compute_fifth_component += Script.parse_string("OP_2OVER")  # Pick c2
        compute_fifth_component += pick(position=11, n_elements=1)  # Pick b1
        compute_fifth_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component --------------------------------------------------

        # Computation of fourth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 (a1*c2), altstack = [fifthComponent]
        compute_fourth_component = Script.parse_string("OP_2DUP")  # Pick c2
        compute_fourth_component += pick(position=11, n_elements=2)  # Pick a1
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2, altstack = [fifthComponent, a1*c2 + a2*c1]
        compute_fourth_component += pick(position=8, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=8, n_elements=2)  # Pick a2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component -------------------------------------------------

        # Computation of third component ---------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1 b1 a2 b2,
        # altstack = [fifthComponent, fourthComponent, c1*c2]
        compute_third_component = roll(position=6, n_elements=2)  # Roll c1
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component --------------------------------------------------

        # Computation of second component --------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1 b1 a2 b2 (a1*b2),
        # altstack = [fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=5, n_elements=2)  # Pick a1
        compute_second_component += pick(position=2, n_elements=1)  # Pick b2
        compute_second_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: # After this, the stack is: a1 b1 a2 b2,
        # altstack = [fifthComponent, fourthComponent, thirdComponent, a1*b2 + a2*b1]
        compute_second_component += pick(position=4, n_elements=2)  # Pick a2
        compute_second_component += pick(position=7, n_elements=1)  # Pick b1
        compute_second_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component -------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: (a1*a2 + (b2*b1*xi)),
        # altstack = [fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=3, n_elements=1)  # Roll b1
        compute_first_component += Script.parse_string("OP_MUL OP_TOALTSTACK")
        compute_first_component += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute a1*a2
        # After this, the stack is: (a1*a2 + (b2*b1*xi))_0,
        # altstack = [fifthComponent, fourthComponent, thirdComponent, secondComponent, (a1*a2 + (b2*b1*xi))_1]
        compute_first_component += Script.parse_string("OP_FROMALTSTACK OP_TUCK OP_ADD OP_TOALTSTACK OP_ADD")
        if take_modulo:
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            compute_first_component += fetch_q
            compute_first_component += mod(stack_preparation="")
            compute_first_component += mod()
        else:
            compute_first_component += Script.parse_string("OP_FROMALTSTACK")

        # End of computation of first component --------------------------------------------------

        out += (
            compute_fifth_component
            + compute_fourth_component
            + compute_third_component
            + compute_second_component
            + compute_first_component
        )

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(7):
                out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 8))

        return out

    def miller_loop_output_times_eval(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of dense by sparse in Fq^12 as a cubic extension.

        Sparse means: a + bs + cr^2 in Fq^12 = Fq^4[r] / (r^3 - s) = F_q^2[s,r] / (r^3 - s, s^2 - xi), a,c are in Fq^2
        and b in Fq, as when evaluating line functions
        Dense means: a + bs + cr + drs + er^2 + f r^2s
        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y (dense)
        Assumption on data:
            - X and Y are passed as a sparse/dense elements in Fq^12 (elements in Fq2).
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq2 implementation
        fq2 = self.FQ2

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Computation of sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (b1*c2)
        compute_sixth_component = pick(position=14, n_elements=2)  # Pick b1
        compute_sixth_component += Script.parse_string("OP_2OVER")  # Pick c2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (b1*c2) (e2*b1)
        compute_sixth_component += pick(position=10, n_elements=2)  # Pick e2
        compute_sixth_component += pick(position=6, n_elements=1)  # Pick b1
        compute_sixth_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2, altstack = [(b1*c2) + (e2*b1) + (a2*f1)]
        compute_sixth_component += pick(position=10, n_elements=2)  # Pick f1
        compute_sixth_component += pick(position=10, n_elements=2)  # Pick a2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component -------------------------------------------------

        # Computation of fifth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (a1*c2), altstack = [sixthComponent]
        compute_fifth_component = pick(position=16, n_elements=2)  # Pick a1
        compute_fifth_component += Script.parse_string("OP_2OVER")  # Pick c2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (a1*c2) (a2*e1), altstack = [sixthComponent]
        compute_fifth_component += pick(position=10, n_elements=2)  # Pick e1
        compute_fifth_component += pick(position=8, n_elements=2)  # Pick a2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2,
        # altstack = [sixthComponent, (a1*c2) + (a2*e1) + b2*f1*xi]
        compute_fifth_component += pick(position=10, n_elements=2)  # Pick f1
        compute_fifth_component += pick(position=8, n_elements=1)  # Pick b2
        compute_fifth_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component -------------------------------------------------

        # Computation of fourth component -------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (c1*b2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = pick(position=12, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=4, n_elements=1)  # Pick b2
        compute_fourth_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (c1*b2) (d1*a2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=12, n_elements=2)  # Pick d1
        compute_fourth_component += pick(position=8, n_elements=2)  # Pick a2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 f1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, (c1*b2) + (d1*a2) + (e1*c2)]
        compute_fourth_component += roll(position=12, n_elements=2)  # Roll e1
        compute_fourth_component += pick(position=7, n_elements=2)  # Pick c2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component ------------------------------------------------

        # Computation of third component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 f1 a2 b2 c2 (c1*a2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = pick(position=10, n_elements=2)  # Pick c1
        compute_third_component += pick(position=6, n_elements=2)  # Pick a2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 f1 a2 b2 c2 (c1*a2) (b2*d1),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=10, n_elements=2)  # Pick d1
        compute_third_component += pick(position=6, n_elements=1)  # Pick b2
        compute_third_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, (c1*a2) + [(b2*d1) + (c2*f1)]*xi]
        compute_third_component += roll(position=10, n_elements=2)  # Pick f1
        compute_third_component += pick(position=7, n_elements=2)  # Pick c2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component -------------------------------------------------

        # Computation of second component -------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 (a1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=12, n_elements=2)  # Pick a1
        compute_second_component += pick(position=4, n_elements=1)  # Pick b2
        compute_second_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 (a1*b2) (b1*a2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=12, n_elements=2)  # Pick b1
        compute_second_component += pick(position=8, n_elements=2)  # Pick a2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is:  a1 b1 d1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, (a1*b2)+  (b1*a2) + (c1*c2)]
        compute_second_component += roll(position=12, n_elements=2)  # Roll c1
        compute_second_component += pick(position=7, n_elements=2)  # Pick c2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component ------------------------------------------------

        # Computation of first component --------------------------------------------------------

        # After this, the stack is: a1 b1 a2 b2 (c2*d1),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=6, n_elements=2)  # Roll c1
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 a2 [(c1*c2) + (b1*b2)]*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += roll(position=6, n_elements=2)  # Roll b1
        compute_first_component += roll(position=4, n_elements=1)  # Roll b2
        compute_first_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: [a1*a2 + [(c1*c2) + (b1*b2)]*xi],
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        if take_modulo:
            compute_first_component += fq2.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of first component -------------------------------------------------

        out += (
            compute_sixth_component
            + compute_fifth_component
            + compute_fourth_component
            + compute_third_component
            + compute_second_component
            + compute_first_component
        )

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(9):
                out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))

        return out

    def line_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of sparse by somewhat sparse in Fq^12 as a cubic extension.

        Sparse means: a + bs + cr in Fq^12 = Fq^4[r] / (r^3 - s) = F_q^2[s,r] / (r^3 - s, s^2 - xi), a,c are in Fq^2, b
        is in fq
        Somewhat sparse means: a + b s + c rs + d r^2 + e r^2s
        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y (dense)
        Assumption on data:
            - X and Y are passed as a sparse/somewhat sparse elements in Fq^12 (elements in Fq2).
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq2 implementation
        fq2 = self.FQ2

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Computation of sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*e2)
        compute_sixth_component = pick(position=14, n_elements=2)  # Pick a1
        compute_sixth_component += Script.parse_string("OP_2OVER")  # Pick e2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*e2) (d2*b1)
        compute_sixth_component += pick(position=5, n_elements=2)  # Pick d2
        compute_sixth_component += pick(position=16, n_elements=1)  # Pick b1
        compute_sixth_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2, altstack = [a1*e2 + b1*d2 + c1*b2]
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick c1
        compute_sixth_component += pick(position=13, n_elements=2)  # Pick b2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component -------------------------------------------------

        # Computation of fifth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*d2), altstack = [sixthComponent]
        compute_fifth_component = pick(position=14, n_elements=2)  # Pick a1
        compute_fifth_component += pick(position=5, n_elements=2)  # Pick d2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*d2) (b1*e2*xi), altstack = [sixthComponent]
        compute_fifth_component += Script.parse_string("OP_2OVER")  # Pick e2
        compute_fifth_component += pick(position=16, n_elements=1)  # Pick b1
        compute_fifth_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2, altstack = [sixthComponent, (a1*d2) + (b1*e2*xi) + (c1*a2)]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick c1
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick a2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component -------------------------------------------------

        # Computation of fourth component -------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*c2), altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = pick(position=14, n_elements=2)  # Pick a1
        compute_fourth_component += pick(position=7, n_elements=2)  # Pick c2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2 e2, altstack = [sixthComponent, fifthComponent, a1*c2 + c1 * d2]
        compute_fourth_component += pick(position=13, n_elements=2)  # Pick c1
        compute_fourth_component += roll(position=7, n_elements=2)  # Roll d2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component ------------------------------------------------

        # Computation of third component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 e2 (b1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = Script.parse_string("OP_2OVER")  # Pick c2
        compute_third_component += pick(position=12, n_elements=1)  # Pick b1
        compute_third_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, ((b1*c2) + (c1*e2)) * xi]
        compute_third_component += Script.parse_string("OP_2SWAP")  # Roll e2
        compute_third_component += pick(position=11, n_elements=2)  # Pick c1
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component -------------------------------------------------

        # Computation of second component -------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 (a1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=10, n_elements=2)  # Pick a1
        compute_second_component += pick(position=5, n_elements=2)  # Pick b2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, a1*b2 + a2*b1]
        compute_second_component += pick(position=7, n_elements=2)  # Pick a2
        compute_second_component += pick(position=12, n_elements=1)  # Pick b1
        compute_second_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component ------------------------------------------------

        # Computation of first component --------------------------------------------------------

        # After this, the stack is: a1 b1 a2 b2 (c1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=7, n_elements=2)  # Roll c1
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 a2 [(c1*c2) + (b1*b2)]*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2SWAP")  # Roll b2
        compute_first_component += roll(position=6, n_elements=1)  # Roll b1
        compute_first_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: [a1*a2 + [(c1*c2) + (b1*b2)]*xi],
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        if take_modulo:
            compute_first_component += fq2.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of first component -------------------------------------------------

        out += (
            compute_sixth_component
            + compute_fifth_component
            + compute_fourth_component
            + compute_third_component
            + compute_second_component
            + compute_first_component
        )

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(9):
                out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))

        return out

    def line_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of somewhat sparse by somewhat sparse in Fq^12 as a cubic extension.

        Somewhat sparse means: a + bs + c rs + d r^2 + e r^2s
        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y (dense)
        Assumption on data:
            - X and Y are passed as a somewhat sparse elements in Fq^12 (elements in Fq2).
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq2 implementation
        fq2 = self.FQ2

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Computation sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*b2)
        compute_sixth_component = pick(position=13, n_elements=2)  # Pick d1
        compute_sixth_component += pick(position=9, n_elements=2)  # Pick b2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*b2) (e1*a2)
        compute_sixth_component += pick(position=13, n_elements=2)  # Pick e1
        compute_sixth_component += pick(position=13, n_elements=2)  # Pick a2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*b2) (e1*a2) (a1*e2)
        compute_sixth_component += pick(position=23, n_elements=2)  # Pick a1
        compute_sixth_component += pick(position=7, n_elements=2)  # Pick e2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*b2) (e1*a2) (a1*e2) (b1*d2)
        compute_sixth_component += pick(position=23, n_elements=2)  # Pick b1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick d2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2, altstack = [(d1*b2) + (e1*a2) + (a1*e2) + (b1*d2)]
        compute_sixth_component += fq2.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        ) + fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component ----------------------------------------------

        # Computation of fifth component -----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*c2), altstack = [sixthComponent]
        compute_fifth_component = pick(position=15, n_elements=2)  # Pick c1
        compute_fifth_component += pick(position=7, n_elements=2)  # Pick c2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*a2) (c1*c2), altstack = [sixthComponent]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick d1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick a2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += Script.parse_string("OP_2SWAP")

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*a2) (c1*c2) (e1*b2), altstack = [sixthComponent]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick b2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*a2) ((c1*c2) + (e1*b2) + (b1*e2)) * xi,
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick b1
        compute_fifth_component += pick(position=9, n_elements=2)  # Pick e2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*a2) (((c1*c2) + (e1*b2) + (b1*e2)) * xi) (a1*d2),
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick a1
        compute_fifth_component += pick(position=9, n_elements=2)  # Pick d2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixthComponent, (d1*a2) + (((c1*c2) + (e1*b2) + (b1*e2)) * xi) + (a1*d2)]
        compute_fifth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component ---------------------------------------------

        # Computation of fourth component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*a2), altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = pick(position=15, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=11, n_elements=2)  # Pick a2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*a2) (d1*d2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick d1
        compute_fourth_component += pick(position=7, n_elements=2)  # Pick d2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*a2) (d1*d2) (e1*e2*xi),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fourth_component += pick(position=7, n_elements=2)  # Pick e2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*a2) (d1*d2) (e1*e2*xi) (a1*c2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_fourth_component += pick(position=13, n_elements=2)  # Pick c2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixthComponent, fifthComponent, (c1*a2) + (d1*d2) + (e1*e2*xi) + (a1*c2)]
        compute_fourth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component --------------------------------------------

        # Computation of third component ----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = pick(position=15, n_elements=2)  # Pick c1
        compute_third_component += pick(position=9, n_elements=2)  # Pick b2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*b2) (d1*e2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=15, n_elements=2)  # Pick d1
        compute_third_component += pick(position=5, n_elements=2)  # Pick e2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*b2) (d1*e2) (e1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=15, n_elements=2)  # Pick e1
        compute_third_component += pick(position=9, n_elements=2)  # Pick d2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*b2) (d1*e2) (e1*d2) (b1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=23, n_elements=2)  # Pick b1
        compute_third_component += pick(position=13, n_elements=2)  # Pick c2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, ((c1*b2) + (d1*e2) + (e1*d2) + (b1*c2))*xi]
        compute_third_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component ---------------------------------------------

        # Computation of second component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 (c1*e2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=15, n_elements=2)  # Pick c1
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 d2 ((c1*e2) + (c2*e1))*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += roll(position=11, n_elements=2)  # Roll e1
        compute_second_component += pick(position=7, n_elements=2)  # Pick c2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 d2 ((c1*e2) + (c2*e1))*xi (a1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=17, n_elements=2)  # Pick a1
        compute_second_component += pick(position=9, n_elements=2)  # Pick b2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 d2 ((c1*e2) + (c2*e1))*xi (a1*b2) (a2*b1),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=17, n_elements=2)  # Pick b1
        compute_second_component += pick(position=13, n_elements=2)  # Pick a2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 d2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, ((c1*e2) + (c2*e1))*xi + (a1*b2)]
        compute_second_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component --------------------------------------------

        # Computation of first component ----------------------------------------------------

        # After this, the stack is: a1 b1 d1 a2 b2 c2 (c1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=11, n_elements=2)  # Roll c1
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 a2 b2 (c1*d2) (d1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += roll(position=9, n_elements=2)  # Roll d1
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll c2
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 a2 (c1*d2) (d1*c2) (b1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll b2
        compute_first_component += roll(position=9, n_elements=2)  # Roll b1
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 a2 ( (c1*d2) + (d1*c2) + (b1*b2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: (a1*a2) + ( (c1*d2) + (d1*c2) + (b1*b2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        if take_modulo:
            compute_first_component += fq2.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of first component --------------------------------------------

        out += (
            compute_sixth_component
            + compute_fifth_component
            + compute_fourth_component
            + compute_third_component
            + compute_second_component
            + compute_first_component
        )

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(9):
                out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))

        return out

    def line_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of somewhat sparse by dense in Fq^12 as a cubic extension.

        Somewhat sparse means: a + bs + cr + dr^2 + e r^2s
        Dense means: a + bs + cr + drs + e r^2 + f r^2 s
        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y (dense)
        Assumption on data:
            - X and Y are passed as a somewhat sparse elements in Fq^12 (elements in Fq2).
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq2 implementation
        fq2 = self.FQ2

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Computation sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2)
        compute_sixth_component = pick(position=15, n_elements=2)  # Pick d1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick b2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2) (e1*a2)
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick a2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2) (e1*a2) (a1*e2)
        compute_sixth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_sixth_component += pick(position=7, n_elements=2)  # Pick f2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2) (e1*a2) (a1*e2) (b1*e2)
        compute_sixth_component += pick(position=25, n_elements=2)  # Pick b1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick e2
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2) (e1*a2) (a1*e2) (b1*e2) (c1*c2)
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick c2
        compute_sixth_component += pick(position=27, n_elements=2)  # Pick c1
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [(d1*b2) + (e1*a2) + (a1*e2) + (b1*e2) + (c1*c2)]
        compute_sixth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component ----------------------------------------------

        # Computation of fifth component -----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2), altstack = [sixthComponent]
        compute_fifth_component = pick(position=15, n_elements=2)  # Pick d1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick a2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2) (e1*b2), altstack = [sixthComponent]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick b2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2) (e1*b2) (b1*f2),
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick b1
        compute_fifth_component += pick(position=7, n_elements=2)  # Pick f2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2) ( (e1*b2) + (b1*f2) + (c1*d2) )*xi,
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick c1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick d2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2) ( (e1*b2) + (b1*f2) + (c1*d2) )*xi (a1*e2),
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_fifth_component += pick(position=9, n_elements=2)  # Pick e2
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2,
        # altstack = [sixthComponent, (d1*a2) + ( (e1*b2) + (b1*f2) + (c1*d2) )*xi + (a1*e2)]
        compute_fifth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component ---------------------------------------------

        # Computation of fourth component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = pick(position=15, n_elements=2)  # Pick d1
        compute_fourth_component += pick(position=5, n_elements=2)  # Pick e2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2) (e1*f2*xi),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fourth_component += pick(position=5, n_elements=2)  # Pick f2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2) (e1*f2*xi) (a1*d2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_fourth_component += pick(position=11, n_elements=2)  # Pick d2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2) (e1*f2*xi) (a1*d2) (b1*c2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=25, n_elements=2)  # Pick b1
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick c2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2) (e1*f2*xi) (a1*d2) (b1*c2) (c1*a2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=25, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=21, n_elements=2)  # Pick a2
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2,
        # altstack = [sixthComponent, fifthComponent, (d1*e2) + (e1*f2*xi) + (a1*d2) + (b1*c2) + (c1*a2)]
        compute_fourth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component --------------------------------------------

        # Computation of third component ----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*f2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = pick(position=15, n_elements=2)  # Pick d1
        compute_third_component += Script.parse_string("OP_2OVER")  # Pick f2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*f2) (e1*e2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=15, n_elements=2)  # Pick e1
        compute_third_component += pick(position=7, n_elements=2)  # Pick e2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*f2) (e1*e2) (b1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=23, n_elements=2)  # Pick b1
        compute_third_component += pick(position=11, n_elements=2)  # Pick d2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 ( (d1*f2) + (e1*e2) + (b1*d2) + (c1*b2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=15, n_elements=2)  # Pick b2
        compute_third_component += pick(position=25, n_elements=2)  # Pick b2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 ( (d1*f2) + (e1*e2) + (b1*d2) + (c1*b2) )*xi
        # (a1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=23, n_elements=2)  # Pick a1
        compute_third_component += pick(position=11, n_elements=2)  # Pick c2
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, ( (d1*f2) + (e1*e2) + (b1*d2) + (c1*b2) )*xi +
        # (a1*c2)]
        compute_third_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component ---------------------------------------------

        # Computation of second component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=15, n_elements=2)  # Pick d1
        compute_second_component += pick(position=9, n_elements=2)  # Pick c2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*c2) (e1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=15, n_elements=2)  # Pick e1
        compute_second_component += pick(position=9, n_elements=2)  # Pick d2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*c2) ( (e1*d2) + (c1*f2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += Script.parse_string("OP_2ROT")  # Roll f2
        compute_second_component += pick(position=21, n_elements=2)  # Pick c1
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*c2) ( (e1*d2) + (c1*f2) )*xi (a1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=23, n_elements=2)  # Pick a1
        compute_second_component += pick(position=13, n_elements=2)  # Pick b2
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*c2) ( (e1*d2) + (c1*f2) )*xi (a1*b2) (b1*a2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=15, n_elements=2)  # Pick a2
        compute_second_component += pick(position=25, n_elements=2)  # Pick b1
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent,
        # (d1*c2) + ( (e1*d2) + (c1*f2) )*xi + (a1*b2) + (b1*a2)]
        compute_second_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component --------------------------------------------

        # Computation of first component ----------------------------------------------------

        # After this, the stack is: a1 b1 d1 e1 a2 b2 c2 d2 (e2*c1),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=15, n_elements=2)  # Roll c1
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 e1 a2 b2 c2 (e2*c1) (d1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += roll(position=13, n_elements=2)  # Roll d1
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll d2
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 b1 a2 b2 ( (e2*c1) + (d1*d2) + (e1*c2) ),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll c2
        compute_first_component += roll(position=11, n_elements=2)  # Roll e1
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a1 a2 ( (b1*b2) + (e2*c1) + (d1*d2) + (e1*c2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2SWAP")  # Roll b2
        compute_first_component += roll(position=7, n_elements=2)  # Roll b1
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: (a1*a2) + ( (b1*b2) + (e2*c1) + (d1*d2) + (e1*c2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        if take_modulo:
            compute_first_component += fq2.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of first component --------------------------------------------

        out += (
            compute_sixth_component
            + compute_fifth_component
            + compute_fourth_component
            + compute_third_component
            + compute_second_component
            + compute_first_component
        )

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(9):
                out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))

        return out

    def miller_loop_output_square(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        return MillerOutputOperations.square(
            self,
            take_modulo=take_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_mul(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def line_eval_times_eval_times_miller_loop_output(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        return self.line_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
            take_modulo=take_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_times_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )


miller_output_ops = MillerOutputOperations(q=fq2_script.MODULUS, fq2=fq2_script, fq4=fq4_script)
