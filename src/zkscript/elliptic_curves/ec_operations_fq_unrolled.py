# Math modules
from math import ceil, log2

# from src.tx_engine.engine.script import Script
from tx_engine import Script

# EC arithmetic
from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackNumber

# Utility scripts
from src.zkscript.util.utility_scripts import nums_to_script, pick, roll, verify_bottom_constant


class EllipticCurveFqUnrolled:
    def __init__(self, q: int, ec_over_fq: EllipticCurveFq):
        # Characteristic of the field over which the curve is defined
        self.MODULUS = q
        # Implementation of EC operations over Fq
        self.EC_OVER_FQ = ec_over_fq

    def unrolled_multiplication(
        self,
        max_multiplier: int,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Unrolled double-and-add multiplication loop for a point in E(F_q).

        Notice that modulo_threshold is given as bit length.
        Input parameters:
            - Stack: q .. marker_a_is_zero [lambdas,a] P
            - Altstack: []
        Output:
            - P aP
        Assumption on data:
            - P is passed as a couple of integers (minimally encoded, in little endian)
            - [lambdas,a] is a list, see below for its construction
            - marker_a_is_zero: a == 0

        [lambdas,a] is the list constructed starting from:
            - exp_a, which is the binary expansion of a
            - lambdas, which is the list where:
                - lambdas[i] = the gradient needed to compute point doubling if exp_a[len(exp_a)-2-i] = 0
                - lambdas[i] = [gradient needed to compute 2T, gradient needed to compute T + P] if exp_a[i] = 1, where
                T is the intermediate value of the computation
        The list [lambdas,a] is constructed as follows: set a = (a0,a1,...,a_N), where a = sum_i 2^i ai and
        M = log_2(max_multiplier).
        Then, starting from M-1 to 0, do:
            - if N <= i <= M-1, the append at the beginning of the list: 0x00
            - if 0 <= i <= N-1:
                - if exp_a[i] == 0, then append at the beginning of the list: 0x00 lambda[i] 0x01
                - if exp_a[i] == 1, then append at the beginning of the list: lambdas[i][0] 0x01 lambdas[i][1] 0x01

        Example:
            - max_multiplier = 8
            - a = 3
        Then:
            - exp_a = (1,1)
            - lambdas = [lambda_(2T+P),lambda_2T]
            - M = log(8) = 3
            - N = log(a) = 1
        Thus:
            - [lambdas,a] = lambda_(2T+P) OP_1 lambda_2T OP_1 OP_0 OP_0 OP_0 OP_0

        Example:
            - max_multiplier = 8
            - a = 8
        Then:
            - exp_a = (0,0,0,1)
            - lambdas = [lambda_2T,lambda_2T,lambda_2T]
            - M = log(8) = 3
            - N = log(a) = 3
        Thus:
            - [lambdas,a] = OP_0 OP_0 lambda_2T OP_1 OP_0 OP_0 lambda_2T OP_1 OP_0 OP_0 lambda_2T OP_1

        The meaning of the list is the following:
            - if it starts with OP_0, then do not execute the loop
            - if it starts with OP_1:
                - execute the doubling (always needed)
                - if after the doubling there is OP_1, then execute the addition, otherwise go to the next iteration of
                the loop.

        MODULO OPERATIONS:

        As we are carrying out EC operation over the base field, each element is a single number. The formula for EC
        point doubling/addition is:

        x_(P+Q) = lambda^2 - x_P - x_Q
        y_(P+Q) = -y_P + (x_(P+Q) - x_P) * lambda

        where lambda is the gradient of the line through P and Q. Then, we have (with q exchanged for current_size in
        future steps)

        log_2(abs(x_(P+Q)) <= log_2(q^2 + 2q) = log_2(q) + log_2(q+2) <= 2 log_2(q+2)
        log_2(abs(y_(P+Q)) <= log_2(q + (q^2 + 3q) * q) = log_2(q + q^3 + 3q^2) <= log_2(q) + log_2(q^2 + 3q + 1)

        Hence, we at every step we check that the next operation doesn't make
        log_2(q) + log_2(q^2 + 3q + 1) > modulo_threshold.

        """
        # Elliptic curve arithmetic
        ec_over_fq = self.EC_OVER_FQ

        """
        Set a = (a0,a1,...,aN) where a = sum_i 2^i ai.

        At the beginning of every iteration of the loop the stack is assumed to be:
			auxiliary_data marker_doubling P T
		where:
			- T is the i-th step of the calculation of aP
			- marker_doubling is the marker that tells us if we need to double T
		If marker_doubling:
			- is OP_0 => auxiliary_data = "", move to next iteration
			- is OP_1 => the auxiliary_data is assumed to be:
				auxiliary_data_addition marker_addition lambda_(2T)
		If marker_addition:
			- is OP_0 => auxiliary_data_addition = "", after the doubling, move to next iteration
			- is OP_1 => then auxiliary_data_addition is assumed to be: lambda_(2T+P)
        """

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: marker_a_is_zero [lambdas,a] P T
        set_T = Script.parse_string("OP_2DUP")
        out += set_T

        size_q = ceil(log2(self.MODULUS))
        current_size = size_q

        # Compute aP
        # Stack in: marker_a_is_zero [lambdas, a] P T
        # Stack out: marker_a_s_zero P aP
        for i in range(int(log2(max_multiplier)) - 1, -1, -1):
            # This is an approximation, but I'm quite sure it works.
            # We always have to take into account both operations
            # because we don't know which ones are going to be executed.
            size_after_operations = 2 * 4 * current_size
            if size_after_operations > modulo_threshold or i == 0:
                take_modulo = True
                current_size = size_q
            else:
                take_modulo = False
                current_size = size_after_operations

            # Stack in: auxiliary_data marker_doubling P T
            # Stack out: auxiliary_data P T marker_doubling
            out += roll(
                position=4, n_elements=1
            )  # Roll marker to decide whether to excute the loop and the auxiliary data

            # Stack in: auxiliary_data P T marker_doubling
            # Stack out: P T if marker_doubling = 0, else P 2T
            out += Script.parse_string("OP_IF")  # Check marker for executing iteration
            out += ec_over_fq.point_algebraic_doubling(
                take_modulo=take_modulo,
                check_constant=False,
                clean_constant=False,
                verify_gradient=True,
                stack_elements={
                    "lambda": StackNumber(4, 1, False, roll),
                    "P": StackEllipticCurvePoint(
                        StackNumber(1, 1, False, roll),
                        StackNumber(0, 1, False, roll),
                    ),
                },
            )  # Compute 2T

            # Stack in: auxiliary_data_addition marker_addition P 2T
            # Stack out: auxiliary_data_addition P 2T marker_addition
            out += roll(position=4, n_elements=1)  # Roll marker for addition and auxiliary data addition

            # Stack in: auxiliary_data_addition marker_addition P 2T
            # Stack out: P 2T if marker_addition = 0, else P (2T+P)
            out += Script.parse_string(
                "OP_IF"
            )  # Check marker for +P; if we enter here, after execution, the stack is: P 2T + P
            out += ec_over_fq.point_algebraic_addition(
                take_modulo=take_modulo,
                check_constant=False,
                clean_constant=False,
                verify_gradient=True,
                stack_elements={
                    "lambda": StackNumber(4, 1, False, roll),
                    "P": StackEllipticCurvePoint(
                        StackNumber(3, 1, False, pick),
                        StackNumber(2, 1, False, pick),
                    ),
                    "Q": StackEllipticCurvePoint(
                        StackNumber(1, 1, False, roll),
                        StackNumber(0, 1, False, roll),
                    ),
                },
            )  # Compute 2T + P
            out += Script.parse_string("OP_ENDIF OP_ENDIF")  # Conclude the conditional branches

        # Stack in: marker_a_is_zero P aP
        # Stack out: P 0x00 0x00 if a == 0, else P aP
        out += roll(position=4, n_elements=1)
        out += Script.parse_string("OP_IF")
        out += Script.parse_string("OP_2DROP 0x00 0x00")
        out += Script.parse_string("OP_ENDIF")

        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")

        return out

    def unrolled_multiplication_input(
        self,
        P: list[int],
        a: int,
        lambdas: list[list[list[int]]],
        max_multiplier: int,
        load_modulus=True,
    ) -> Script:
        """Return the input script needed to execute the unrolled multiplication script above.

        lambdas is the sequence of lambdas as they are computed by executing the multiplication.
        If exp_a is the binary representation of a, then len(lambdas) = len(exp_a)-1, because the last element of exp_a
        (the most significant bit) is not used.

        The list lamdbas is computed as:
            lambdas = []
            for i in range(len(exp_a)-2,-1,-1):
                to_add = []
                to_add.append(T.get_lambda(T).to_list())
                T = T + T
                if exp_a[i] == 1:
                    to_add.append(T.get_lambda(P).to_list())
                lambdas.append(to_add)
        """
        M = int(log2(max_multiplier))

        out = nums_to_script([self.MODULUS]) if load_modulus else Script()

        # Add the lambdas
        if a == 0:
            out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * M))
        else:
            exp_a = [int(bin(a)[j]) for j in range(2, len(bin(a)))][::-1]

            N = len(exp_a) - 1

            # Marker marker_a_equal_zero
            out += Script.parse_string("OP_0")

            # Load the lambdas and the markers
            for j in range(len(lambdas) - 1, -1, -1):
                if exp_a[-j - 2] == 1:
                    out += nums_to_script(lambdas[j][1]) + Script.parse_string("OP_1")
                    out += nums_to_script(lambdas[j][0]) + Script.parse_string("OP_1")
                else:
                    out += Script.parse_string("OP_0")
                    out += nums_to_script(lambdas[j][0])
                    out += Script.parse_string("OP_1")
            out += Script.parse_string(" ".join(["OP_0"] * (M - N)))

        # Load P
        out += nums_to_script(P)

        return out
