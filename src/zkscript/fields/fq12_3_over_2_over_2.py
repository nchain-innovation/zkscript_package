from tx_engine import Script

from src.zkscript.util.utility_scripts import mod, pick, roll, verify_bottom_constant


class Fq12Cubic:
    r"""F_q^12 as cubic extension of F_q^4, which is built as a quadratic extension of F_q^2.

    The NON_RESIDUE_OVER_FQ4 is specified by defining the method self.FQ4.mul_by_non_residue

    F_q^12 = F_q^4[v] / v^3 - NON_RESIDUE_OVER_FQ4, F_q^4 = F_q^2[u] / u^2 - NON_RESIDUE_OVER_FQ2
    """

    def __init__(self, q: int, fq2, fq4):
        # Characteristic of the field
        self.MODULUS = q
        # FQ2
        self.FQ2 = fq2
        # FQ4
        self.FQ4 = fq4

    def mul(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^12 as cubic extension.

        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y
        Assumption on data:
            - X and Y are passed as triplets of elements of Fq4
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq4 implementation
        fq4 = self.FQ4

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Computation of third component ---------------------------------------------------------

        # After this, the stack is: x0 x1 x2 y0 y1 y2 (x2*y0)
        compute_third_component = pick(position=15, n_elements=4)  # Pick x2
        compute_third_component += pick(position=15, n_elements=4)  # Pick y0
        compute_third_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x1 x2 y0 y1 y2 (x2*y0) (x1*y1)
        compute_third_component += pick(position=11, n_elements=4)  # Pick y1
        compute_third_component += pick(position=27, n_elements=4)  # Pick x1
        compute_third_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x1 x2 y0 y1 y2, altstack = [(x2*y0) + (x1*y1) + (x0*y2)]
        compute_third_component += pick(position=31, n_elements=4)  # Pick x0
        compute_third_component += pick(position=15, n_elements=4)  # Pick y2
        compute_third_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq4.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # End of computation of third component ---------------------------------------------------

        # Computation of second component ---------------------------------------------------------

        # After this, the stack is: x0 x1 x2 y0 y1 y2 (x2*y2*NON_RESIDUE_OVER_FQ4),
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2)]
        compute_second_component = pick(position=15, n_elements=4)  # Pick x2
        compute_second_component += pick(position=7, n_elements=4)  # Pick y2
        compute_second_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq4.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        # After this, the stack is:  x0 x1 x2 y0 y1 y2 (x2*y2*NON_RESIDUE_OVER_FQ4) (x1*y0),
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2)]
        compute_second_component += pick(position=15, n_elements=4)  # Pick y0
        compute_second_component += pick(position=27, n_elements=4)  # Pick x1
        compute_second_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is:  x0 x1 x2 y0 y1 y2,
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2), (x2*y2*NON_RESIDUE_OVER_FQ4) + (x1*y0) + (x0*y1)]
        compute_second_component += pick(position=15, n_elements=4)  # Pick y1
        compute_second_component += pick(position=35, n_elements=4)  # Pick x0
        compute_second_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq4.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # End of computation of second component ---------------------------------------------------

        # Computation of first component -----------------------------------------------------------

        # After this, the stack is: x0 x1 y0 y2 (y1*x2),
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2), (x2*y2*NON_RESIDUE_OVER_FQ4) + (x1*y0) + (x0*y1)]
        compute_first_component = roll(position=15, n_elements=4)  # Roll x2
        compute_first_component += roll(position=11, n_elements=4)  # Roll y1
        compute_first_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 y0 [(y1*x2) + (y2*x1)] * NON_RESIDUE_OVER_FQ2,
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2), (x2*y2*s) + (x1*y0) + (x0*y1)]
        compute_first_component += roll(position=15, n_elements=4)  # Roll x1
        compute_first_component += roll(position=11, n_elements=4)  # Roll y2
        compute_first_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq4.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq4.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: firstComponent, altstack = [thirdComponent, secondComponent]
        compute_first_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))
        compute_first_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 4))
        if take_modulo:
            compute_first_component += fq4.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            compute_first_component += fq4.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of first component ----------------------------------------------------

        out += compute_third_component + compute_second_component + compute_first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(7):
                out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 8))

        return out

    def square(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring in F_q^12 as cubic extension.

        Input parameters:
            - Stack: q .. X
            - Altstack: []
        Output:
            - X**2
        Assumption on data:
            - X is passed as as a triplet of elements of Fq4
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq2 implementation
        fq4 = self.FQ4

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Computation third component ------------------------------------------------------------

        # After this, the stack is: x0 x1 x2 (2*x2*x0)
        compute_third_component = Script.parse_string("OP_2OVER OP_2OVER")  # Pick x2
        compute_third_component += pick(position=15, n_elements=4)  # Pick x0
        compute_third_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_2") + fq4.fq_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        # After this, the stack is: x0 x1 x2, altstack = [2*x2*x0 + x1^2]
        compute_third_component += pick(position=11, n_elements=4)  # Pick x1
        compute_third_component += fq4.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq4.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # End of computation of third component --------------------------------------------------

        # Computation of second component --------------------------------------------------------

        # After this, the stack is: x0 x2 2x1 2*x1*x0
        compute_second_component = roll(position=7, n_elements=4)  # Roll x1
        compute_second_component += Script.parse_string("OP_2") + fq4.fq_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_2OVER OP_2OVER")  # Duplicate 2*x1
        compute_second_component += pick(position=15, n_elements=4)  # Pick x0
        compute_second_component += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x2 2x1, altstack = [thirdComponent, 2*x1*x0 + x2^2 * s]
        compute_second_component += pick(position=11, n_elements=4)  # Pick x2
        compute_second_component += fq4.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq4.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += fq4.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # End of computation of second component -------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: x0, altstack = [thirdComponent, secondComponent, 2*x1*x2 * s + x0^2]
        compute_first_component = fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq4.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))
        compute_first_component += fq4.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 4))
        if take_modulo:
            compute_first_component += fq4.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            compute_first_component += fq4.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of third component --------------------------------------------------

        out += compute_third_component + compute_second_component + compute_first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(7):
                out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 8))

        return out
