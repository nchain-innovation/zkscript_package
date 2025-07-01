"""Bitcoin scripts that perform arithmetic operations in a quadratic extension of F_q."""

from typing import Callable

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.fields.prime_field_extension import PrimeFieldExtension
from src.zkscript.util.utility_scripts import mod, nums_to_script, pick, roll, verify_bottom_constant


class Fq2(PrimeFieldExtension):
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^2 = F_q[x] / (x^2 - non_residue).

    F_q^2 = F_q[u] / (u^2 - non_residue) is a quadratic extension of a base field F_q.

    Elements in F_q^2 are of the form `x0 + x1 * u`, where `x0` and `x1` are elements of F_q, and `u^2` is equal to
    some `non_residue` in F_q.

    Attributes:
        modulus (int): The characteristic of the base field F_q.
        non_residue (int): The non-residue element used to define the quadratic extension.
        extension_degree (int): The extension degree over the prime field, equal to 2.
        prime_field: The Bitcoin Script implementation of the prime field F_q.
        mul_by_fq2_non_residue (Callable[..., Script] | None): If Fq2 is used for towering as
            Fq^2[v] / (v^n - fq2_non_residue), this is the Bitcoin Script implementation of the multiplication by
            fq2_non_residue.
    """

    def __init__(self, q: int, non_residue: int, mul_by_fq2_non_residue: Callable[..., Script] | None = None):
        """Initialise F_q^2, the quadratic extension of F_q.

        Args:
            q: The characteristic of the base field F_q.
            non_residue: The non-residue element used to define the quadratic extension.
            mul_by_fq2_non_residue (Callable[..., Script] | None): If Fq2 is used for towering as
                Fq^2[v] / (v^n - fq2_non_residue), this is the Bitcoin Script implementation of the multiplication by
                fq2_non_residue. Defaults to None.
        """
        self.modulus = q
        self.non_residue = non_residue
        self.extension_degree = 2
        self.prime_field = Fq(q)
        self.mul_by_fq2_non_residue = mul_by_fq2_non_residue

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
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

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

    def mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        scalar: int = 1,
    ) -> Script:
        """Multiplication in F_q^2 followed by scalar multiplication.

        The script computes the operation (x, y) --> scalar * x * y, where scalar is in Fq.

        Stack input:
            - stack:    [q, ..., x := (x0, x1), y := (y0, y1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., scalar * x * y := (
                                                    scalar * (x_0 * y_0 + x_1 * y_1 * self.non_residue),
                                                    scalar * (x_0 * y_1 + x_1 * y_0)
                                                    )
                                                    ]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            scalar (int): The scalar to multiply the result by. Defaults to `1`.

        Returns:
            Script to multiply two elements in F_q^2 and then rescale the result.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:  [.., x0, x1, y0, y1]
        # stack out: [.., x0, x1, y0, y1, scalar * ((x_0 * y_0) - (x_1 * y_1))]
        out += Script.parse_string("OP_2OVER OP_2OVER")  # Duplicate X Y
        out += Script.parse_string("OP_ROT OP_MUL")  # Compute x_1 * y_1
        out += Script.parse_string("OP_TOALTSTACK")  # Place x_1 * y_1 on altstack
        out += Script.parse_string("OP_MUL")  # Compute x_0 * y_0
        out += Script.parse_string("OP_FROMALTSTACK")  # Pull x_1 * y_1 from altstack
        if self.non_residue == -1:
            out += Script.parse_string("OP_SUB")  # Compute (x_0 * y_0 - x_1 * y_1)
        else:
            out += nums_to_script([self.non_residue]) + Script.parse_string(
                "OP_MUL OP_ADD"
            )  # Compute (x_0 * y_0 + x_1 * y_1 * non_residue)
        if scalar != 1:
            out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")

        # stack in:  [.., x0, x1, y0, y1, scalar * ((x_0 * y_0) - (x_1 * y_1))]
        # stack out: [.., scalar * ((x_0 * y_0) - (x_1 * y_1)), scalar * (x_0 * y_1 + x_1 * y_0)]
        out += Script.parse_string("OP_2SWAP OP_MUL")  # Compute x_1 * y_0
        out += Script.parse_string("OP_2SWAP OP_MUL")  # Compute x_0 * y_1
        out += Script.parse_string("OP_ADD")  # Compute (x_0 * y_1 + x_1 * y_0)
        if scalar != 1:
            out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")

        if take_modulo:
            out += Script.parse_string("OP_TOALTSTACK")
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)

            out += mod(is_positive=positive_modulo, stack_preparation="")
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)

        return out

    def square(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        scalar: int = 1,
    ) -> Script:
        """Squaring in F_q^2 followed by scalar multiplication.

        The script computes the operation x --> scalar * x^2, where scalar is in Fq.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., scalar * x^2 := (
                                                    scalar * (x0^2 + x1^2 * self.non_residue),
                                                    2 * scalar * x0 * x1
                                                    )
                                                    ]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            scalar (int): The scalar to multiply the result by. Defaults to `1`.

        Returns:
            Script to square an element in F_q^2 and rescale the result.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        if self.non_residue == -1:
            # stack in:  [.., x0, x1]
            # stack out: [.., x0, x1, scalar * (x0^2 - x1^2)]
            out += Script.parse_string("OP_2DUP OP_2DUP")
            out += Script.parse_string(
                "OP_SUB OP_2SWAP OP_ADD OP_MUL"
            )  # Compute (x0 - x1), compute (x0 + x1), multiply
            if scalar != 1:
                out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")

            # stack in:  [.., x0, x1, scalar * (x0^2 - x1^2)]
            # stack out: [.., scalar * (x0^2 - x1^2), 2 * scalar * x0 * x1]
            if take_modulo:
                out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
                out += mod(stack_preparation="", is_positive=positive_modulo)
                out += (
                    Script.parse_string("OP_2SWAP OP_MUL")
                    + nums_to_script([2 * scalar])
                    + Script.parse_string("OP_MUL OP_ROT")
                )
                out += mod(
                    stack_preparation="",
                    is_constant_reused=is_constant_reused,
                    is_positive=positive_modulo,
                )

            else:
                out += nums_to_script([2 * scalar]) + Script.parse_string("OP_2SWAP OP_MUL OP_MUL")
        else:
            # stack in:     [.., x0, x1]
            # stack out:    [.., x0, x1]
            # altstack out: [2 * scalar * x0 * x1]
            out += Script.parse_string("OP_2DUP") + nums_to_script([2 * scalar]) + Script.parse_string("OP_MUL OP_MUL")
            out += Script.parse_string("OP_TOALTSTACK")

            # stack in:     [.., x0, x1]
            # altstack in:  [2 * scalar * x0 * x1]
            # stack out:    [.., scalar * (x0^2 + x1^2 * self.non_residue)]
            # altstack out: [2 * scalar * x0 * x1]
            out += (
                Script.parse_string("OP_DUP")
                + nums_to_script([self.non_residue])
                + Script.parse_string("OP_MUL OP_MUL")
            )
            out += Script.parse_string("OP_SWAP OP_DUP OP_MUL OP_ADD")
            if scalar != 1:
                out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")

            if take_modulo:
                out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
                out += mod(stack_preparation="", is_positive=positive_modulo)
                out += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)
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
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

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
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

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
            - stack:    [q, ..., x * u := (x1 * self.non_residue, x0)]
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
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        if self.non_residue != -1:
            out += nums_to_script([self.non_residue]) + Script.parse_string("OP_MUL")
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

            # After this, the stack is: [x1*non_residue % q] x0 q
            batched_modulo += mod(stack_preparation="", is_positive=positive_modulo)
            batched_modulo += mod(
                stack_preparation="OP_ROT OP_ROT", is_constant_reused=is_constant_reused, is_positive=positive_modulo
            )

            out += fetch_q + batched_modulo
        else:
            # After this, the stack is: x1*non_residue x0
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
            - stack:    [q, ..., x * (1 + u) := (x0 + x1 * non_residue, x0 + x1)]
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
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # After this, the stack is: x0 x1, altstack = [x0 + x1]
        out += Script.parse_string("OP_2DUP OP_ADD")  # Compute (x_0 + x_1)
        out += Script.parse_string("OP_TOALTSTACK")
        if self.non_residue == -1:
            out += Script.parse_string("OP_SUB")
        else:
            # After this, the stack is: x0 + x1 * non_residue, altstack = [x0 + x1]
            out += nums_to_script([self.non_residue])
            out += Script.parse_string("OP_MUL OP_ADD")  # Compute (x_0 + x_1 * non_residue)

        out += (
            self.take_modulo(
                positive_modulo=positive_modulo, clean_constant=clean_constant, is_constant_reused=is_constant_reused
            )
            if take_modulo
            else Script.parse_string(" ".join(["OP_FROMALTSTACK"] * (self.extension_degree - 1)))
        )

        return out

    def cube(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        scalar: int = 1,
    ) -> Script:
        """Squaring in F_q^2 followed by scalar multiplication.

        The script computes the operation x --> scalar * x^3, where scalar is in Fq.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., scalar * x^3 := (
                                                    scalar * (x0^3 + 3 * x0 * x1^2 * self.non_residue),
                                                    scalar * (self.non_residue * x1^3 + 3 * x0^2 * x1)
                                                    )
                                                    ]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            scalar (int): The scalar to multiply the result by. Defaults to `1`.

        Returns:
            Script to square an element in F_q^2 and rescale the result.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()
        # stack in:     [.., x0, x1]
        # stack out:    [.., x0, x1, x0^2, x1^2]
        out += Script.parse_string("OP_2DUP OP_2DUP OP_ROT OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK OP_MUL OP_FROMALTSTACK")

        # stack in:     [.., x0, x1, x0^2, x1^2]
        # stack out:    [.., x0^2, x1^2 * non_res, x0]
        # altstack out: [self.non_residue * x1^3 + 3 * x0^2 * x1]
        out += nums_to_script([self.non_residue])
        out += Script.parse_string("OP_MUL OP_2SWAP OP_2OVER")

        out += Script.parse_string("OP_ROT OP_TUCK OP_MUL OP_TOALTSTACK")
        out += Script.parse_string("OP_3 OP_MUL OP_MUL OP_FROMALTSTACK OP_ADD OP_TOALTSTACK")

        # stack in:     [.., x0^2, x1^2 * self.non_residue, x0]
        # altstack in:  [self.non_residue * x1^3 + 3 * x0^2 * x1]
        # stack out:    [.., x0^3 + 3 * x1^2 * x0 * self.non_residue]
        # altstack out: [self.non_residue * x1^3 + 3 * x0^2 * x1]

        out += Script.parse_string("OP_TUCK OP_MUL OP_3 OP_MUL OP_TOALTSTACK")
        out += Script.parse_string("OP_MUL OP_FROMALTSTACK OP_ADD")

        # stack in:     [.., x0^3 + 3 * x1^2 * x0 * self.non_residue]
        # altstack in:  [self.non_residue * x1^3 + 3 * x0^2 * x1]

        if scalar != 1:
            out += nums_to_script([scalar])
            out += Script.parse_string("OP_TUCK OP_MUL")

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo, is_constant_reused=True)
            preparation = "OP_ROT OP_FROMALTSTACK OP_MUL OP_ROT" if scalar != 1 else "OP_FROMALTSTACK OP_ROT"
            out += mod(
                stack_preparation=preparation,
                is_mod_on_top=True,
                is_positive=positive_modulo,
                is_constant_reused=is_constant_reused,
            )

        else:
            out += Script.parse_string("OP_SWAP OP_FROMALTSTACK OP_MUL")

        return out

    def norm(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        scalar: int = 1,
    ) -> Script:
        """Compute the norm of an element x = (x0, x1).

        The script computes the operation x --> x0^2 - x1^2*self.non_residue.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x0^2 - x1^2*self.non_residue]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            scalar (int): The scalar to multiply the result by. Defaults to `1`.

        Returns:
            Script to compute the norm of an element in F_q^2.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()
        scalar_is_negative = scalar < 0
        # stack in:     [.., x0, x1]
        # stack out:    [.., x0^2 + self.non_residue * x1^2]
        out += Script.parse_string("OP_DUP OP_MUL")  # compute x1^2
        if self.non_residue != -1:
            out += nums_to_script(
                [self.non_residue if scalar_is_negative else -self.non_residue]
            )  # compute x1^2 * self.non_residue
            out += Script.parse_string("OP_MUL")
        elif scalar_is_negative:
            out += Script.parse_string("OP_NEGATE")
        out += Script.parse_string("OP_SWAP OP_DUP OP_MUL")  # compute x0^2
        out += Script.parse_string(
            "OP_SUB" if scalar_is_negative else "OP_ADD"
        )  # compute x0^2 + x1^2 * self.non_residue

        if scalar not in {1, -1}:
            out += nums_to_script([abs(scalar)])
            out += Script.parse_string("OP_MUL")  # compute x1^2 * self.non_residue * scalar

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(
                stack_preparation="",
                is_mod_on_top=True,
                is_positive=positive_modulo,
                is_constant_reused=is_constant_reused,
            )

        return out
