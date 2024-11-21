"""Operations between Miller output (in F_q^4) and line evaluations for MNT4-753."""

from tx_engine import Script

from src.zkscript.bilinear_pairings.mnt4_753.fields import fq4_script

# Fq2 Script implementation
from src.zkscript.fields.fq4 import Fq4 as Fq4ScriptModel
from src.zkscript.util.utility_scripts import mod, pick, roll, verify_bottom_constant


class MillerOutputOperations(Fq4ScriptModel):
    """Arithmetic for Miller loop for MNT4-753.

    Operations are performed in F_q^4 = F_q^2[s] / (s^2 - u) = F_q[u,s] / (s^2 -  u, u^2 - 13).

    We call `sparse` elements of the form: a + bu + cus. Output of line evaluations are sparse elements in F_q^4.
    """

    def line_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of two sparse elements in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (a1, b1, c1), y := (a2, b2, c2)], `x`, `y` are two sparse elements in F_q^4
            - altstack: []

        Stack output:
            - stack:    [q, ..., z := x * y], `z` is an element in F_q^4
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
<<<<<<< Updated upstream
=======
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
>>>>>>> Stashed changes
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply two sparse elements in F_q^4.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Computation of fourth component --------------------------------------------------------

        # After this, the stack is: a1 b1 c1 a2 b2 c2, altstack = [(a2*c1) + (a1*c2)]
        compute_fourth_component = Script.parse_string("OP_2OVER")  # Pick a2 and c1
        compute_fourth_component += Script.parse_string("OP_MUL")
        compute_fourth_component += Script.parse_string("OP_OVER")  # Pick c2
        compute_fourth_component += pick(position=7, n_elements=1)  # Pick a1
        compute_fourth_component += Script.parse_string("OP_MUL OP_ADD")
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK")

        # End of computation of fourth component -------------------------------------------------

        # Computation of third component ---------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1 b1 c1 a2 b2 c2,
        # altstack = [fourthComponent, 12*(b1*c2 + c1*b2)]
        compute_third_component = Script.parse_string("OP_OVER")  # Pick b2
        compute_third_component += pick(position=4, n_elements=1)  # Pick c1
        compute_third_component += Script.parse_string("OP_MUL")
        compute_third_component += Script.parse_string("OP_OVER")  # Pick c2
        compute_third_component += pick(position=6, n_elements=1)  # Pick b1
        compute_third_component += Script.parse_string("OP_MUL")
        compute_third_component += Script.parse_string("OP_ADD OP_13 OP_MUL")
        compute_third_component += Script.parse_string("OP_TOALTSTACK")

        # End of computation of third component --------------------------------------------------

        # Computation of second component --------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1 b1 a2 b2,
        # altstack = [fourthComponent, thirdComponent, a1*b2 = b1*a2 + c1*c2*13]
        compute_second_component = Script.parse_string("OP_OVER")  # Pick b2
        compute_second_component += pick(position=6, n_elements=1)  # Pick a1
        compute_second_component += Script.parse_string("OP_MUL")
        compute_second_component += Script.parse_string("OP_SWAP")  # Roll c2
        compute_second_component += roll(position=4, n_elements=1)  # Roll c1
        compute_second_component += Script.parse_string("OP_MUL OP_13 OP_MUL")
        compute_second_component += pick(position=3, n_elements=1)  # Pick a2
        compute_second_component += pick(position=5, n_elements=1)  # Pick b1
        compute_second_component += Script.parse_string("OP_MUL OP_ADD OP_ADD")
        compute_second_component += Script.parse_string("OP_TOALTSTACK")

        # End of computation of second component -------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1*a2 + b1*b2*13,
        # altstack = [fourthComponent, thirdComponent, secondComponent]
        compute_first_component = Script.parse_string("OP_ROT")  # Roll b1
        compute_first_component += Script.parse_string("OP_MUL OP_13 OP_MUL")
        compute_first_component += Script.parse_string("OP_ROT OP_ROT")
        compute_first_component += Script.parse_string("OP_MUL OP_ADD")  # Roll a1 and a2

        # End of computation of first component --------------------------------------------------

        out += compute_fourth_component + compute_third_component + compute_second_component + compute_first_component

        if take_modulo:
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            batched_modulo = mod(stack_preparation="", is_positive=positive_modulo)
            batched_modulo += mod(is_positive=positive_modulo)
            batched_modulo += mod(is_positive=positive_modulo)
            batched_modulo += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 3))

        return out

    def miller_loop_output_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of an element by a sparse element in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (a1, b1), y := (a2, b2)], `a1`, `b1`, `a2` are in F_q^2, `b2` is in F_q
            - altstack: []

        Stack output:
            - stack:    [q, ..., z := x * y], `z` is an element in F_q^4
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
<<<<<<< Updated upstream
=======
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
>>>>>>> Stashed changes
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply an element by a sparse element in F_q^4.
        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # The stack at the beginning is: a1 b1 a2 b2 with:
        # 	- a1,b1,a2 in Fq2
        # 	- b2 in Fq

        # Computation of second component --------------------------------------------------------

        # After this, the stack is: a1 b1 a2 b2 (a1*b2*u), altstack = []
        compute_second_component = Script.parse_string("OP_DUP")  # Duplicate b2
        compute_second_component += pick(position=7, n_elements=2)  # Pick a1
        compute_second_component += Script.parse_string("OP_ROT")  # Roll b2
        compute_second_component += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        compute_second_component += fq2.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )

        # After this, the stack is: a1 b1 a2 b2, altstack = [(a1*b2*u) + b1*a2]
        compute_second_component += pick(position=6, n_elements=2)  # Pick b1
        compute_second_component += pick(position=6, n_elements=2)  # Pick a2
        compute_second_component += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        compute_second_component += fq2.add(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component -------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1*a2 + b1*b2*13, altstack = [secondComponent]
        compute_first_component = Script.parse_string("OP_13 OP_MUL")  # b2*13
        compute_first_component += roll(position=4, n_elements=2)  # Roll b1
        compute_first_component += Script.parse_string("OP_ROT")
        compute_first_component += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")
        compute_first_component += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        if take_modulo:
            compute_first_component += fq2.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += fq2.add(
                take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
            )

        # End of computation of first component --------------------------------------------------

        out += compute_second_component + compute_first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            batched_modulo = mod(is_positive=positive_modulo)
            batched_modulo += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)

            out += batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def line_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication of a sparse element by an element in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (a1, b1), y := (a2, b2)], `a1`, `a2`, `b2` are in F_q^2, `b1` is in F_q
            - altstack: []

        Stack output:
            - stack:    [q, ..., z := x * y], `z` is in F_q^4
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
<<<<<<< Updated upstream
=======
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
>>>>>>> Stashed changes
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply a sparse element by an element in F_q^4.
        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # The stack at the beginning is: a1 b1 a2 b2 with:
        # 	- a1,a2,b2 in Fq2
        # 	- b1 in Fq

        # Computation of second component --------------------------------------------------------

        # After this, the stack is: a1 b1 a2 b2 (a2*b1*u), altstack = []
        compute_second_component = Script.parse_string("OP_2OVER")  # Duplicate a2
        compute_second_component += pick(position=6, n_elements=1)  # Pick b1
        compute_second_component += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        compute_second_component += fq2.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )

        # After this, the stack is: a1 b1 a2 b2, altstack = [(a1*b2) + u*b1*a2]
        compute_second_component += Script.parse_string("OP_2OVER")  # Duplicate b2
        compute_second_component += pick(position=10, n_elements=2)  # Pick a1
        compute_second_component += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        compute_second_component += fq2.add(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component -------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: # After this, the stack is: a1*a2 + b1*b2*13, altstack = [secondComponent]
        compute_first_component = roll(position=4, n_elements=1)  # Roll b1
        compute_first_component += Script.parse_string("OP_13 OP_MUL")  # Compute b1*13
        compute_first_component += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")
        compute_first_component += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        if take_modulo:
            compute_first_component += fq2.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += fq2.add(
                take_modulo=False,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )

        # End of computation of first component --------------------------------------------------

        out += compute_second_component + compute_first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            batched_modulo = mod(is_positive=positive_modulo)
            batched_modulo += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
            out += batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def line_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^4."""
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def line_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^4."""
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
        """Multiplication in F_q^4."""
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

    def miller_loop_output_square(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring of the Miller output in F_q^4."""
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
        """Multiplication in F_q^4."""
        return MillerOutputOperations.mul(
            self,
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
        """Multiplication in F_q^4."""
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
        """Multiplication in F_q^4."""
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
        """Multiplication in F_q^4."""
        return MillerOutputOperations.mul(
            self,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )


miller_output_ops = MillerOutputOperations(q=fq4_script.MODULUS, base_field=fq4_script.BASE_FIELD)
