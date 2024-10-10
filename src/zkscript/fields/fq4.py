from tx_engine import Script

from src.zkscript.util.utility_scripts import mod, nums_to_script, pick, roll, verify_constant


def fq4_for_towering(mul_by_non_residue):
    """Construct towering extensions.

    This export Fq4 class below together with a mul_by_non_residue method.
    """

    class Fq4ForTowering(Fq4):
        pass

    Fq4ForTowering.mul_by_non_residue = mul_by_non_residue

    return Fq4ForTowering


class Fq4:
    """F_q^4 built as quadratic extension of F_q^2.

    The non residue is specified by defining the method self.BASE_FIELD.mul_by_non_residue.
    """

    def __init__(self, q: int, base_field, gammas_frobenius: list[list[int]] | None = None):
        # Characteristic of the field
        self.MODULUS = q
        # Script implementation of the base field Fq2
        self.BASE_FIELD = base_field
        # Gammas for the Frobenius - list of [gamma1,gamma2,...,gamma3] where gammai = [gammai1],
        # with gammai1 = NON_RESIDUE_OVER_FQ2.power((q**i-1)//2)
        self.GAMMAS_FROBENIUS = gammas_frobenius

    def add(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Addition in F_q^4.

        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X + Y
        Assumption on data:
            - X and Y are passed as couples of elements of Fq2 (see Fq2.py)
        Variables:
            - If take_modulo is set to True, then the coordinates of X + Y are in Z_q; otherwise, the coordinates are
            not taken modulo q.

        Example:
            take_modulo = False:
                x_0 x_1 y_0 y_1 [add] --> (x_0 + y_0) (x_1 + y_1)
            take_modulo = True:
                x_0 x_1 y_0 y_1 [add] --> [(x_0 + y_0) % q] [(x_1 + y_1) % q]

        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        # After this, base stack is: x_0 y_0, altstack = (x_1 + y_1)
        out += Script.parse_string("OP_2ROT")
        out += fq2.add(take_modulo=False)  # Compute (x_1 + y_1)
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        if take_modulo:
            # After this, base stack is: (x_0 + y_0)_0 q (x_0 + y_0)_1 altstack = (x1 + y1)
            out += fq2.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )  # Compute (x_0 + y_0)
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            # After this, base stack is: (x_0 + y_0) (x_1 + y_1)
            out += fq2.add(take_modulo=False)  # Compute (x_0 + y_0)
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def fq_scalar_mul(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^4 by a scalar in F_q.

        Input parameters:
            - Stack: q .. X <lambda>
            - Altstack: []
        Output:
            - lambda * X
        Assumption on data:
            - X is passed as a couple of elements of Fq2 (see Fq2.py)
            - lambda is passed as an integer: minimally encoded, little endian
        Variables:
            - If take_modulo is set to True, then the coordinates X are in Z_q; otherwise, the coordinates are not taken
            modulo q.

        Example:
            take_modulo = False:
                x_0 x_1 lambda [scalarMul] --> (lambda * x_0) (lambda * x_1)
            take_modulo = True:
                x_0 x_1 lambda [scalarMul] --> [(lambda * x_0) % q] [(lambda * x_1) % q]

        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        # After this, the base stack is x_0 lambda, altstack = (x_1 * lambda)
        out += Script.parse_string("OP_TUCK OP_MUL OP_TOALTSTACK")
        out += Script.parse_string("OP_TUCK OP_MUL OP_TOALTSTACK")

        if take_modulo:
            # After this, base stack is: x_00 * lambda q x_01 * lambda altstack = (x_1 * lambda)
            out += fq2.scalar_mul(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            # After this, base stack is: (x_0 + y_0) (x_1 + y_1)
            out += fq2.scalar_mul(take_modulo=False)
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def scalar_mul(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Scalar multiplication in F_q^4.

        Input parameters:
            - Stack: q .. X <lambda>
            - Altstack: []
        Output:
            - lambda * X
        Assumption on data:
            - X is passed as a couple of elements of Fq2 (see Fq2.py)
            - lambda is in F_q2^2 (see Fq2.py)
        Variables:
            - If take_modulo is set to True, then the coordinates X are in Z_q; otherwise, the coordinates are not taken
            modulo q.

        Example:
            take_modulo = False:
                x_0 x_1 lambda [scalarMul] --> (lambda * x_0) (lambda * x_1)
            take_modulo = True:
                x_0 x_1 lambda [scalarMul] --> [(lambda * x_0) % q] [(lambda * x_1) % q]

        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        if take_modulo:
            # After this, the base stack is x_0 lambda lambda x1
            out += Script.parse_string("OP_2DUP OP_2ROT")  # Prepare top of stack: x_0 lambda
            # After this, the base stack is x_0 lambda, altstack = (x1 * lambda)
            out += fq2.mul(take_modulo=False)  # Compute x_1 * lambda
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            # After this, the stack is: (x0 * lambda)_0 q (x0 * lambda)_1, altstack = (x1 * lambda)
            out += fq2.mul(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod()
            out += mod(is_constant_reused=is_constant_reused)
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
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication in F_q^4.

        Input parameters:
            - Stack: q .. X Y
            - Altstack: []
        Output:
            - X * Y
        Assumption on data:
            - X and Y are passed as couples of elements of Fq2 (see Fq2.py)
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.

        Example:
            take_modulo = False:
                x_0 x_1 y_0 y_1 [mul] --> (x_0 * y_0 + x_1 * y_1 * xi) (x_0 * y_1 + x_1 * y_0)
            take_modulo = True:
                x_0 x_1 y_0 y_1 [mul] --> [(x_0 * y_0 + x_1 * y_1 * xi) % q] [(x_0 * y_1 + x_1 * y_0) % q]

        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        # After this, the stack is: x0 x1 y0 y1 y0 y1
        out += Script.parse_string("OP_2OVER OP_2OVER")
        # After this, the stack is: x0 x1 y0 y1 y0 (y1 * x0)
        out += pick(position=11, n_elements=2)  # Pick x0
        out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # After this, the stack is x0 x1 y0 y1, altstack = [(x0*y1) + (x1*y0)]
        out += Script.parse_string("OP_2SWAP")
        out += pick(position=9, n_elements=2)  # Pick x1
        out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        out += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # After this, the stack is (x0 * y0 + x1 * y1 * NON_RESIDUE), altstack = [(x0*y1) + (x1*y0)]
        out += Script.parse_string("OP_2ROT")
        out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        out += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string("OP_2ROT OP_2ROT")
        out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)

        if take_modulo:
            out += fq2.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def square(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Squaring in F_q^4.

        Input parameters:
            - Stack: q .. X
            - Altstack: []
        Output:
            - X**2
        Assumption on data:
            - X is passed as as a couple of elements of Fq2 (see Fq2.py)
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.

        Example:
            take_modulo = False:
                x_0 x_1 [square] --> (x_0^2 + x_1^2 * xi) (2 * x_0 * x_1)
            take_modulo = True:
                x_0 x_1 [square] --> [(x_0^2 + x_1^2 * xi) % q] [(2 * x_0 * x_1) % q]

        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        if take_modulo:
            # After this, the stack is: x0 x1, altstack = 2x0*x1
            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_2")
            out += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # After this, the stack is: x1^2 * xi x0^2, altstack = 2x0*x1
            out += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
            out += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_2SWAP")
            out += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
            # After this, the stack is: x1^2 * xi + x0^2, altstack = 2x0*x1
            out += fq2.add(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            # After this, the stack is: x_0 x_1 x_0 (x_1^2 * xi)
            out += Script.parse_string("OP_2OVER OP_2OVER")  # Prepare top of the stack with  x_1
            out += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)
            out += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)

            # After this, the stack is: x_0 x_1 (x_1^2 * xi) x_0^2
            out += Script.parse_string("OP_2SWAP")  # Prepare top of the stack with x_0
            out += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)

            # After this, the stack is: x_0 x_1 [(x_1^2 * xi) + x_0^2]
            out += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)

            # After this, the stack is: [(x_1^2 * xi) + x_0^2] (2 * x_0 * x_1)
            out += Script.parse_string("OP_2ROT OP_2ROT")  # Prepare top of the stack with x_0 x_1
            out += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_2")
            out += fq2.scalar_mul(
                take_modulo=False, check_constant=False, clean_constant=False
            )  # Top of the stack is now 2 * x_0 * x_1 (not mod by q)

        return out

    def add_three(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Add three elements in F_q^4.

        Input parameters:
            - Stack: q .. X Y Z
            - Altstack: []
        Output:
            - X + Y + Z
        Assumption on data:
            - X, Y and Z are passed as a couple of elements of Fq2
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        # After this, the stack is: x0 y0 z0, altstack = [ x1 + y1 + z1]
        out += Script.parse_string("OP_2ROT")  # Roll y1
        out += roll(position=9, n_elements=2)  # Roll x1
        out += fq2.add_three(take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        if take_modulo:
            # After this, the stack is: x0 + y0 + z0, altstack = [x1 + y1 + z1]
            out += fq2.add_three(
                take_modulo=True, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod()
            out += mod(is_constant_reused=is_constant_reused)
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
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Frobenius for odd powers n = 2k + 1 in in F_q^4.

        Input parameters:
            - Stack: q .. X
            - Altstack:
        Output:
            - X**q**n
        Assumption on data:
            - X is passed as as a couple of elements of Fq2. Namely, X = a b
        """
        assert n % 2 == 1
        assert n % 4 != 0

        # Fq2 implementation
        fq2 = self.BASE_FIELD
        # Gammas
        gammas = self.GAMMAS_FROBENIUS[n % 4 - 1]

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        # After this, the stack is: a, altstack = [Conjugate(b)*gamma]
        out += fq2.conjugate(take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False)
        out += nums_to_script(gammas)
        out += fq2.mul(take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False)
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        if is_constant_reused:
            # After this, the stack is: Conjugate(a)_0 q Conjugate(a)_1
            out += fq2.conjugate(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
            # After this, the stack is: Conjugate(a) Conjugate(b)_0 q Conjugate(b)_1
            out += Script.parse_string("OP_FROMALTSTACK OP_ROT OP_FROMALTSTACK")
        else:
            # After this, the stack is: Conjugate(a)
            out += fq2.conjugate(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )
            # After this, the stack is: Conjugate(a) Conjugate(b)
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def frobenius_even(
        self,
        n: int,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Frobenius for even powers n = 2k in F_q^4.

        Input parameters:
            - Stack: q .. X
            - Altstack: []
        Output:
            - X**(q**2)
        Assumption on data:
            - X is passed as as a couple of elements of Fq2 (see Fq2.py). Namely, X = a b
        """
        assert n % 2 == 0
        assert n % 4 != 0

        # Fq2 implementation
        fq2 = self.BASE_FIELD
        # Gammas
        gammas = self.GAMMAS_FROBENIUS[n % 4 - 1]

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        # After this, the stack is: a, altstack = [b*gamma]
        out += nums_to_script(gammas)
        out += fq2.mul(take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False)
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # After this, the stack is: a b*gamma
        if take_modulo:
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            batched_modulo = Script()
            # After this, the stack is [a0, q],  altstack = [b*gamma, a1 % q]
            batched_modulo += mod(is_from_alt=False)
            batched_modulo += Script.parse_string("OP_TOALTSTACK")
            batched_modulo += mod(is_from_alt=False, is_constant_reused=is_constant_reused)
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
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Multiplication by u in F_q^4 = F_q^2[u] / u^2 - NON_RESIDUE_OVER_FQ2.

        Input parameters:
            - Stack: q .. X
            - Altstack: []
        Output:
            - X * s
        Assumption on data:
            - X is passed as a couple of elements of Fq2 (see Fq2.py)
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Fq2 implementation
        fq2 = self.BASE_FIELD

        out = verify_constant(self.MODULUS, check_constant=check_constant)

        if take_modulo:
            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            # After this, the stack is: (x_1 * NON_RESIDUE_OVER_FQ2) x_01 x00
            out += fq2.mul_by_non_residue(
                take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
            )
            out += Script.parse_string("OP_2SWAP OP_SWAP")
            # After this, the stack is: (x_1 * NON_RESIDUE_OVER_FQ2) x_01 q (x00 % q)
            out += fetch_q + mod(is_from_alt=False)
            out += Script.parse_string("OP_SWAP OP_ROT")
            out += mod(is_from_alt=False, is_mod_on_top=False, is_constant_reused=is_constant_reused)
        else:
            # After this, the stack is: x_0 (x_1 * NON_RESIDUE_OVER_FQ2)
            out += fq2.mul_by_non_residue(take_modulo=False, check_constant=False, clean_constant=False)
            out += Script.parse_string("OP_2SWAP")

        return out

    def conjugate(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Conjugation in F_q^4.

        Input parameters:
            - Stack: q .. X
            - Altstack: []
        Output:
            - Conjugate(X)
        Assumption on data:
            - X is passed as a couple of elements in Fq2
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        out = verify_constant(self.MODULUS, check_constant=check_constant)

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
            batched_modulo = Script()
            batched_modulo += mod(is_from_alt=False)
            batched_modulo += mod()
            batched_modulo += mod()
            batched_modulo += mod(is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo

        return out
