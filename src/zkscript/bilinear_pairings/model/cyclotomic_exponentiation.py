from math import ceil, log2

from tx_engine import Script

from src.zkscript.util.utility_scripts import pick, verify_constant


class CyclotomicExponentiation:
    def __init__(self, q: int, cyclotomic_inverse, square, mul, extension_degree: int):
        # Characteristic of the field
        self.MODULUS = q
        # Script to compute the cyclotomic inverse
        self.cyclotomic_inverse = cyclotomic_inverse
        # Script to compute the square in the field over which we are compute the cyclotomic exponentiation
        self.square = square
        # Script to compute the square in the field over which we are compute the cyclotomic exponentiation
        self.mul = mul
        # Extension degree (over Fq) of the field  over which we are compute the cyclotomic exponentiation
        self.EXTENSION_DEGREE = extension_degree

    def cyclotomic_exponentiation(
        self,
        exp_e: list[int],
        take_modulo: bool,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Compute exponetiation f^e for f in the cyclotomic subgroup.

        exp_e = [e_0, ..., e_(l-1)] such that:
            - e := sum_(i=1)^(l-1) e_i 2^i
            - e_i in {-1,0,1}
            - e_(l-1) different from 0

        Input parameters:
            - Stack: q .. X
            - Altstack: []
        Output:
            - X^e
        Assumption on data:
            - X is passed as an element in F_{q^k}
        Variables:
            - If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates
            are not taken modulo q.
        """
        # Bit size of q
        q = self.MODULUS
        BIT_SIZE_Q = ceil(log2(q))

        cyclotomic_inverse = self.cyclotomic_inverse
        square = self.square
        mul = self.mul

        N_ELEMENTS = self.EXTENSION_DEGREE

        # --------------------------------------------------------------------------------------------------------------

        out = verify_constant(q, check_constant=check_constant)

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
