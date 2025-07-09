"""Operations between Miller output (in F_q^12 as cubic extension of F_q^4) and line evaluations for BLS12-381."""

from typing import ClassVar

from tx_engine import Script

from src.zkscript.bilinear_pairings.bls12_381.fields import fq2_script, fq4_script
from src.zkscript.fields.fq12_3_over_2_over_2 import Fq12Cubic as Fq12CubicScriptModel
from src.zkscript.util.utility_scripts import mod, pick, roll, verify_bottom_constant


class MillerOutputOperations(Fq12CubicScriptModel):
    """Arithmetic for Miller loop for BLS12-381.

    Operations are performed in Fq12Cubic, Fq^12 = Fq^4[r] / (r^3 - s) = F_q^2[s,r] / (r^3 - s, s^2 - xi).

    We call:
        - `sparse` elements of the form: a + b s + c r^2, with a, c in F_q^2, and b in F_q.
        - `somewhat sparse` elements of the form: a + b s + c rs + d r^2 + e r^2s, with a, b, c, d, e in F_q^2.
        - `dense` elements of the form: a + b s + c r + d rs + e r^2 + f r^2s, with a, b, c, d, e, f in F_q^2.

    The output of line evaluations are sparse elements.
    The product of two line evaluations are somewhat sparse elements.
    """

    def line_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of two sparse elements in F_q^12 as a cubic extension of F_q^4.

        Stack input:
            - stack:    [q, ..., x := (a1, b1, c1), y := (a2, b2, c2)], `x`, `y` are two sparse elements in F_q^12
            - altstack: []

        Stack output:
            - stack:    [q, ..., z := x * y], `z` is a somewhat sparse element in F_q^12
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply two sparse elements in F_q^12.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation of fifth component ---------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 (b2*c1)
        compute_fifth_component = pick(position=6, n_elements=2)  # Pick c1
        compute_fifth_component += pick(position=4, n_elements=1)  # Pick b2
        compute_fifth_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2, altstack = [b2*c1 + b1*c2]
        compute_fifth_component += Script.parse_string("OP_2OVER")  # Pick c2
        compute_fifth_component += pick(position=11, n_elements=1)  # Pick b1
        compute_fifth_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component --------------------------------------------------

        # Computation of fourth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 (a1*c2), altstack = [fifthComponent]
        compute_fourth_component = Script.parse_string("OP_2DUP")  # Pick c2
        compute_fourth_component += pick(position=11, n_elements=2)  # Pick a1
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2, altstack = [fifthComponent, a1*c2 + a2*c1]
        compute_fourth_component += pick(position=8, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=8, n_elements=2)  # Pick a2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component -------------------------------------------------

        # Computation of third component ---------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1 b1 a2 b2,
        # altstack = [fifthComponent, fourthComponent, c1*c2]
        compute_third_component = roll(position=6, n_elements=2)  # Roll c1
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component --------------------------------------------------

        # Computation of second component --------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1 b1 a2 b2 (a1*b2),
        # altstack = [fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=5, n_elements=2)  # Pick a1
        compute_second_component += pick(position=2, n_elements=1)  # Pick b2
        compute_second_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: # After this, the stack is: a1 b1 a2 b2,
        # altstack = [fifthComponent, fourthComponent, thirdComponent, a1*b2 + a2*b1]
        compute_second_component += pick(position=4, n_elements=2)  # Pick a2
        compute_second_component += pick(position=7, n_elements=1)  # Pick b1
        compute_second_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component -------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: (a1*a2 + (b2*b1*xi)),
        # altstack = [fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=3, n_elements=1)  # Roll b1
        compute_first_component += Script.parse_string("OP_MUL OP_TOALTSTACK")
        compute_first_component += self.fq4.base_field.mul(
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
            compute_first_component += mod(stack_preparation="", is_positive=positive_modulo)
            compute_first_component += mod(is_positive=positive_modulo)
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
                out += mod(is_positive=positive_modulo)
            out += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 8))

        return out

    def miller_loop_output_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of dense element by sparse element in F_q^12 as a cubic extension of F_q^4.

        Stack input:
            - stack:    [q, ..., x := (a1, b1, c1, d1, e1, f1), y := (a2, b2, c2)], `x` is a dense element, `y` is a
                sparse element in F_q^12
            - altstack: []

        Stack output:
            - stack:    [q, ..., z := x * y], `z` is a dense element in F_q^12
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply a dense element by a sparse element in F_q^12.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation of sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (b1*c2)
        compute_sixth_component = pick(position=14, n_elements=2)  # Pick b1
        compute_sixth_component += Script.parse_string("OP_2OVER")  # Pick c2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (b1*c2) (e2*b1)
        compute_sixth_component += pick(position=10, n_elements=2)  # Pick e2
        compute_sixth_component += pick(position=6, n_elements=1)  # Pick b1
        compute_sixth_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2, altstack = [(b1*c2) + (e2*b1) + (a2*f1)]
        compute_sixth_component += pick(position=10, n_elements=2)  # Pick f1
        compute_sixth_component += pick(position=10, n_elements=2)  # Pick a2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_sixth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component -------------------------------------------------

        # Computation of fifth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (a1*c2), altstack = [sixthComponent]
        compute_fifth_component = pick(position=16, n_elements=2)  # Pick a1
        compute_fifth_component += Script.parse_string("OP_2OVER")  # Pick c2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (a1*c2) (a2*e1), altstack = [sixthComponent]
        compute_fifth_component += pick(position=10, n_elements=2)  # Pick e1
        compute_fifth_component += pick(position=8, n_elements=2)  # Pick a2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2,
        # altstack = [sixthComponent, (a1*c2) + (a2*e1) + b2*f1*xi]
        compute_fifth_component += pick(position=10, n_elements=2)  # Pick f1
        compute_fifth_component += pick(position=8, n_elements=1)  # Pick b2
        compute_fifth_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component -------------------------------------------------

        # Computation of fourth component -------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (c1*b2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = pick(position=12, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=4, n_elements=1)  # Pick b2
        compute_fourth_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 (c1*b2) (d1*a2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=12, n_elements=2)  # Pick d1
        compute_fourth_component += pick(position=8, n_elements=2)  # Pick a2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 f1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, (c1*b2) + (d1*a2) + (e1*c2)]
        compute_fourth_component += roll(position=12, n_elements=2)  # Roll e1
        compute_fourth_component += pick(position=7, n_elements=2)  # Pick c2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component ------------------------------------------------

        # Computation of third component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 f1 a2 b2 c2 (c1*a2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = pick(position=10, n_elements=2)  # Pick c1
        compute_third_component += pick(position=6, n_elements=2)  # Pick a2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 f1 a2 b2 c2 (c1*a2) (b2*d1),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=10, n_elements=2)  # Pick d1
        compute_third_component += pick(position=6, n_elements=1)  # Pick b2
        compute_third_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, (c1*a2) + [(b2*d1) + (c2*f1)]*xi]
        compute_third_component += roll(position=10, n_elements=2)  # Pick f1
        compute_third_component += pick(position=7, n_elements=2)  # Pick c2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component -------------------------------------------------

        # Computation of second component -------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 (a1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=12, n_elements=2)  # Pick a1
        compute_second_component += pick(position=4, n_elements=1)  # Pick b2
        compute_second_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 (a1*b2) (b1*a2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=12, n_elements=2)  # Pick b1
        compute_second_component += pick(position=8, n_elements=2)  # Pick a2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is:  a1 b1 d1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, (a1*b2)+  (b1*a2) + (c1*c2)]
        compute_second_component += roll(position=12, n_elements=2)  # Roll c1
        compute_second_component += pick(position=7, n_elements=2)  # Pick c2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component ------------------------------------------------

        # Computation of first component --------------------------------------------------------

        # After this, the stack is: a1 b1 a2 b2 (c2*d1),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=6, n_elements=2)  # Roll c1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 a2 [(c1*c2) + (b1*b2)]*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += roll(position=6, n_elements=2)  # Roll b1
        compute_first_component += roll(position=4, n_elements=1)  # Roll b2
        compute_first_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: [a1*a2 + [(c1*c2) + (b1*b2)]*xi],
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        if take_modulo:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )

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
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))

        return out

    def miller_loop_output_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of Miller output by line eval times eval in Fq^12 as a cubic extension.

        Line eval times eval is: a + bs + cr + dr^2 + e r^2s
        Miller output is: a + bs + cr + drs + e r^2 + f r^2 s
        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y (dense)
        Assumption on data:
            - X and Y are passed as a somewhat sparse elements in Fq^12 (elements in Fq2).
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q;
            otherwise, the coordinates are not taken modulo q.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (e1*b2)
        compute_sixth_component = pick(position=13, n_elements=2)  # Pick e1
        compute_sixth_component += pick(position=9, n_elements=2)  # Pick b2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (e1*b2) (a2*f1)
        compute_sixth_component += pick(position=13, n_elements=2)  # Pick f1
        compute_sixth_component += pick(position=13, n_elements=2)  # Pick a2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (e1*b2) (a2*f1) (c1*c2)
        compute_sixth_component += pick(position=21, n_elements=2)  # Pick c1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick c2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (e1*b2) (a2*f1) (c1*c2) (b1*d2)
        compute_sixth_component += pick(position=25, n_elements=2)  # Pick b1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick d2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (e1*b2) (a2*f1) (c1*c2) (b1*d2) (e2*a1)
        compute_sixth_component += pick(position=29, n_elements=2)  # Pick a1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick e2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2,
        # altstack = [(d1*b2) + (e1*a2) + (a1*e2) + (b1*e2) + (c1*c2)]
        compute_sixth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_sixth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component ----------------------------------------------

        # Computation of fifth component -----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*c2),
        # altstack = [sixth_component]
        compute_fifth_component = pick(position=15, n_elements=2)  # Pick d1
        compute_fifth_component += pick(position=7, n_elements=2)  # Pick c2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*c2) (e2*b1),
        # altstack = [sixth_component]
        compute_fifth_component += Script.parse_string("OP_2OVER")  # Pick e2
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick b1
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*c2) (e2*b1) (b2*f1),
        # altstack = [sixth_component]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick f1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick b2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 [(d1*c2) + (e2*b1) + (b2*f1)]*xi,
        # altstack = [sixth_component]
        compute_fifth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 [(d1*c2) + (e2*b1) + (b2*f1)]*xi (a2*e1),
        # altstack = [sixth_component]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick a2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 [(d1*c2) + (e2*b1) + (b2*f1)]*xi (a2*e1) (d2*a1),
        # altstack = [sixth_component]
        compute_fifth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_fifth_component += pick(position=9, n_elements=2)  # Pick a2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2,
        # altstack = [sixth_component, fifth_component]
        compute_fifth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component ---------------------------------------------

        # Computation of fourth component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*a2),
        # altstack = [sixth_component, fifth_component]
        compute_fourth_component = pick(position=15, n_elements=2)  # Pick d1
        compute_fourth_component += pick(position=11, n_elements=2)  # Pick a2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*a2) (e2*f1*xi),
        # altstack = [sixth_component, fifth_component]
        compute_fourth_component += Script.parse_string("OP_2OVER")  # Pick e2
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick f1
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*a2) (e2*f1*xi) (d2*e1),
        # altstack = [sixth_component, fifth_component]
        compute_fourth_component += pick(position=17, n_elements=2)  # Pick e1
        compute_fourth_component += pick(position=9, n_elements=2)  # Pick d2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*a2) (e2*f1*xi) (d2*e1) (b2*c1),
        # altstack = [sixth_component, fifth_component]
        compute_fourth_component += pick(position=23, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick b2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*a2) (e2*f1*xi) (d2*e1) (b2*c1) (c2*a1),
        # altstack = [sixth_component, fifth_component]
        compute_fourth_component += pick(position=29, n_elements=2)  # Pick a1
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick c2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2,
        # altstack = [sixth_component, fifth_component,  (d1*a2) + (e2*f1*xi) + (d2*e1) + (b2*c1) + (c2*a1)]
        compute_fourth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component --------------------------------------------

        # Computation of third component ----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*b2),
        # altstack = [sixth_component, fifth_component, fourth_component]
        compute_third_component = pick(position=15, n_elements=2)  # Pick d1
        compute_third_component += pick(position=9, n_elements=2)  # Pick b2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*b2) (e1*e2),
        # altstack = [sixth_component, fifth_component, fourth_component]
        compute_third_component += Script.parse_string("OP_2OVER")  # Pick e2
        compute_third_component += pick(position=17, n_elements=2)  # Pick e1
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*b2) (e1*e2) (d2*f1),
        # altstack = [sixth_component, fifth_component, fourth_component]
        compute_third_component += pick(position=15, n_elements=2)  # Pick f1
        compute_third_component += pick(position=9, n_elements=2)  # Pick d2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 ( (d1*b2) + (e1*e2) + (d2*f1) + (b1*c2) )*xi
        # altstack = [sixth_component, fifth_component, fourth_component]
        compute_third_component += pick(position=25, n_elements=2)  # Pick b1
        compute_third_component += pick(position=13, n_elements=2)  # Pick c2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 ((d1*b2) + (e1*e2) + (d2*f1) + (b1*c2))*xi (a2*c1),
        # altstack = [sixth_component, fifth_component, fourth_component]
        compute_third_component += pick(position=19, n_elements=2)  # Pick c1
        compute_third_component += pick(position=13, n_elements=2)  # Pick a2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2,
        # altstack = [sixth_component, fifth_component, fourth_component,
        # ((d1*b2) + (e1*e2) + (d2*f1) + (b1*c2) )*xi + (a2*c1) ]
        compute_third_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component ---------------------------------------------

        # Computation of second component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 f1 a2 b2 c2 d2 e2 (d1*e2),
        # altstack = [sixth_component, fifth_component, fourth_component, third_component]
        compute_second_component = pick(position=15, n_elements=2)  # Pick d1
        compute_second_component += Script.parse_string("OP_2OVER")  # Pick e2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 [(d1*e2) + (c2*f1)]*xi,
        # altstack = [sixth_component, fifth_component, fourth_component, third_component]
        compute_second_component += roll(position=13, n_elements=2)  # Roll f1
        compute_second_component += pick(position=9, n_elements=2)  # Pick c2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 [(d1*e2) + (c2*f1)]*xi (a1*b2),
        # altstack = [sixth_component, fifth_component, fourth_component, third_component]
        compute_second_component += pick(position=21, n_elements=2)  # Pick a1
        compute_second_component += pick(position=11, n_elements=2)  # Pick b2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 [(d1*e2) + (c2*f1)]*xi (a1*b2) (a2*b1),
        # altstack = [sixth_component, fifth_component, fourth_component, third_component]
        compute_second_component += pick(position=21, n_elements=2)  # Pick b1
        compute_second_component += pick(position=15, n_elements=2)  # Pick a2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 [(d1*e2) + (c2*f1)]*xi (a1*b2) (a2*b1) (d2*c1),
        # altstack = [sixth_component, fifth_component, fourth_component, third_component]
        compute_second_component += pick(position=21, n_elements=2)  # Pick c1
        compute_second_component += pick(position=11, n_elements=2)  # Pick d2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixth_component, fifth_component, fourth_component, third_component,
        # [(d1*e2) + (c2*f1)]*xi + (a1*b2) + (a2*b1) + (d2*c1)] ]
        compute_second_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component --------------------------------------------

        # Computation of first component ----------------------------------------------------

        # After this, the stack is: a1 b1 d1 e1 a2 b2 c2 d2 (e2*c1),
        # altstack = [sixth_component, fifth_component, fourth_component, third_component, second_component]
        compute_first_component = roll(position=15, n_elements=2)  # Roll c1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 e1 a2 b2 c2 (e2*c1) (d1*d2),
        # altstack = [sixth_component, fifth_component, fourth_component, third_component, second_component]
        compute_first_component += roll(position=13, n_elements=2)  # Roll d1
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll d2
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 a2 b2 ( (e2*c1) + (d1*d2) + (e1*c2) ),
        # altstack = [sixth_component, fifth_component, fourth_component, third_component, second_component]
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll c2
        compute_first_component += roll(position=11, n_elements=2)  # Roll e1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 a2 ( (b1*b2) + (e2*c1) + (d1*d2) + (e1*c2) )*xi,
        # altstack = [sixth_component, fifth_component, fourth_component, third_component, second_component]
        compute_first_component += Script.parse_string("OP_2SWAP")  # Roll b2
        compute_first_component += roll(position=7, n_elements=2)  # Roll b1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: (a1*a2) + ( (b1*b2) + (e2*c1) + (d1*d2) + (e1*c2) )*xi,
        # altstack = [sixth_component, fifth_component, fourth_component, third_component, second_component]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        if take_modulo:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )

        # End of computation of first component --------------------------------------------

        out += compute_sixth_component
        out += compute_fifth_component
        out += compute_fourth_component
        out += compute_third_component
        out += compute_second_component
        out += compute_first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(9):
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))
        return out

    def line_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of sparse element by somewhat sparse element in F_q^12 as a cubic extension of F_q^4.

        Stack input:
            - stack:    [q, ..., x := (a1, b1, c1), y := (a2, b2, c2, d2, e2)], `x` is a sparse element, `y` is a
                somewhat sparse element in F_q^12
            - altstack: []

        Stack output:
            - stack:    [q, ..., z := x * y], `z` is a dense element in F_q^12
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply a sparse element by a somewhat sparse element in F_q^12.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation of sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*e2)
        compute_sixth_component = pick(position=14, n_elements=2)  # Pick a1
        compute_sixth_component += Script.parse_string("OP_2OVER")  # Pick e2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*e2) (d2*b1)
        compute_sixth_component += pick(position=5, n_elements=2)  # Pick d2
        compute_sixth_component += pick(position=16, n_elements=1)  # Pick b1
        compute_sixth_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2, altstack = [a1*e2 + b1*d2 + c1*b2]
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick c1
        compute_sixth_component += pick(position=13, n_elements=2)  # Pick b2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_sixth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component -------------------------------------------------

        # Computation of fifth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*d2), altstack = [sixthComponent]
        compute_fifth_component = pick(position=14, n_elements=2)  # Pick a1
        compute_fifth_component += pick(position=5, n_elements=2)  # Pick d2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*d2) (b1*e2*xi), altstack = [sixthComponent]
        compute_fifth_component += Script.parse_string("OP_2OVER")  # Pick e2
        compute_fifth_component += pick(position=16, n_elements=1)  # Pick b1
        compute_fifth_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2, altstack = [sixthComponent, (a1*d2) + (b1*e2*xi) + (c1*a2)]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick c1
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick a2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component -------------------------------------------------

        # Computation of fourth component -------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 d2 e2 (a1*c2), altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = pick(position=14, n_elements=2)  # Pick a1
        compute_fourth_component += pick(position=7, n_elements=2)  # Pick c2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2 e2, altstack = [sixthComponent, fifthComponent, a1*c2 + c1 * d2]
        compute_fourth_component += pick(position=13, n_elements=2)  # Pick c1
        compute_fourth_component += roll(position=7, n_elements=2)  # Roll d2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component ------------------------------------------------

        # Computation of third component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 e2 (b1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = Script.parse_string("OP_2OVER")  # Pick c2
        compute_third_component += pick(position=12, n_elements=1)  # Pick b1
        compute_third_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, ((b1*c2) + (c1*e2)) * xi]
        compute_third_component += Script.parse_string("OP_2SWAP")  # Roll e2
        compute_third_component += pick(position=11, n_elements=2)  # Pick c1
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component -------------------------------------------------

        # Computation of second component -------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2 (a1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=10, n_elements=2)  # Pick a1
        compute_second_component += pick(position=5, n_elements=2)  # Pick b2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 a2 b2 c2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, a1*b2 + a2*b1]
        compute_second_component += pick(position=7, n_elements=2)  # Pick a2
        compute_second_component += pick(position=12, n_elements=1)  # Pick b1
        compute_second_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component ------------------------------------------------

        # Computation of first component --------------------------------------------------------

        # After this, the stack is: a1 b1 a2 b2 (c1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=7, n_elements=2)  # Roll c1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 a2 [(c1*c2) + (b1*b2)]*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2SWAP")  # Roll b2
        compute_first_component += roll(position=6, n_elements=1)  # Roll b1
        compute_first_component += self.fq4.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: [a1*a2 + [(c1*c2) + (b1*b2)]*xi],
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        if take_modulo:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )

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
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))

        return out

    def line_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of two somewhat sparse elements in F_q^12 as a cubic extension of F_q^4.

        Stack input:
            - stack:    [q, ..., x := (a1, b1, c1, d1, e1), y := (a2, b2, c2, d2, e2)], `x` `y` are somewhat sparse
                elements in F_q^12
            - altstack: []

        Stack output:
            - stack:    [q, ..., z := x * y], `z` is a dense element in F_q^12
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply two somewhat sparse elements in F_q^12.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*b2)
        compute_sixth_component = pick(position=13, n_elements=2)  # Pick d1
        compute_sixth_component += pick(position=9, n_elements=2)  # Pick b2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*b2) (e1*a2)
        compute_sixth_component += pick(position=13, n_elements=2)  # Pick e1
        compute_sixth_component += pick(position=13, n_elements=2)  # Pick a2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*b2) (e1*a2) (a1*e2)
        compute_sixth_component += pick(position=23, n_elements=2)  # Pick a1
        compute_sixth_component += pick(position=7, n_elements=2)  # Pick e2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*b2) (e1*a2) (a1*e2) (b1*d2)
        compute_sixth_component += pick(position=23, n_elements=2)  # Pick b1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick d2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2, altstack = [(d1*b2) + (e1*a2) + (a1*e2) + (b1*d2)]
        compute_sixth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        ) + self.fq4.base_field.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component ----------------------------------------------

        # Computation of fifth component -----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*c2), altstack = [sixthComponent]
        compute_fifth_component = pick(position=15, n_elements=2)  # Pick c1
        compute_fifth_component += pick(position=7, n_elements=2)  # Pick c2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*a2) (c1*c2), altstack = [sixthComponent]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick d1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick a2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += Script.parse_string("OP_2SWAP")

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*a2) (c1*c2) (e1*b2), altstack = [sixthComponent]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick b2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*a2) ((c1*c2) + (e1*b2) + (b1*e2)) * xi,
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick b1
        compute_fifth_component += pick(position=9, n_elements=2)  # Pick e2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*a2) (((c1*c2) + (e1*b2) + (b1*e2)) * xi) (a1*d2),
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick a1
        compute_fifth_component += pick(position=9, n_elements=2)  # Pick d2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixthComponent, (d1*a2) + (((c1*c2) + (e1*b2) + (b1*e2)) * xi) + (a1*d2)]
        compute_fifth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component ---------------------------------------------

        # Computation of fourth component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*a2), altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = pick(position=15, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=11, n_elements=2)  # Pick a2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*a2) (d1*d2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick d1
        compute_fourth_component += pick(position=7, n_elements=2)  # Pick d2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*a2) (d1*d2) (e1*e2*xi),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fourth_component += pick(position=7, n_elements=2)  # Pick e2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*a2) (d1*d2) (e1*e2*xi) (a1*c2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_fourth_component += pick(position=13, n_elements=2)  # Pick c2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixthComponent, fifthComponent, (c1*a2) + (d1*d2) + (e1*e2*xi) + (a1*c2)]
        compute_fourth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component --------------------------------------------

        # Computation of third component ----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = pick(position=15, n_elements=2)  # Pick c1
        compute_third_component += pick(position=9, n_elements=2)  # Pick b2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*b2) (d1*e2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=15, n_elements=2)  # Pick d1
        compute_third_component += pick(position=5, n_elements=2)  # Pick e2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*b2) (d1*e2) (e1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=15, n_elements=2)  # Pick e1
        compute_third_component += pick(position=9, n_elements=2)  # Pick d2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (c1*b2) (d1*e2) (e1*d2) (b1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=23, n_elements=2)  # Pick b1
        compute_third_component += pick(position=13, n_elements=2)  # Pick c2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, ((c1*b2) + (d1*e2) + (e1*d2) + (b1*c2))*xi]
        compute_third_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component ---------------------------------------------

        # Computation of second component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 (c1*e2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=15, n_elements=2)  # Pick c1
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 d2 ((c1*e2) + (c2*e1))*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += roll(position=11, n_elements=2)  # Roll e1
        compute_second_component += pick(position=7, n_elements=2)  # Pick c2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 d2 ((c1*e2) + (c2*e1))*xi (a1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=17, n_elements=2)  # Pick a1
        compute_second_component += pick(position=9, n_elements=2)  # Pick b2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 d2 ((c1*e2) + (c2*e1))*xi (a1*b2) (a2*b1),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=17, n_elements=2)  # Pick b1
        compute_second_component += pick(position=13, n_elements=2)  # Pick a2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 a2 b2 c2 d2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, ((c1*e2) + (c2*e1))*xi + (a1*b2)]
        compute_second_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component --------------------------------------------

        # Computation of first component ----------------------------------------------------

        # After this, the stack is: a1 b1 d1 a2 b2 c2 (c1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=11, n_elements=2)  # Roll c1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 a2 b2 (c1*d2) (d1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += roll(position=9, n_elements=2)  # Roll d1
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll c2
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 a2 (c1*d2) (d1*c2) (b1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll b2
        compute_first_component += roll(position=9, n_elements=2)  # Roll b1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 a2 ( (c1*d2) + (d1*c2) + (b1*b2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: (a1*a2) + ( (c1*d2) + (d1*c2) + (b1*b2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        if take_modulo:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )

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
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))

        return out

    def line_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of somewhat sparse element by dense element in F_q^12 as a cubic extension of F_q^4.

        Stack input:
            - stack:    [q, ..., x := (a1, b1, c1, d1, e1), y := (a2, b2, c2, d2, e2, f2)], `x` is a somewhat sparse
                element, `y` is a dense element in F_q^12
            - altstack: []

        Stack output:
            - stack:    [q, ..., z := x * y], `z` is a dense element in F_q^12
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply a somewhat sparse element by a dense element in F_q^12.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation sixth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2)
        compute_sixth_component = pick(position=15, n_elements=2)  # Pick d1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick b2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2) (e1*a2)
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick a2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2) (e1*a2) (a1*e2)
        compute_sixth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_sixth_component += pick(position=7, n_elements=2)  # Pick f2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2) (e1*a2) (a1*e2) (b1*e2)
        compute_sixth_component += pick(position=25, n_elements=2)  # Pick b1
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick e2
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*b2) (e1*a2) (a1*e2) (b1*e2) (c1*c2)
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick c2
        compute_sixth_component += pick(position=27, n_elements=2)  # Pick c1
        compute_sixth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [(d1*b2) + (e1*a2) + (a1*e2) + (b1*e2) + (c1*c2)]
        compute_sixth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_sixth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of sixth component ----------------------------------------------

        # Computation of fifth component -----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2), altstack = [sixthComponent]
        compute_fifth_component = pick(position=15, n_elements=2)  # Pick d1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick a2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2) (e1*b2), altstack = [sixthComponent]
        compute_fifth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick b2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2) (e1*b2) (b1*f2),
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick b1
        compute_fifth_component += pick(position=7, n_elements=2)  # Pick f2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2) ( (e1*b2) + (b1*f2) + (c1*d2) )*xi,
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=23, n_elements=2)  # Pick c1
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick d2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*a2) ( (e1*b2) + (b1*f2) + (c1*d2) )*xi (a1*e2),
        # altstack = [sixthComponent]
        compute_fifth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_fifth_component += pick(position=9, n_elements=2)  # Pick e2
        compute_fifth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2,
        # altstack = [sixthComponent, (d1*a2) + ( (e1*b2) + (b1*f2) + (c1*d2) )*xi + (a1*e2)]
        compute_fifth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fifth component ---------------------------------------------

        # Computation of fourth component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = pick(position=15, n_elements=2)  # Pick d1
        compute_fourth_component += pick(position=5, n_elements=2)  # Pick e2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2) (e1*f2*xi),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick e1
        compute_fourth_component += pick(position=5, n_elements=2)  # Pick f2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2) (e1*f2*xi) (a1*d2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=25, n_elements=2)  # Pick a1
        compute_fourth_component += pick(position=11, n_elements=2)  # Pick d2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2) (e1*f2*xi) (a1*d2) (b1*c2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=25, n_elements=2)  # Pick b1
        compute_fourth_component += pick(position=15, n_elements=2)  # Pick c2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*e2) (e1*f2*xi) (a1*d2) (b1*c2) (c1*a2),
        # altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += pick(position=25, n_elements=2)  # Pick c1
        compute_fourth_component += pick(position=21, n_elements=2)  # Pick a2
        compute_fourth_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2,
        # altstack = [sixthComponent, fifthComponent, (d1*e2) + (e1*f2*xi) + (a1*d2) + (b1*c2) + (c1*a2)]
        compute_fourth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of fourth component --------------------------------------------

        # Computation of third component ----------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*f2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = pick(position=15, n_elements=2)  # Pick d1
        compute_third_component += Script.parse_string("OP_2OVER")  # Pick f2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*f2) (e1*e2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=15, n_elements=2)  # Pick e1
        compute_third_component += pick(position=7, n_elements=2)  # Pick e2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*f2) (e1*e2) (b1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=23, n_elements=2)  # Pick b1
        compute_third_component += pick(position=11, n_elements=2)  # Pick d2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 ( (d1*f2) + (e1*e2) + (b1*d2) + (c1*b2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=15, n_elements=2)  # Pick b2
        compute_third_component += pick(position=25, n_elements=2)  # Pick b2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 ( (d1*f2) + (e1*e2) + (b1*d2) + (c1*b2) )*xi
        # (a1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += pick(position=23, n_elements=2)  # Pick a1
        compute_third_component += pick(position=11, n_elements=2)  # Pick c2
        compute_third_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, ( (d1*f2) + (e1*e2) + (b1*d2) + (c1*b2) )*xi +
        # (a1*c2)]
        compute_third_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component ---------------------------------------------

        # Computation of second component ---------------------------------------------------

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*c2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = pick(position=15, n_elements=2)  # Pick d1
        compute_second_component += pick(position=9, n_elements=2)  # Pick c2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 f2 (d1*c2) (e1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=15, n_elements=2)  # Pick e1
        compute_second_component += pick(position=9, n_elements=2)  # Pick d2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*c2) ( (e1*d2) + (c1*f2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += Script.parse_string("OP_2ROT")  # Roll f2
        compute_second_component += pick(position=21, n_elements=2)  # Pick c1
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*c2) ( (e1*d2) + (c1*f2) )*xi (a1*b2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=23, n_elements=2)  # Pick a1
        compute_second_component += pick(position=13, n_elements=2)  # Pick b2
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2 (d1*c2) ( (e1*d2) + (c1*f2) )*xi (a1*b2) (b1*a2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=15, n_elements=2)  # Pick a2
        compute_second_component += pick(position=25, n_elements=2)  # Pick b1
        compute_second_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 c1 d1 e1 a2 b2 c2 d2 e2,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent,
        # (d1*c2) + ( (e1*d2) + (c1*f2) )*xi + (a1*b2) + (b1*a2)]
        compute_second_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component --------------------------------------------

        # Computation of first component ----------------------------------------------------

        # After this, the stack is: a1 b1 d1 e1 a2 b2 c2 d2 (e2*c1),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component = roll(position=15, n_elements=2)  # Roll c1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 e1 a2 b2 c2 (e2*c1) (d1*d2),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += roll(position=13, n_elements=2)  # Roll d1
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll d2
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 b1 a2 b2 ( (e2*c1) + (d1*d2) + (e1*c2) ),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT")  # Roll c2
        compute_first_component += roll(position=11, n_elements=2)  # Roll e1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a1 a2 ( (b1*b2) + (e2*c1) + (d1*d2) + (e1*c2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2SWAP")  # Roll b2
        compute_first_component += roll(position=7, n_elements=2)  # Roll b1
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += self.fq4.base_field.mul_by_fq2_non_residue(
            self=self.fq4.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: (a1*a2) + ( (b1*b2) + (e2*c1) + (d1*d2) + (e1*c2) )*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")  # Roll a1 and a2
        compute_first_component += self.fq4.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        if take_modulo:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.fq4.base_field.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )

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
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 10))

        return out

    def miller_loop_output_square(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring of the Miller output in F_q^12 as a cubic extension of F_q^4."""
        return MillerOutputOperations.square(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^12 as a cubic extension of F_q^4."""
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def line_eval_times_eval_times_miller_loop_output(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of somewhat sparse element by dense element in F_q^12 as a cubic extension of F_q^4."""
        return self.line_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^12 as a cubic extension of F_q^4.."""
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_times_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^12 as a cubic extension of F_q^4."""
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^12 as a cubic extension of F_q^4."""
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    # Mapping of Miller output functions names to (function, position of the innermost denominator).
    # - Key: string name of the function
    # - Value: (function reference, position of the innermost denominator)

    function_index: ClassVar[dict] = {
        "line_eval_times_eval": (line_eval_times_eval, 6),
        "miller_loop_output_times_eval": (miller_loop_output_times_eval, 6),
        "miller_loop_output_times_eval_times_eval": (miller_loop_output_times_eval_times_eval, 11),
        "line_eval_times_eval_times_eval": (line_eval_times_eval_times_eval, 11),
        "line_eval_times_eval_times_eval_times_eval": (line_eval_times_eval_times_eval_times_eval, 11),
        "line_eval_times_eval_times_eval_times_eval_times_eval_times_eval": (
            line_eval_times_eval_times_eval_times_eval_times_eval_times_eval,
            13,
        ),
        "miller_loop_output_square": (miller_loop_output_square, 0),
        "miller_loop_output_mul": (miller_loop_output_mul, 13),
        "line_eval_times_eval_times_miller_loop_output": (line_eval_times_eval_times_miller_loop_output, 13),
        "miller_loop_output_times_eval_times_eval_times_eval": (
            miller_loop_output_times_eval_times_eval_times_eval,
            13,
        ),
        "miller_loop_output_times_eval_times_eval_times_eval_times_eval": (
            miller_loop_output_times_eval_times_eval_times_eval_times_eval,
            13,
        ),
        "miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval": (
            miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval,
            13,
        ),
    }

    def rational_form(
        self,
        function_name: str,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Adapt Miller output operation to support values in rational forms.

        An element x = (x0, ..., xn) in Fq^k is represented in rational form as X = (X0, ..., Xn, k),
        with xi = Xi/k (in Fq).

        Args:
            function_name (str): The name of the function to be adapted to values in rational form.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to perform the required function with elements written in rational form.

        """
        function, denominator_position = self.function_index[function_name]

        out = roll(denominator_position, 1) if denominator_position != 0 else pick(denominator_position, 1)
        out += Script.parse_string("OP_MUL OP_TOALTSTACK")

        out += function(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=take_modulo,  # we need it only if we are going to take the modulo later
        )

        if take_modulo:
            out += mod(
                "OP_FROMALTSTACK OP_ROT",
                is_constant_reused=is_constant_reused,
                is_mod_on_top=True,
                is_positive=positive_modulo,
            )
        else:
            out += Script.parse_string("OP_FROMALTSTACK")

        return out


miller_output_ops = MillerOutputOperations(q=fq2_script.modulus, fq4=fq4_script)
