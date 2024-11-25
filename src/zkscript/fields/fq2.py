"""Bitcoin scripts that perform arithmetic operations in a quadratic extension of F_q."""

from tx_engine import Script

from src.zkscript.util.utility_scripts import mod, nums_to_script, verify_bottom_constant


def fq2_for_towering(mul_by_non_residue):
    """Export Fq2 class with a mul_by_non_residue method to construct towering extensions."""

    class Fq2ForTowering(Fq2):
        pass

    Fq2ForTowering.mul_by_non_residue = mul_by_non_residue

    return Fq2ForTowering


class Fq2:
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^2 = F_q[x] / (x^2 - non_residue).

    F_q^2 = F_q[u] / (u^2 - non_residue) is a quadratic extension of a base field F_q.

    Elements in F_q^2 are of the form `x0 + x1 * u`, where `x0` and `x1` are elements of F_q, and `u^2` is equal to
    some `non_residue` in F_q.

    Attributes:
        MODULUS: The characteristic of the base field F_q.
        NON_RESIDUE: The non-residue element used to define the quadratic extension.
    """

    def __init__(self, q: int, non_residue: int):
        """Initialise F_q^2, the quadratic extension of F_q.

        Args:
            q: The characteristic of the base field F_q.
            non_residue: The non-residue element used to define the quadratic extension.
        """
        self.MODULUS = q
        self.NON_RESIDUE = non_residue

    def add(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Addition in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1), y := (y0, y1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x + y := (x0 + y0, x1 + y1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to add two elements in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, base stack is: x_0 y_0, altstack = (x_1 + y_1)
        sumX1Y1 = Script.parse_string("OP_ROT OP_ADD")  # Compute (x_1 + y_1)
        sumX1Y1 += Script.parse_string("OP_TOALTSTACK")

        # After this, base stack is: (x_0 + y_0), altstack = (x_1 + y_1)
        sumX0Y0 = Script.parse_string("OP_ADD")  # Compute (x_0 + y_0)

        out += sumX1Y1 + sumX0Y0

        if take_modulo:
            batched_modulo = Script()

            assert clean_constant is not None
            assert is_constant_reused is not None
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: q [(x_0 + y_0) % q], altstack = (x_1 + y_1)
            batched_modulo += mod(stack_preparation="", is_positive=positive_modulo)
            batched_modulo += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK")

        return out

    def subtract(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Subtraction in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1), y := (y0, y1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x - y := (x0 - y0, x1 - y1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to subtract two elements in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, base stack is: x_0 y_0, altstack = [(x_1 - y_1)]
        subX1Y1 = Script.parse_string("OP_ROT OP_SWAP OP_SUB")  # Compute (x_1 - y_1)
        subX1Y1 += Script.parse_string("OP_TOALTSTACK")

        # After this, base stack is:  x_0 - y_0, altstack = [(x_1 - y_1)]
        subX0Y0 = Script.parse_string("OP_SUB")  # Compute (x_0 - y_0)

        out += subX1Y1 + subX0Y0

        if take_modulo:
            batched_modulo = Script()

            assert clean_constant is not None
            assert is_constant_reused is not None
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: q [(x_0 - y_0) % q], altstack = (x_1 - y_1)
            batched_modulo += mod(stack_preparation="", is_positive=positive_modulo)
            batched_modulo += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)
            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK")

        return out

    def negate(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Negation in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., -x := (-x0, -x1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to negate an element in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        flipX1 = Script.parse_string("OP_NEGATE")  # Negate x_1
        flipX1 += Script.parse_string("OP_TOALTSTACK")

        flipX0 = Script.parse_string("OP_NEGATE")  # Negate x_0

        out += flipX1 + flipX0

        if take_modulo:
            batched_modulo = Script()

            assert clean_constant is not None
            assert is_constant_reused is not None
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: q [-x0 % q], altstack = (x_1 + y_1)
            batched_modulo += mod(is_positive=positive_modulo, stack_preparation="")
            batched_modulo += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK")

        return out

    def scalar_mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Scalar multiplication in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1), lambda]
            - altstack: []

        Stack output:
            - stack:    [q, ..., lambda * x := (lambda * x0, lambda * x1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply an element by a scalar `lambda` in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the base stack is x_0 lambda, altstack = [(x_1 * lambda)]
        X1Lambda = Script.parse_string("OP_TUCK OP_MUL")  # Compute x_0 * lambda and put it on top of the stack
        X1Lambda += Script.parse_string("OP_TOALTSTACK")

        # After this, the base stack is (x_0 * lambda), altstack = [(x_1 * lambda)]
        X0Lambda = Script.parse_string("OP_MUL")  # Compute x_1 * lambda

        out += X1Lambda + X0Lambda

        if take_modulo:
            batched_modulo = Script()

            assert clean_constant is not None
            assert is_constant_reused is not None
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: q [(x_0 * lambda) % q], altstack = (x_1 * lambda)
            batched_modulo += mod(is_positive=positive_modulo, stack_preparation="")
            batched_modulo += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK")

        return out

    def mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1), y := (y0, y1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x * y := (x_0 * y_0 + x_1 * y_1 * self.NON_RESIDUE, x_0 * y_1 + x_1 * y_0)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply two elements in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the base stack is: x_0 x_1 y_0 y_1 [(x_0 * y_0) - (x_1 * y_1)]
        firstComponent = Script.parse_string("OP_2OVER OP_2OVER")  # Duplicate X Y
        firstComponent += Script.parse_string("OP_ROT OP_MUL")  # Compute x_1 * y_1
        firstComponent += Script.parse_string("OP_TOALTSTACK")  # Place x_1 * y_1 on altstack
        firstComponent += Script.parse_string("OP_MUL")  # Compute x_0 * y_0
        firstComponent += Script.parse_string("OP_FROMALTSTACK")  # Pull x_1 * y_1 from altstack
        if self.NON_RESIDUE == -1:
            firstComponent += Script.parse_string("OP_SUB")  # Compute (x_0 * y_0 - x_1 * y_1)
        else:
            firstComponent += nums_to_script([self.NON_RESIDUE]) + Script.parse_string(
                "OP_MUL OP_ADD"
            )  # Compute (x_0 * y_0 + x_1 * y_1 * NON_RESIDUE)

        # After this, the base stack is: [(x_0 * y_0) - (x_1 * y_1)] [(x_0 * y_1) + (x_1 * y_0)]
        secondComponent = Script.parse_string("OP_2SWAP OP_MUL")  # Compute x_1 * y_0
        secondComponent += Script.parse_string("OP_2SWAP OP_MUL")  # Compute x_0 * y_1
        secondComponent += Script.parse_string("OP_ADD")  # Compute (x_0 * y_1 + x_1 * y_0)

        out += firstComponent + secondComponent

        if take_modulo:
            # After this, the stack is: [(x_0 * y_0) - (x_1 * y_1)], altstack = [(x_0 * y_1) + (x_1 * y_0)]
            # Ready for batched modulo operations
            out += Script.parse_string("OP_TOALTSTACK")

            batched_modulo = Script()

            assert clean_constant is not None
            assert is_constant_reused is not None
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            batched_modulo += mod(is_positive=positive_modulo, stack_preparation="")
            batched_modulo += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo

        return out

    def square(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x^2 := (x0^2 + x1^2 * self.NON_RESIDUE, 2 * x0 * x1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to square an element in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        if self.NON_RESIDUE == -1:
            # After this, the stack is x0 x1 (x0^2 - x1^2)
            out += Script.parse_string("OP_2DUP OP_2DUP")
            out += Script.parse_string(
                "OP_SUB OP_2SWAP OP_ADD OP_MUL"
            )  # Compute (x0 - x1), compute (x0 + x1), multiply

            if take_modulo:
                assert clean_constant is not None
                assert is_constant_reused is not None
                if clean_constant:
                    fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
                else:
                    fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

                # After this, the stack is: x0 x1 q [(x0^2 - x1^2) % q]
                out += fetch_q + mod(stack_preparation="", is_positive=positive_modulo)
                # Compute (x_0^2 - x_1^2) % q
                # After this, the stack is: [(x0^2 - x1^2) % q] (2x0x1) q

                out += mod(
                    stack_preparation="OP_2SWAP OP_MUL OP_2 OP_MUL OP_ROT",
                    is_constant_reused=is_constant_reused,
                    is_positive=positive_modulo,
                )

            else:
                out += Script.parse_string(
                    "OP_ROT OP_ROT OP_MUL OP_2 OP_MUL"
                )  # Compute 2 * x_0 * x_1 and place it on top of the stack
        else:
            # After this, the stack is x0 x1, altstack = (2 x_0 x_1)
            out += Script.parse_string("OP_2DUP OP_2 OP_MUL OP_MUL")
            out += Script.parse_string("OP_TOALTSTACK")

            # After this, the stack is: x_0^2 + x_1^2 * NON_RESIDUE
            out += (
                Script.parse_string("OP_DUP")
                + nums_to_script([self.NON_RESIDUE])
                + Script.parse_string("OP_MUL OP_MUL")
            )
            out += Script.parse_string("OP_SWAP OP_DUP OP_MUL OP_ADD")

            if take_modulo:
                batched_modulo = Script()

                assert clean_constant is not None
                assert is_constant_reused is not None
                if clean_constant:
                    fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
                else:
                    fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

                # After this, the stack is: q [firstComponent % q], altstack = secondComponent
                batched_modulo += mod(stack_preparation="", is_positive=positive_modulo)
                batched_modulo += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)

                out += fetch_q + batched_modulo
            else:
                out += Script.parse_string("OP_FROMALTSTACK")

        return out

    def add_three(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Addition of three elements in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1), y := (y0, y1), z := (z0, z1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x + y + z := (x0 + y0 + z0, x1 + y1 + z1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to add three elements in F_q^2.

        Preconditions:
            - If take_modulo is `True`, then the coordinates of x, y and z must be positive.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: x0 x1 y0 z0, altstack = [y1 + z1]
        out += Script.parse_string("OP_ROT OP_ADD OP_TOALTSTACK")
        # After this, the stack is: x1 (x0 + y0 + z0)
        out += Script.parse_string("OP_ADD OP_ROT OP_ADD")

        if take_modulo:
            assert clean_constant is not None
            assert is_constant_reused is not None
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: x1 q [(x0 + y0 + z0) % q]
            out += fetch_q + mod(stack_preparation="", is_positive=positive_modulo)
            # After this, the stack is: [(x0 + y0 + z0) % q] q (x1+y1+z1)
            out += mod(
                stack_preparation="OP_SWAP OP_ROT OP_FROMALTSTACK OP_ADD",
                is_mod_on_top=False,
                is_constant_reused=is_constant_reused,
                is_positive=positive_modulo,
            )
        else:
            out += Script.parse_string("OP_SWAP")
            # After this, the stack is: (x0 + y0 + z0) (x1 + y1 + z1)
            out += Script.parse_string("OP_FROMALTSTACK OP_ADD")

        return out

    def conjugate(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Conjugation in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., conjugate(x) := (x0, -x1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to conjugate an element in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: x0 -x1
        out += Script.parse_string("OP_NEGATE")

        if take_modulo:
            assert clean_constant is not None
            assert is_constant_reused is not None
            # After this, the stack is: x0, altstack = [-x1]
            out += Script.parse_string("OP_TOALTSTACK")

            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # Mod, pull from altstack, rotate, repeat
            batched_modulo = Script()
            batched_modulo += mod(is_positive=positive_modulo, stack_preparation="")
            batched_modulo += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo

        return out

    def mul_by_u(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication by u in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x * u := (x1 * self.NON_RESIDUE, x0)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            A script to multiply an element by u in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        if self.NON_RESIDUE != -1:
            out += nums_to_script([self.NON_RESIDUE]) + Script.parse_string("OP_MUL")
        else:
            out += Script.parse_string("OP_NEGATE")

        if take_modulo:
            batched_modulo = Script()

            assert clean_constant is not None
            assert is_constant_reused is not None
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: [x1*NON_RESIDUE % q] x0 q
            batched_modulo += mod(stack_preparation="", is_positive=positive_modulo)
            batched_modulo += mod(
                stack_preparation="OP_ROT OP_ROT", is_constant_reused=is_constant_reused, is_positive=positive_modulo
            )

            out += fetch_q + batched_modulo
        else:
            # After this, the stack is: x1*NON_RESIDUE x0
            out += Script.parse_string("OP_SWAP")

        return out

    def mul_by_one_plus_u(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication by 1 + u in F_q^2.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x * (1 + u) := (x0 + x1 * NON_RESIDUE, x0 + x1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            A script to multiply an element by 1 + u in F_q^2.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: x0 x1, altstack = [x0 + x1]
        out += Script.parse_string("OP_2DUP OP_ADD")  # Compute (x_0 + x_1)
        out += Script.parse_string("OP_TOALTSTACK")
        if self.NON_RESIDUE == -1:
            out += Script.parse_string("OP_NEGATE OP_ADD")
        elif self.NON_RESIDUE > 0:
            # After this, the stack is: x0 + x1 * NON_RESIDUE, altstack = [x0 + x1]
            out += nums_to_script([self.NON_RESIDUE]) + Script.parse_string(
                "OP_MUL OP_ADD"
            )  # Compute (x_0 + x_1 * NON_RESIDUE)
        else:
            # After this, the stack is: x0 + x1 * NON_RESIDUE, altstack = [x0 + x1]
            out += Script.parse_string(
                str(abs(self.NON_RESIDUE)) + " OP_NEGATE OP_MUL OP_ADD"
            )  # Compute (x_0 + x_1 * NON_RESIDUE)

        if take_modulo:
            batched_modulo = Script()

            assert clean_constant is not None
            assert is_constant_reused is not None
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: q [(x0 - x1) % q], altstack = [x0 + x1]
            batched_modulo += mod(stack_preparation="", is_positive=positive_modulo)
            # After this, the stack is: [(x0 - x1) % q] (x0 + x1) q
            batched_modulo += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK")

        return out
