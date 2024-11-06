"""cyclotomic_exponentiation module.

This module enables constructing Bitcoin scripts that perform exponentiation in the cyclotomic subgroup.
"""

from math import ceil, log2

from tx_engine import Script

from src.zkscript.util.utility_scripts import pick, verify_bottom_constant


class CyclotomicExponentiation:
    """Cyclotomic subgroup."""

    def __init__(self, q: int, cyclotomic_inverse, square, mul, extension_degree: int):
        """Initialise the cyclotomic subgroup.

        Args:
            q: The characteristic of the base field F_q.
            cyclotomic_inverse: Script to compute the cyclotomic inverse.
            square: Script to compute the square in the field over which we compute the cyclotomic exponentiation.
            mul: Script to compute the square in the field over which we compute the cyclotomic exponentiation.
            extension_degree: Extension degree (over F_q) of the field over which we compute the cyclotomic
                exponentiation.
        """
        self.MODULUS = q
        self.cyclotomic_inverse = cyclotomic_inverse
        self.square = square
        self.mul = mul
        self.EXTENSION_DEGREE = extension_degree

    def cyclotomic_exponentiation(
        self,
        exp_e: list[int],
        take_modulo: bool,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Exponentiation in the cyclotomic subgroup.

        Stack input:
            - stack:    [q, ..., x], `x` in F_{q^k}
            - altstack: []

        Stack output:
            - stack:    [q, ..., x^e]
            - altstack: []

        Args:
            exp_e (list[int]): Exponent `exp_e = [e_0, ..., e_(l-1)]` such that:
                - `e := sum_(i=1)^(l-1) e_i 2^i`
                - `e_i in {-1,0,1}`
                - `e_(l-1) different from 0`
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to perform exponentiation in the cyclotomic subgroup.
        """
        # Bit size of q
        q = self.MODULUS
        BIT_SIZE_Q = ceil(log2(q))

        cyclotomic_inverse = self.cyclotomic_inverse
        square = self.square
        mul = self.mul

        N_ELEMENTS = self.EXTENSION_DEGREE

        # --------------------------------------------------------------------------------------------------------------

        out = verify_bottom_constant(q) if check_constant else Script()

        # Prepare the stack with the copies of f and Inverse(f) needed

        # ever seen f?
        ever_seen_f = False
        # ever seen Inverse(f)?
        ever_seen_inverse = False
        # prev = 1 --> last loaded was f; prev = -1 --> last loaded was Inverse(f)
        prev = 0
        # counter for how many copies of previous element we have loaded
        count_prev = 0
        # At the end of this loop, the stack is : f .. f Inverse(f) ... Inverse(f) f ... f g according to the non-zero
        # elements in exp_e
        for i in range(len(exp_e)):
            if exp_e[i] == 1:
                if prev == 1:
                    # Duplicate f
                    out += pick(position=N_ELEMENTS - 1, n_elements=N_ELEMENTS)
                    count_prev += 1
                elif prev == -1:
                    if ever_seen_f:
                        # Duplicate f
                        out += pick(position=N_ELEMENTS + N_ELEMENTS * count_prev - 1, n_elements=N_ELEMENTS)
                        count_prev = 1
                        prev = 1
                    else:
                        # We have never seen f yet, we construct it
                        out += pick(position=N_ELEMENTS - 1, n_elements=N_ELEMENTS)  # Duplicate Inverse(f)
                        out += cyclotomic_inverse(take_modulo=False, check_constant=False, clean_constant=False)
                        prev = 1
                        count_prev = 1
                        ever_seen_f = True
                else:
                    # Never seen either, so we set up f
                    prev = 1
                    count_prev = 1
                    ever_seen_f = True
            elif exp_e[i] == -1:
                if prev == 1:
                    if ever_seen_inverse:
                        # Pick Inverse(f)
                        out += pick(position=N_ELEMENTS + N_ELEMENTS * count_prev - 1, n_elements=4)
                        prev = -1
                        count_prev = 1
                    else:
                        # We have never seen Inverse(f) yet, we construct it
                        out += pick(position=N_ELEMENTS - 1, n_elements=N_ELEMENTS)  # Duplicate f
                        out += cyclotomic_inverse(take_modulo=False, check_constant=False, clean_constant=False)
                        prev = -1
                        count_prev = 1
                        ever_seen_inverse = True
                elif prev == -1:
                    # Duplicate Inverse(f)
                    out += pick(position=N_ELEMENTS - 1, n_elements=N_ELEMENTS)
                    count_prev += 1
                else:
                    # Never seen either, so we set up Inverse(f)
                    out += cyclotomic_inverse(take_modulo=False, check_constant=False, clean_constant=False)
                    prev = -1
                    count_prev = 1
                    ever_seen_inverse = True
            else:
                pass

        # --------------------------------------------------------------------------------------------------------------

        current_size = BIT_SIZE_Q
        for i in range(len(exp_e) - 2, -1, -1):
            modulo_square = False
            modulo_multiplication = False
            clean_constant_final = False

            """
            Compute future size:

            I am at the beginning of an iteration of the cycle and I assume that squaring will not raise an overflow
            error.
            Then, I check:
                - If exp_e[i] != 0:
                    - Is squaring + multiplication raise an overflow?
                        ---> If yes, mod after squaring (no need to mod after multiplication because squaring +
                        multiplication starting from bitSizeOfQ does not raise an overflow)
                        ---> If not, is another squaring raising an error?
                            ---> If yes, mod after multiplication
                            ---> If not, do nothing
                - If exp_e[i] == 0:
                    - Is squaring twice raising an error?
                        ---> If yes, mod after squaring
                        ---> If not, do nothing
            If i == 0, always mod after multiplication
            """

            if i == 0:
                clean_constant_final = clean_constant

            if i == 0 and take_modulo:
                modulo_square = True
                if exp_e[0] != 0:
                    modulo_multiplication = True  # Mod out after last multiplication
            elif exp_e[i] != 0:
                future_size = ceil(log2(30)) + current_size * 2  # After squaring
                future_size = ceil(log2(30)) + future_size + BIT_SIZE_Q  # After squaring and multiplication

                if future_size > modulo_threshold:
                    modulo_square = True  # Mod out after squaring
                    current_size = ceil(log2(30)) + BIT_SIZE_Q * 2  # After multiplying
                else:
                    future_size_2 = ceil(log2(30)) + future_size * 2  # After another squaring
                    if future_size_2 > modulo_threshold:
                        modulo_multiplication = True  # Mod out after multiplication
                        current_size = BIT_SIZE_Q  # After multiplying
                    else:
                        current_size = future_size
            else:
                future_size = ceil(log2(30)) + current_size * 2  # After squaring
                future_size_2 = ceil(log2(30)) + future_size * 2  # After another squaring

                if future_size_2 > modulo_threshold:
                    modulo_square = True  # Mod out after squaring
                    current_size = BIT_SIZE_Q  # After modulo
                else:
                    current_size = future_size

            if exp_e[i] != 0:
                # After this, the stack is: f Conjugate(f) g^2
                out += square(
                    take_modulo=modulo_square, check_constant=False, clean_constant=False, is_constant_reused=False
                )
                out += mul(
                    take_modulo=modulo_multiplication,
                    check_constant=False,
                    clean_constant=clean_constant_final,
                    is_constant_reused=False,
                )
            else:
                # After this, the stack is: f g^2
                out += square(
                    take_modulo=modulo_square,
                    check_constant=False,
                    clean_constant=clean_constant_final,
                    is_constant_reused=False,
                )

        return out
