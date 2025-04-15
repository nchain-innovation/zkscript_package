"""Bitcoin scripts that perform arithmetic operations in a cubic extension of F_q^4."""

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.fields.fq4 import Fq4
from src.zkscript.fields.prime_field_extension import PrimeFieldExtension
from src.zkscript.util.utility_scripts import mod, pick, roll, verify_bottom_constant


class Fq12Cubic(PrimeFieldExtension):
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^12 = F_q^4[v] / v^3 - non_residue_over_fq4.

    F_q^12 = F_q^4[v] / v^3 - non_residue_over_fq4 is a cubic extension of F_q^4 = F_q^2[u] / u^2 -
    non_residue_over_fq2.

    Elements in F_q^12 are of the form `a + b * v + c * v^2`, where `a`, `b`, `c` are elements of F_q^4, `v^3` is equal
    to the cubic fq4_non_residue, and the arithmetic operations `+` and `*` are derived from the operations in
    F_q^4.

    The mutliplication by fq4_non_residue is specified by defining the method self.fq4.mul_by_fq4_non_residue.

    Attributes:
        modulus (int): The characteristic of the field F_q.
        extension_degree (int): The extension degree over the prime field, equal to 12.
        prime_field: The Bitcoin Script implementation of the prime field F_q.
        fq4 (Fq4): Bitcoin script instance to perform arithmetic operations in F_q^4.
    """

    def __init__(self, q: int, fq4: Fq4):
        """Initialise F_q^12, the cubic extension of F_q^4.

        Args:
            q (int): The characteristic of the field F_q.
            fq4 (Fq4): Bitcoin script instance to perform arithmetic operations in F_q^4.
        """
        self.modulus = q
        self.extension_degree = 12
        self.prime_field = Fq(q)
        self.fq4 = fq4

    def mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^12.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, ..., x11), y := (y0, y1, ..., y11)], `x`, `y` are triplets of elements of
                F_q^4
            - altstack: []

        Stack output:
            - stack:    [q, ..., x * y]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply two elements in F_q^12.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation of third component ---------------------------------------------------------

        # After this, the stack is: x0 x1 x2 y0 y1 y2 (x2*y0)
        compute_third_component = pick(position=15, n_elements=4)  # Pick x2
        compute_third_component += pick(position=15, n_elements=4)  # Pick y0
        compute_third_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x1 x2 y0 y1 y2 (x2*y0) (x1*y1)
        compute_third_component += pick(position=11, n_elements=4)  # Pick y1
        compute_third_component += pick(position=27, n_elements=4)  # Pick x1
        compute_third_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x1 x2 y0 y1 y2, altstack = [(x2*y0) + (x1*y1) + (x0*y2)]
        compute_third_component += pick(position=31, n_elements=4)  # Pick x0
        compute_third_component += pick(position=15, n_elements=4)  # Pick y2
        compute_third_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += self.fq4.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # End of computation of third component ---------------------------------------------------

        # Computation of second component ---------------------------------------------------------

        # After this, the stack is: x0 x1 x2 y0 y1 y2 (x2*y2*NON_RESIDUE_OVER_FQ4),
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2)]
        compute_second_component = pick(position=15, n_elements=4)  # Pick x2
        compute_second_component += pick(position=7, n_elements=4)  # Pick y2
        compute_second_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += self.fq4.mul_by_fq4_non_residue(
            self=self.fq4, take_modulo=False, check_constant=False, clean_constant=False
        )
        # After this, the stack is:  x0 x1 x2 y0 y1 y2 (x2*y2*NON_RESIDUE_OVER_FQ4) (x1*y0),
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2)]
        compute_second_component += pick(position=15, n_elements=4)  # Pick y0
        compute_second_component += pick(position=27, n_elements=4)  # Pick x1
        compute_second_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is:  x0 x1 x2 y0 y1 y2,
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2), (x2*y2*NON_RESIDUE_OVER_FQ4) + (x1*y0) + (x0*y1)]
        compute_second_component += pick(position=15, n_elements=4)  # Pick y1
        compute_second_component += pick(position=35, n_elements=4)  # Pick x0
        compute_second_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += self.fq4.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # End of computation of second component ---------------------------------------------------

        # Computation of first component -----------------------------------------------------------

        # After this, the stack is: x0 x1 y0 y2 (y1*x2),
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2), (x2*y2*NON_RESIDUE_OVER_FQ4) + (x1*y0) + (x0*y1)]
        compute_first_component = roll(position=15, n_elements=4)  # Roll x2
        compute_first_component += roll(position=11, n_elements=4)  # Roll y1
        compute_first_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 y0 [(y1*x2) + (y2*x1)] * NON_RESIDUE_OVER_FQ2,
        # altstack = [(x2*y0) + (x1*y1) + (x0*y2), (x2*y2*s) + (x1*y0) + (x0*y1)]
        compute_first_component += roll(position=15, n_elements=4)  # Roll x1
        compute_first_component += roll(position=11, n_elements=4)  # Roll y2
        compute_first_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += self.fq4.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += self.fq4.mul_by_fq4_non_residue(
            self=self.fq4, take_modulo=False, check_constant=False, clean_constant=False
        )
        # After this, the stack is: firstComponent, altstack = [thirdComponent, secondComponent]
        compute_first_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))
        compute_first_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 4))
        if take_modulo:
            compute_first_component += self.fq4.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.fq4.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of first component ----------------------------------------------------

        out += compute_third_component + compute_second_component + compute_first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(7):
                out += mod(is_positive=positive_modulo)
            out += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 8))

        return out

    def square(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring in F_q^12.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, ..., x11)], `x` is a triplet of elements of F_q^4
            - altstack: []

        Stack output:
            - stack:    [q, ..., x^2]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to square an element in F_q^12.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation third component ------------------------------------------------------------

        # After this, the stack is: x0 x1 x2 (2*x2*x0)
        compute_third_component = Script.parse_string("OP_2OVER OP_2OVER")  # Pick x2
        compute_third_component += pick(position=15, n_elements=4)  # Pick x0
        compute_third_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False, scalar=2)
        # After this, the stack is: x0 x1 x2, altstack = [2*x2*x0 + x1^2]
        compute_third_component += pick(position=11, n_elements=4)  # Pick x1
        compute_third_component += self.fq4.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += self.fq4.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # End of computation of third component --------------------------------------------------

        # Computation of second component --------------------------------------------------------

        # After this, the stack is: x0 x2 2x1 2*x1*x0
        compute_second_component = roll(position=7, n_elements=4)  # Roll x1
        compute_second_component += Script.parse_string("OP_2") + self.fq4.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_2OVER OP_2OVER")  # Duplicate 2*x1
        compute_second_component += pick(position=15, n_elements=4)  # Pick x0
        compute_second_component += self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x2 2x1, altstack = [thirdComponent, 2*x1*x0 + x2^2 * s]
        compute_second_component += pick(position=11, n_elements=4)  # Pick x2
        compute_second_component += self.fq4.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += self.fq4.mul_by_fq4_non_residue(
            self=self.fq4, take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.fq4.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # End of computation of second component -------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: x0, altstack = [thirdComponent, secondComponent, 2*x1*x2 * s + x0^2]
        compute_first_component = self.fq4.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += self.fq4.mul_by_fq4_non_residue(
            self=self.fq4, take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))
        compute_first_component += self.fq4.square(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 4))
        if take_modulo:
            compute_first_component += self.fq4.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.fq4.add(take_modulo=False, check_constant=False, clean_constant=False)

        # End of computation of third component --------------------------------------------------

        out += compute_third_component + compute_second_component + compute_first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(7):
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 8))

        return out
