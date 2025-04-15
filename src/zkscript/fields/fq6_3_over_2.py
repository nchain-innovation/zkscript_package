"""Bitcoin scripts that perform arithmetic operations in a cubic extension of F_q^2."""

from typing import Callable

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.fields.fq2 import Fq2
from src.zkscript.fields.prime_field_extension import PrimeFieldExtension
from src.zkscript.util.utility_scripts import mod, pick, roll, verify_bottom_constant


class Fq6(PrimeFieldExtension):
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^6 = F_q^2[v] / (v^3 - non_residue_over_fq2).

    F_q^6 = F_q^2[v] / (v^3 - non_residue_over_fq2) is a cubic extension of F_q^2.

    Elements in F_q^6 are of the form `a + b * v + c * v^2`, where `a`, `b`, `c` are elements of F_q^2, `v^3` is equal
    to the cubic non_residue_over_fq2, and the arithmetic operations `+` and `*` are derived from the operations in
    F_q^2.

    The cubic non_residue_over_fq2 is specified by the method self.base_field.mul_by_fq2_non_residue.

    Attributes:
        modulus (int: The characteristic of the field F_q.
        extension_degree (int): The extension degree over the prime field, equal to 6.
        prime_field: The Bitcoin Script implementation of the prime field F_q.
        base_field (Fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
        mul_by_fq6_non_residue (Callable[..., Script] | None): If Fq6 is used for towering as
            Fq^6[v] / (v^n - fq6_non_residue), this is the Bitcoin Script implementation of the multiplication by
            fq6_non_residue.
    """

    def __init__(self, q: int, base_field: Fq2, mul_by_fq6_non_residue: Callable[..., Script] | None = None):
        """Initialise F_q^6, the cubic extension of F_q^2.

        Args:
            q (int): The characteristic of the field F_q.
            base_field (Fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
            mul_by_fq6_non_residue (Callable[..., Script] | None): If Fq6 is used for towering as
                Fq^6[v] / (v^n - fq6_non_residue), this is the Bitcoin Script implementation of the multiplication
                by fq6_non_residue. Defaults to None.
        """
        self.modulus = q
        self.extension_degree = 6
        self.prime_field = Fq(q)
        self.base_field = base_field
        self.mul_by_fq6_non_residue = mul_by_fq6_non_residue

    def scalar_mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Scalar multiplication in F_q^6.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3, x4, x5), lambda := (l0, l1)], `x` is a triplet of elements of
                F_q^2, `lambda` is an element of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., x * lambda]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply an element in F_q^4 by a scalar `lambda` in F_q^2.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # After this, the stack is: x0 x1 lambda, altstack = [x2 * lambda]
        out += Script.parse_string("OP_2SWAP OP_2OVER")
        out += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
        # After this, the stack is: x0 lambda (x1*lamdba), altstack = [x2 * lambda]
        out += Script.parse_string("OP_2SWAP OP_2OVER")
        out += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)

        if take_modulo:
            # After this, the stack is: x0*lambda, altstack = [x2*lambda, x1*lambda]
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            out += self.base_field.mul(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(3):
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            # After this, the stack is: (x0 * lambda) (x1 * lambda) (x2 * lamdba)
            out += Script.parse_string("OP_2ROT OP_2ROT")
            out += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_2SWAP OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def negate(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Negation in F_q^6.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3, x4, x5)], `x` is a triplet of elements of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., -x]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to negate an element in F_q^6.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        if take_modulo:
            # After this, stack is: x0 x1, altstack = [-x2]
            out += self.base_field.negate(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            # After this, stack is: x0, altstack = [-x2, -x1]
            out += self.base_field.negate(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            # After this, stack is: -x_0, altstack = [-x2,-x1]
            out += self.base_field.negate(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(3):
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            # After this, stack is: x_1 x_2 -x_0
            out += Script.parse_string("OP_2ROT")
            out += self.base_field.negate(take_modulo=False, check_constant=False, clean_constant=False)

            # After this, stack is: x_2 -x_0 -x_1
            out += Script.parse_string("OP_2ROT")
            out += self.base_field.negate(take_modulo=False, check_constant=False, clean_constant=False)

            # After this, stack is: -x_0 -x_1 -x_2
            out += Script.parse_string("OP_2ROT")
            out += self.base_field.negate(take_modulo=False, check_constant=False, clean_constant=False)

        return out

    def mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^6.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3, x4, x5), y := (y0, y1, y2, y3, y4, y5)], `x`, `y` are triplets of
                elements of F_q^2
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
            Script to multiply two elements in F_q^6.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation of third component ---------------------------------------------------------

        # After this, the stack is: x0 x1 x2 y0 y1 y2 (x1*y1)
        compute_third_component = Script.parse_string("OP_2OVER")  # Pick y1
        compute_third_component += pick(position=11, n_elements=2)  # Pick x1
        compute_third_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x1 x2 y0 y1 y2 (x1*y1) (x0*y2)
        compute_third_component += Script.parse_string("OP_2OVER")  # Pick y2
        compute_third_component += pick(position=15, n_elements=2)  # Pick x0
        compute_third_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x1 x2 y0 y1 y2, altstack = [thirdComponent]
        compute_third_component += pick(position=11, n_elements=2)  # Pick x2
        compute_third_component += pick(position=11, n_elements=2)  # Pick y0
        compute_third_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += self.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component ---------------------------------------------------

        # Computation of second component ---------------------------------------------------------

        # After this, the stack is: x0 x1 x2 y0 y1 y2 (y1*x0)
        compute_second_component = Script.parse_string("OP_2OVER")  # Pick y1
        compute_second_component += pick(position=13, n_elements=2)  # Pick x0
        compute_second_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x1 x2 y0 y1 y2 (y1*x0) (x2*y2*xi)
        compute_second_component += Script.parse_string("OP_2OVER")  # Pick y2
        compute_second_component += pick(position=11, n_elements=2)  # Pick x2
        compute_second_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += self.base_field.mul_by_fq2_non_residue(
            self=self.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )
        # After this, the stack is: x0 x1 x2 y0 y1 y2, altstack = [thirdComponent,secondComponent]
        compute_second_component += pick(position=13, n_elements=2)  # Pick x1
        compute_second_component += pick(position=11, n_elements=2)  # Pick y0
        compute_second_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += self.base_field.add_three(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component ---------------------------------------------------

        # Computation of first component -----------------------------------------------------------

        # After this, the stack is: x0 x2 y0 y1 (y2*x1), altstack = [thirdComponent,secondComponent]
        compute_first_component = roll(position=9, n_elements=2)  # Roll x1
        compute_first_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 y0 [(y2*x1) + (x2*y1)] * xi, altstack = [thirdComponent,secondComponent]
        compute_first_component += Script.parse_string("OP_2SWAP")  # Roll y1
        compute_first_component += roll(position=7, n_elements=2)  # Roll x2
        compute_first_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += self.base_field.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += self.base_field.mul_by_fq2_non_residue(
            self=self.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )
        # After this, the stack is: firstComponent, altstack = [thirdComponent,secondComponent]
        compute_first_component += Script.parse_string("OP_2ROT OP_2ROT")
        compute_first_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        if take_modulo:
            compute_first_component += self.base_field.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.base_field.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )

        # End of computation of first component ----------------------------------------------------

        if take_modulo:
            out += compute_third_component + compute_second_component + compute_first_component

            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(3):
                out += mod(is_positive=positive_modulo)
            out += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)
        else:
            out += (
                compute_third_component
                + compute_second_component
                + compute_first_component
                + Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 4))
            )

        return out

    def square(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring in F_q^6.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3, x4, x5)], `x` is a triplet of elements of F_q^2
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
            Script to square an element in F_q^6.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Computation third component ------------------------------------------------------------

        # After this, the stack is: x0 x1 x2 x1^2
        compute_third_component = Script.parse_string("OP_2OVER")  # Pick x1
        compute_third_component += self.base_field.square(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is: x0 x1 x2 2x2 x1^2 2x2
        compute_third_component += Script.parse_string("OP_2OVER")  # Pick x2
        compute_third_component += Script.parse_string("OP_2") + self.base_field.base_field_scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_third_component += Script.parse_string("OP_2SWAP OP_2OVER")
        # After this, the stack is: x0 x1 x2 2x2, altstack = [thirdComponent]
        compute_third_component += pick(position=11, n_elements=2)  # Pick x0
        compute_third_component += self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += self.base_field.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of third component --------------------------------------------------

        # Computation of second component --------------------------------------------------------

        # After this, the stack is: x0 x1 2x2 x2^2
        compute_second_component = Script.parse_string("OP_2SWAP")  # Roll x2
        compute_second_component += self.base_field.square(
            take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_second_component += self.base_field.mul_by_fq2_non_residue(
            self=self.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )
        # After this, the stack is: x0 2x2 x1 x2^2 2x1*x0
        compute_second_component += Script.parse_string("OP_2ROT OP_2SWAP OP_2OVER")
        compute_second_component += pick(position=9, n_elements=2)  # Pick x0
        compute_second_component += self.base_field.mul(
            take_modulo=False, check_constant=False, clean_constant=False, scalar=2
        )
        # After this, the stack is: x0 2x2 x1, altstack = [thirdComponent, secondComponent]
        compute_second_component += self.base_field.add(take_modulo=False, check_constant=False, clean_constant=False)
        compute_second_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # End of computation of second component -------------------------------------------------

        # Computation of first component ---------------------------------------------------------

        # After this, the stack is: firstComponent, altstack = [thirdComponent, secondComponent]
        compute_first_component = self.base_field.mul(take_modulo=False, check_constant=False, clean_constant=False)
        compute_first_component += self.base_field.mul_by_fq2_non_residue(
            self=self.base_field, take_modulo=False, check_constant=False, clean_constant=False
        )
        compute_first_component += Script.parse_string("OP_2SWAP")  # Roll x0
        compute_first_component += self.base_field.square(take_modulo=False, check_constant=False, clean_constant=False)
        if take_modulo:
            compute_first_component += self.base_field.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
        else:
            compute_first_component += self.base_field.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )

        # End of computation of first component --------------------------------------------------

        if take_modulo:
            out += compute_third_component + compute_second_component + compute_first_component

            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            for _ in range(3):
                out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            out += (
                compute_third_component
                + compute_second_component
                + compute_first_component
                + Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 4))
            )

        return out

    def mul_by_v(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication by v in F_q^6 = F_q^2[v] / (v^3 - non_residue_over_fq2).

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3, x4, x5)], `x` is a triplet of elements of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., x * v]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply an element by v in F_q^6.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        if take_modulo:
            # After this, the stack is: x0 x1 x2*NON_RESIDUE
            out += self.base_field.mul_by_fq2_non_residue(
                self=self.base_field,
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
            # After this the stack is: x1 (x2*NON_RESIDUE) x0
            out += mod(stack_preparation="OP_2ROT OP_SWAP OP_DEPTH OP_1SUB OP_PICK", is_positive=positive_modulo)
            out += mod(
                stack_preparation="OP_SWAP OP_ROT",
                is_mod_on_top=False,
                is_constant_reused=False,
                is_positive=positive_modulo,
            )

            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # Mod out twice - after this the stack is: (x2*NON_RESIDUE) x0 x1
            out += Script.parse_string("OP_2ROT OP_SWAP")
            out += fetch_q
            out += mod(stack_preparation="", is_positive=positive_modulo)
            out += mod(
                stack_preparation="OP_SWAP OP_ROT",
                is_mod_on_top=False,
                is_constant_reused=is_constant_reused,
                is_positive=positive_modulo,
            )
        else:
            out += self.base_field.mul_by_fq2_non_residue(
                self=self.base_field, take_modulo=False, check_constant=False, clean_constant=False
            )
            out += Script.parse_string("OP_2ROT OP_2ROT")

        return out
