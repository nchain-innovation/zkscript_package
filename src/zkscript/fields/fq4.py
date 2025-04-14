"""Bitcoin scripts that perform arithmetic operations in a quadratic extension of F_q^2."""

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.fields.prime_field_extension import PrimeFieldExtension
from src.zkscript.util.utility_scripts import mod, nums_to_script, pick, roll, verify_bottom_constant


def fq4_for_towering(mul_by_non_residue):
    """Export Fq4 class with a mul_by_non_residue method to construct towering extensions."""

    class Fq4ForTowering(Fq4):
        pass

    Fq4ForTowering.mul_by_non_residue = mul_by_non_residue

    return Fq4ForTowering


class Fq4(PrimeFieldExtension):
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^4 = F_q^2[u] / (u^2 - non_residue_over_fq2).

    F_q^4 = F_q^2[u] / (u^2 - non_residue_over_fq2) is a quadratic extension of F_q^2.

    Elements in F_q^4 are of the form `a + b * u`, where `a`, `b` are elements of F_q^2, `u^2` is equal to
    the non-residue over F_q^2, and the arithmetic operations `+` and `*` are derived from the operations in F_q^2.

    The non-residue over F_q^2 is specified by defining the method self.BASE_FIELD.mul_by_non_residue.

    Attributes:
        MODULUS: The characteristic of the field F_q.
        BASE_FIELD (Fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
        EXTENSION_DEGREE: The extension degree over the prime field, equal to 4.
        GAMMAS_FROBENIUS: The list of [gamma1,gamma2,...,gamma3] for the Frobenius where gammai = [gammai1],
            with gammai1 = non_residue_over_fq2.power((q**i-1)//2).
        PRIME_FIELD: The Bitcoin Script implementation of the prime field F_q.
    """

    def __init__(self, q: int, base_field, gammas_frobenius: list[list[int]] | None = None):
        """Initialise F_q^4, the quadratic extension of F_q^2.

        Args:
            q: The characteristic of the field F_q.
            base_field (Fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
            gammas_frobenius: The list of [gamma1,gamma2,...,gamma3] for the Frobenius where gammai = [gammai1],
                with gammai1 = non_residue_over_fq2.power((q**i-1)//2).
        """
        self.MODULUS = q
        self.BASE_FIELD = base_field
        self.EXTENSION_DEGREE = 4
        self.GAMMAS_FROBENIUS = gammas_frobenius
        self.PRIME_FIELD = Fq(q)

    def scalar_mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Scalar multiplication in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3), lambda := (l0, l1)], `x` is a couple of elements of F_q^2,
                `lambda` is an element of F_q^2
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
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        if take_modulo:
            # After this, the base stack is x_0 lambda lambda x1
            out += Script.parse_string("OP_2DUP OP_2ROT")  # Prepare top of stack: x_0 lambda
            # After this, the base stack is x_0 lambda, altstack = (x1 * lambda)
            out += fq2.mul(take_modulo=False)  # Compute x_1 * lambda
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            # After this, the stack is: (x0 * lambda)_0 q (x0 * lambda)_1, altstack = (x1 * lambda)
            out += fq2.mul(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            # After this, the base stack is x_1 lambda x0 lambda
            out += Script.parse_string("OP_2ROT OP_2OVER")  # Prepare top of stack: x_0 lambda
            # After this, the base stack is x_1 lambda (x0 * lambda)
            out += fq2.mul(take_modulo=False)  # Compute x_0 * lambda
            # After this, the base stack is: (x0 * lambda) (x_1 * lambda)
            out += Script.parse_string("OP_2ROT OP_2ROT")
            out += fq2.mul(take_modulo=False)

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
        """Multiplication in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (x0, x1), y := (y0, y1)], `x`, `y` are couples of elements of
                F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., scalar * x * y]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            scalar (int): The scalar to multiply the result by. Defaults to 1.

        Returns:
            Script to multiply two elements in F_q^4.
        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack in:     [x0, x1, y0, y1]
        # stack out:    [x0, x1, y0, y1]
        # altstack out: [scalar * ((x0*y1) + (x1*y0))]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += pick(position=11, n_elements=2)  # Pick x0
        out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string("OP_2SWAP")
        out += pick(position=9, n_elements=2)  # Pick x1
        out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        out += fq2.add(take_modulo=False, check_constant=False, clean_constant=False, scalar=scalar)
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # stack in:     [x0, x1, y0, y1]
        # altstack in:  [scalar * ((x0*y1) + (x1*y0))]
        # stack out:    [scalar * (x0 * y0 + x1 * y1 * NON_RESIDUE)]
        # atlstack out: [(x0*y1) + (x1*y0)]
        out += Script.parse_string("OP_2ROT")
        out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        out += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string("OP_2ROT OP_2ROT")
        out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        out += fq2.add(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            is_constant_reused=take_modulo,
            scalar=scalar,
        )

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

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
        """Squaring in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (x0, x1)], `x` is a couple of elements of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., scalar * x^2]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            scalar (int): The scalar to multiply the result by. Defaults to 1.

        Returns:
            Script to square an element in F_q^4.
        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        if take_modulo:
            # stack in:     [x0, x1]
            # stack out:    [x0, x1]
            # altstack out: [2 * scalar * * x0 * x1]
            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False, scalar=2 * scalar)
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack in:     [x0, x1]
            # altstack in:  [2 * scalar * * x0 * x1]
            # stack out:    [scalar * (x0^2 + x1^2 * NON_RESIDUE)]
            # altstack out: [2 * scalar * * x0 * x1]
            out += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
            out += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_2SWAP")
            out += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
            out += fq2.add(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
                scalar=scalar,
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        else:
            # stack in:  [x0, x1]
            # stack out: [x0, x1, scalar * (x0^2 + x1^2 * NON_RESIDUE)]
            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
            out += fq2.mul_by_non_residue(
                take_modulo=False, check_constant=False, clean_constant=False
            )  # Compute x1^2 * NON_RESIDUE
            out += Script.parse_string("OP_2SWAP")  # Roll x0
            out += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute x0^2
            out += fq2.add(take_modulo=False, check_constant=False, clean_constant=False, scalar=scalar)

            # stack out: [x0, x1, scalar * (x0^2 + x1^2 * NON_RESIDUE)]
            # stack out: [scalar * (x0^2 + x1^2 * NON_RESIDUE), 2 * scalar * x0 * x1]
            out += Script.parse_string("OP_2ROT OP_2ROT")  # Roll x0, x1
            out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False, scalar=2 * scalar)

        return out

    def add_three(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Addition of three elements in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3), y := (y0, y1, y2, y3), z := (z0, z1, z2, z3)], `x`, `y`, `z` are
                couples of elements of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., x + y + z]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to add three elements in F_q^4.
        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: x0 y0 z0, altstack = [ x1 + y1 + z1]
        out += Script.parse_string("OP_2ROT")  # Roll y1
        out += roll(position=9, n_elements=2)  # Roll x1
        out += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        if take_modulo:
            # After this, the stack is: x0 + y0 + z0, altstack = [x1 + y1 + z1]
            out += fq2.add_three(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod(is_positive=positive_modulo)
            out += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)
        else:
            # After this, the stack is: x0 + y0 + z0, altstack = [x1 + y1 + z1]
            out += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
            # After this, the stack is (x0 + y0 + z0) (x1 + y1 + z1)
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def frobenius_odd(
        self,
        n: int,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Frobenius for odd powers n = 2k + 1 in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3)], `x` is a couple of elements of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., x^(q^n)]
            - altstack: []

        Args:
            n (int): Frobenius odd power.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to compute the Frobenius endomorphism for odd powers of an element in F_q^4.
        """
        assert n % 2 == 1

        # Fq2 implementation
        fq2 = self.BASE_FIELD
        # Gammas
        gammas = self.GAMMAS_FROBENIUS[n % 4 - 1]

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: a, altstack = [Conjugate(b)*gamma]
        out += fq2.conjugate(take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False)
        out += nums_to_script(gammas)
        out += fq2.mul(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        if is_constant_reused:
            # After this, the stack is: Conjugate(a)_0 q Conjugate(a)_1
            out += fq2.conjugate(
                take_modulo=take_modulo,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=True,
            )
            # After this, the stack is: Conjugate(a) Conjugate(b)_0 q Conjugate(b)_1
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT OP_FROMALTSTACK")
        else:
            # After this, the stack is: Conjugate(a)
            out += fq2.conjugate(
                take_modulo=take_modulo,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=clean_constant,
                is_constant_reused=False,
            )
            # After this, the stack is: Conjugate(a) Conjugate(b)
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def frobenius_even(
        self,
        n: int,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Frobenius for even powers n = 2k in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3)], `x` is a couple of elements of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., x^(q^2)]
            - altstack: []

        Args:
            n (int): Frobenius even power.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to compute the Frobenius endomorphism for even powers of an element in F_q^4.
        """
        assert n % 2 == 0
        assert n % 4 != 0

        # Fq2 implementation
        fq2 = self.BASE_FIELD
        # Gammas
        gammas = self.GAMMAS_FROBENIUS[n % 4 - 1]

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: a, altstack = [b*gamma]
        out += nums_to_script(gammas)
        out += fq2.mul(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # After this, the stack is: a b*gamma
        if take_modulo:
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is [a0, q],  altstack = [b*gamma, a1 % q]
            batched_modulo = mod(stack_preparation="", is_positive=positive_modulo)
            batched_modulo += mod(
                stack_preparation="OP_TOALTSTACK", is_constant_reused=is_constant_reused, is_positive=positive_modulo
            )
            batched_modulo += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 3))
            if is_constant_reused:
                # After this, the stack is: [a, (b*gamma)_0, q, (b*gamma)_1]
                batched_modulo += roll(position=4, n_elements=1)
                batched_modulo += Script.parse_string("OP_SWAP")

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def mul_by_u(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication by u in F_q^4 = F_q^2[u] / (u^2 - non_residue_over_fq2).

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3)], `x` is a couple of elements of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., x * u]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to multiply an element by u in F_q^4.
        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        if take_modulo:
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: (x_1 * NON_RESIDUE_OVER_FQ2) x_01 x00
            out += fq2.mul_by_non_residue(
                take_modulo=True,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
            out += Script.parse_string("OP_2SWAP OP_SWAP")
            # After this, the stack is: (x_1 * NON_RESIDUE_OVER_FQ2) x_01 q (x00 % q)
            out += fetch_q + mod(stack_preparation="", is_positive=positive_modulo)
            out += mod(
                stack_preparation="OP_SWAP OP_ROT",
                is_mod_on_top=False,
                is_constant_reused=is_constant_reused,
                is_positive=positive_modulo,
            )
        else:
            # After this, the stack is: x_0 (x_1 * NON_RESIDUE_OVER_FQ2)
            out += fq2.mul_by_non_residue(
                take_modulo=False, positive_modulo=positive_modulo, check_constant=False, clean_constant=False
            )
            out += Script.parse_string("OP_2SWAP")

        return out

    def conjugate(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Conjugation in F_q^4.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2, x3)], `x` is a couple of elements of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., conjugate(x)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.

        Returns:
            Script to conjugate an element in F_q^4.
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Fq2 implementation
        fq2 = self.BASE_FIELD

        # After this, the stack is: x0 -x1
        out += fq2.negate(take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False)

        if take_modulo:
            assert clean_constant is not None
            assert is_constant_reused is not None
            # After this, the stack is: x0_0, altstack = [-x1, x0_1]
            out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 3))

            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # Mod, pull from altstack, rotate, repeat
            batched_modulo = mod(stack_preparation="", is_positive=positive_modulo)
            batched_modulo += mod(is_positive=positive_modulo)
            batched_modulo += mod(is_positive=positive_modulo)
            batched_modulo += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)

            out += fetch_q + batched_modulo

        return out
