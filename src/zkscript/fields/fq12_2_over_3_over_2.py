from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script, pick, roll


class Fq12:
    r"""F_q^12 as quadratic extension of F_q^6, which is built as cubic extension of F_q^2.

    F_q^12 = F_q^6[u] / u^2 - v, F_q^6 = F_q^2[v] / v^3 - NON_RESIDUE_OVER_FQ2
    """

    def __init__(self, q: int, fq2, fq6, gammas_frobenius: list[list[int]] | None = None):
        # Characteristic of the field
        self.MODULUS = q
        # Fq2 implementation
        self.FQ2 = fq2
        # Fq6 implementation
        self.FQ6 = fq6
        # Gammas for the Frobenius - list of [gamma1,gamma2,...,gamma11] where gammai = [gammai1, .., gammai6],
        # with gammaij = list of coefficients of NON_RESIDUE_OVER_FQ2.power(j * (q**i-1)//6)
        self.GAMMAS_FROBENIUS = gammas_frobenius

    def mul(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^12.

        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y
        Assumption on data:
            - X and Y are passed as couples of elements of Fq6
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq6 implementation
        fq6 = self.FQ6

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # Computation of second component ---------------------------------------------------------

        # After this, the stack is: x0 x1 y0 y1 (x_0 * y_1)
        compute_second_component = (
            Script.parse_string("OP_2OVER OP_2OVER")
            + pick(position=9, n_elements=2)
            + Script.parse_string("OP_2ROT OP_2ROT")
        )  # Pick y1
        compute_second_component += pick(position=29, n_elements=6)  # Pick x0
        compute_second_component += fq6.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: x0 x1 y0 y1 (x_0 * y_1) (x1 * y0)
        compute_second_component += (
            pick(position=15, n_elements=4) + pick(position=21, n_elements=2) + Script.parse_string("OP_2ROT OP_2ROT")
        )  # Pick y0
        compute_second_component += pick(position=29, n_elements=6)  # Pick x1
        compute_second_component += fq6.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: x0 x1 y0 y1, altstack = [secondComponent]
        compute_second_component += fq6.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string(
            "OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK"
        )

        # End of computation of second component --------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: x_0 y_0, altstack = [secondComponent, (x_1 * y_1 * v)]
        compute_first_component = (
            roll(position=15, n_elements=4) + roll(position=17, n_elements=2) + Script.parse_string("OP_2ROT OP_2ROT")
        )  # Roll x1
        compute_first_component += fq6.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq6.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += Script.parse_string(
            "OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK"
        )

        # After this, the stack is: firstComponent, altstack = [secondComponent]
        compute_first_component += fq6.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += Script.parse_string(
            "OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK"
        )
        if take_modulo:
            compute_first_component += fq6.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            compute_first_component += fq6.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of first component ---------------------------------------------------

        out += compute_second_component + compute_first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
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
            out += Script.parse_string(
                "OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK"
            )

        return out

    def square(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring in F_q^12.

        Input parameters:
            - Stack: q .. X
            - Altstack: []
        Output:
            - X**2
        Assumption on data:
            - X is passed as as a couple of elements of Fq6: X = x0 x1, x0 = a b c, x1 = d e f
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq6 implementation
        fq2 = self.FQ2

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # Computation of sixth component ---------------------------------------------------------

        # After this, the stack is: a b c d e f (b*e)
        compute_sixth_component = Script.parse_string("OP_2OVER")  # Pick e
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick b
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f (b*e) (a*f)
        compute_sixth_component += Script.parse_string("OP_2OVER")  # Pick f
        compute_sixth_component += pick(position=15, n_elements=2)  # Pick a
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f, altstack = [((b*e) + (a*f) + (c*d))]
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick c
        compute_sixth_component += pick(position=11, n_elements=2)  # Pick d
        compute_sixth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_sixth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Computation of fifth component ---------------------------------------------------------

        # After this, the stack is: a b c d e f (a*e), altstack = [sixthComponent]
        compute_fifth_component = Script.parse_string("OP_2OVER")  # Pick e
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick a
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f (a*e) (c*f*xi), altstack = [sixthComponent]
        compute_fifth_component += Script.parse_string("OP_2OVER")  # Pick f
        compute_fifth_component += pick(position=11, n_elements=2)  # Pick c
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f, altstack = [sixthComponent, [(a*e) + (c*f*xi) + (b*d)]]
        compute_fifth_component += pick(position=13, n_elements=2)  # Pick b
        compute_fifth_component += pick(position=11, n_elements=2)  # Pick d
        compute_fifth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fifth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Computation of fourth component ---------------------------------------------------------

        # After this, the stack is: a b c d e f (c*e), altstack = [sixthComponent, fifthComponent]
        compute_fourth_component = Script.parse_string("OP_2OVER")  # Pick e
        compute_fourth_component += pick(position=9, n_elements=2)  # Pick c
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f [(c*e) + (b*f)]*xi, altstack = [sixthComponent, fifthComponent]
        compute_fourth_component += Script.parse_string("OP_2OVER")  # Pick f
        compute_fourth_component += pick(position=13, n_elements=2)  # Pick b
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a b c d e f, altstack = [sixthComponent, fifthComponent, [(c*e) + (b*f)]*xi + a*d]]
        compute_fourth_component += pick(position=13, n_elements=2)  # Pick a
        compute_fourth_component += pick(position=9, n_elements=2)  # Pick d
        compute_fourth_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_fourth_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Compute third component -------------------------------------------------------------------

        # After this, the stack is: a b c d e f (d*e),
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component = Script.parse_string("OP_2OVER")  # Pick e
        compute_third_component += pick(position=7, n_elements=2)  # Pick d
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f (d*e) f^2*xi,
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += Script.parse_string("OP_2OVER")  # Pick f
        compute_third_component += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f f^2*xi 2*[(d*e) + (a*c)],
        # altstack = [sixthComponent, fifthComponent, fourthComponent]
        compute_third_component += Script.parse_string("OP_2SWAP")  # Roll (d*e)
        compute_third_component += pick(position=15, n_elements=2)  # Pick a
        compute_third_component += pick(position=13, n_elements=2)  # Pick c
        compute_third_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_2")
        compute_third_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, 2*[f^2*xi 2*[(d*e) + (a*c)] + b^2]]
        compute_third_component += pick(position=13, n_elements=2)  # Pick b
        compute_third_component += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Compute second component ------------------------------------------------------------------

        # After this, the stack is: a b c d e f 2*(e*f),
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component = Script.parse_string("OP_2OVER")  # Pick e
        compute_second_component += Script.parse_string("OP_2OVER")  # Pick f
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_2")
        compute_second_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f xi*[c^2 + 2*e*f],
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=9, n_elements=2)  # Pick c
        compute_second_component += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.mul_by_non_residue(
            take_modulo=False, check_constant=False, clean_constant=False
        )

        # After this, the stack is: a b c d e f xi*[c^2 + 2*e*f] 2*a*b,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent]
        compute_second_component += pick(position=13, n_elements=2)  # Pick a
        compute_second_component += pick(position=13, n_elements=2)  # Pick b
        compute_second_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_2")
        compute_second_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a b c d e f,
        # altstack = [sixthComponent, fifthComponent, fourthComponent, thirdComponent, xi*[c^2 + 2*e*f] + 2*a*b + d^2]
        compute_second_component += pick(position=9, n_elements=2)  # Pick d
        compute_second_component += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Compute first component -------------------------------------------------------------------

        # After this, the stack is: a b c e (d*f)
        compute_first_component = Script.parse_string("OP_2ROT")  # Roll d
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a e (d*f) (b*c)
        compute_first_component += roll(position=7, n_elements=2)  # Pick b
        compute_first_component += roll(position=7, n_elements=2)  # Pick c
        compute_first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a e 2*[(d*f)+(b*c)]
        compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += Script.parse_string("OP_2")
        compute_first_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a xi*[e^2 + 2*[(d*f)+(b*c)]]
        compute_first_component += Script.parse_string("OP_2SWAP")
        compute_first_component += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: a^2 + xi*[e^2 + 2*[(d*f)+(b*c)]]
        compute_first_component += Script.parse_string("OP_2SWAP")
        compute_first_component += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
        if take_modulo:
            compute_first_component += fq2.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            compute_first_component += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)

        # -------------------------------------------------------------------------------------------

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
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_2 OP_MUL OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_2 OP_MUL OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_2 OP_MUL OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_2 OP_MUL OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_2 OP_MUL OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_2 OP_MUL OP_ROT")
            if is_constant_reused:
                out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            else:
                out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD")
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")
            out += Script.parse_string(
                "OP_FROMALTSTACK OP_2 OP_MUL OP_FROMALTSTACK OP_2 OP_MUL OP_FROMALTSTACK OP_2 OP_MUL"
            )
            out += Script.parse_string(
                "OP_FROMALTSTACK OP_2 OP_MUL OP_FROMALTSTACK OP_2 OP_MUL OP_FROMALTSTACK OP_2 OP_MUL"
            )

        return out

    def conjugate(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Conjugate in F_q^12.

        Input parameters:
            - Stack: q .. X
            - Altstack: []
        Output:
            - Conjugate(X)
        Assumption on data:
            - X is passed as as a couple of elements of Fq6 (see Fq6.py)
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq6 implementation
        fq6 = self.FQ6

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        out += fq6.negate(take_modulo=False, check_constant=False, clean_constant=False)

        if take_modulo:
            # Put x1 on altstack
            out += Script.parse_string(
                "OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK"
            )
            # Put everything except x00 on altstack
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK")

            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # Mod out x00
            out += fetch_q
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")

            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            if is_constant_reused:
                out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            else:
                out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD")

        return out

    def frobenius_odd(
        self,
        n: int,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        r"""Frobenius for odd powers n = 2k + 1 in F_q^12.

        Then, Frobenius is computed via the isomorphism: F_q^12 \sim F_q^2[u,v] / (u^2 - v, v^3 - NON_RESIDUE_OVER_FQ2)
        \sim F_q^2[t] / (t^6 - NON_RESIDUE_OVER_FQ2)

        Input parameters:
            - Stack: q .. X
            - Altstack:
        Output:
            - X**q**(n)
        Assumption on data:
            - X is passed as as a sixtuple of elements of Fq2. Namely, X = a b c d e f
        """
        assert n % 2 == 1
        assert n % 12 != 0

        # Fq6 implementation
        fq2 = self.FQ2
        # Gammas
        gammas = self.GAMMAS_FROBENIUS[n % 12 - 1]

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # After this, the stack is: b c d Conjugate(a) e f
        a_conjugate = roll(position=11, n_elements=2)  # Bring a on top of the stack
        a_conjugate += fq2.conjugate(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Conjugate a
        a_conjugate += Script.parse_string("OP_2ROT OP_2ROT")  # Bring e and f on top of the stack

        # After this, the stack is: c d Conjugate(a) [Conjugate(b) * gamma12] e f
        b_conjugate_times_gamma12 = roll(position=11, n_elements=2)  # Bring b on top of the stack
        b_conjugate_times_gamma12 += fq2.conjugate(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Conjugate b
        b_conjugate_times_gamma12 += nums_to_script(gammas[1])  # gamma12
        b_conjugate_times_gamma12 += fq2.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        b_conjugate_times_gamma12 += Script.parse_string("OP_2ROT OP_2ROT")  # Bring e and f on top of the stack

        # After this, the stack is: d Conjugate(a) [Conjugate(b) * gamma12] [Conjugate(c) * gamma14] e f
        c_conjugate_gamma14 = roll(position=11, n_elements=2)  # Bring c on top of the stack
        c_conjugate_gamma14 += fq2.conjugate(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Conjugate c
        c_conjugate_gamma14 += nums_to_script(gammas[3])  # gamma14
        c_conjugate_gamma14 += fq2.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        c_conjugate_gamma14 += Script.parse_string("OP_2ROT OP_2ROT")  # Bring e and f on top of the stack

        # After this, the stack is: Conjugate(a) [Conjugate(b) * gamma12] [Conjugate(c) * gamma14]
        # [Conjugate(d) * gamma11] e f
        d_conjugate_gamma11 = roll(position=11, n_elements=2)  # Bring d on top of the stack
        d_conjugate_gamma11 += fq2.conjugate(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Conjugate d
        d_conjugate_gamma11 += nums_to_script(gammas[0])  # gamma11
        d_conjugate_gamma11 += fq2.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        d_conjugate_gamma11 += Script.parse_string("OP_2ROT OP_2ROT")  # Bring e and f on top of the stack

        # After this, the stack is: Conjugate(a) [Conjugate(b) * gamma12] [Conjugate(c) * gamma14]
        # [Conjugate(d) * gamma11] [Conjugate(e) * gamma13] f
        e_conjugate_gamma13 = Script.parse_string("OP_2SWAP")  # Bring e on top of the stack
        e_conjugate_gamma13 += fq2.conjugate(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Conjugate e
        e_conjugate_gamma13 += nums_to_script(gammas[2])  # gamma13
        e_conjugate_gamma13 += fq2.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        e_conjugate_gamma13 += Script.parse_string("OP_2SWAP")  # Bring f on top of the stack

        # After this, the stack is: Conjugate(a) [Conjugate(b) * gamma12] [Conjugate(c) * gamma14]
        # [Conjugate(d) * gamma11] [Conjugate(e) * gamma13] [Conjugate(f) * gamma15]
        f_conjugate_gamma15 = fq2.conjugate(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Conjugate f
        f_conjugate_gamma15 += nums_to_script(gammas[4])  # gamma15
        f_conjugate_gamma15 += fq2.mul(
            take_modulo=take_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )  # Multiply

        out += (
            a_conjugate
            + b_conjugate_times_gamma12
            + c_conjugate_gamma14
            + d_conjugate_gamma11
            + e_conjugate_gamma13
            + f_conjugate_gamma15
        )

        return out

    def frobenius_even(
        self,
        n: int,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        r"""Frobenius for even power n = 2k in F_q^12.

        Then, Frobenius is computed via the isomorphism: F_q^12 \sim F_q^2[u,v] / (u^2 - v, v^3 - NON_RESIDUE_OVER_FQ2)
        \sim F_q^2[t] / (t^6 - NON_RESIDUE_OVER_FQ2)

        Input parameters:
            - Stack: q .. X
            - Altstack:
        Output:
            - X**q**n
        Assumption on data:
            - X is passed as as a sixtuple of elements of Fq2. Namely, X = a b c d e f
        """
        assert n % 2 == 0
        assert n % 12 != 0

        # Fq6 implementation
        fq2 = self.FQ2
        # Gammas
        gammas = self.GAMMAS_FROBENIUS[n % 12 - 1]

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # After this, the stack is: b c d a e f
        a = roll(position=11, n_elements=2)  # Bring a on top of the stack
        if take_modulo:
            a += Script.parse_string("OP_SWAP")
            a += Script.parse_string("OP_DEPTH OP_1SUB OP_PICK OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            a += Script.parse_string("OP_SWAP OP_ROT")
            a += Script.parse_string("OP_OVER OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD")
        a += Script.parse_string("OP_2ROT OP_2ROT")  # Bring e and f on top of the stack

        # After this, the stack is: c d a [b * gamma22] e f
        b_gamma22 = roll(position=11, n_elements=2)  # Bring b on top of the stack
        b_gamma22 += nums_to_script(gammas[1])  # gamma22
        b_gamma22 += fq2.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        b_gamma22 += Script.parse_string("OP_2ROT OP_2ROT")  # Bring e and f on top of the stack

        # After this, the stack is: d a [b * gamma12] [c * gamma24] e f
        c_gamma24 = roll(position=11, n_elements=2)  # Bring c on top of the stack
        c_gamma24 += nums_to_script(gammas[3])  # gamma24
        c_gamma24 += fq2.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        c_gamma24 += Script.parse_string("OP_2ROT OP_2ROT")  # Bring e and f on top of the stack

        # After this, the stack is: a [b * gamma12] [c * gamma14] [d * gamma21] e f
        d_gamma21 = roll(position=11, n_elements=2)  # Bring d on top of the stack
        d_gamma21 += nums_to_script(gammas[0])  # gamma21
        d_gamma21 += fq2.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        d_gamma21 += Script.parse_string("OP_2ROT OP_2ROT")  # Bring e and f on top of the stack

        # After this, the stack is: a [b * gamma12] [c * gamma14] [d * gamma21] [e * gamma23] f
        e_gamma23 = Script.parse_string("OP_2SWAP")  # Bring e on top of the stack
        e_gamma23 += nums_to_script(gammas[2])  # gamma23
        e_gamma23 += fq2.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        e_gamma23 += Script.parse_string("OP_2SWAP")  # Bring f on top of the stack

        # After this, the stack is: a [b * gamma12] [c * gamma14] [d * gamma21] [e * gamma23] [f * gamma25]
        f_gamma25 = nums_to_script(gammas[4])  # gamma25
        f_gamma25 += fq2.mul(
            take_modulo=take_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )  # Multiply

        out += a + b_gamma22 + c_gamma24 + d_gamma21 + e_gamma23 + f_gamma25

        return out
