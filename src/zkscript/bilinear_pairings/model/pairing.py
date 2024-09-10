# from src.tx_engine.engine.script import Script
from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script, pick, roll
from src.zkscript.util.utility_functions import optimise_script


class Pairing:
    def single_pairing(
        self, modulo_threshold: int, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Pairing computation.

        Input parameters:
            - Stack: q .. miller(P,Q)^-1 lambdas P Q
            - Altstack: []
        Output:
            - e(P,Q)
        Assuption on data:
            - P is a point on E(F_q)
            - Q is a point on E'(F_q^{k/d})
            - miller(P,Q) is the output of the miller loop computed on P,Q represented as an element in F_q^{k/d}
            - If P is the point at infinity, then it is encoded as 0x00 * N_POINTS_CURVE
            (NOT OP_0, data payloads of 0x00)
            - If Q is the point at infinity, then it is encoded as 0x00 * N_POINTS_TWIST
            (NOT OP_0, data payloads of 0x00)
        """
        q = self.MODULUS

        easy_exponentiation_with_inverse_check = self.easy_exponentiation_with_inverse_check
        hard_exponentiation = self.hard_exponentiation

        N_POINTS_CURVE = self.N_POINTS_CURVE
        N_POINTS_TWIST = self.N_POINTS_TWIST
        N_ELEMENTS_MILLER_OUTPUT = self.N_ELEMENTS_MILLER_OUTPUT

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([q])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # Check if Q is point at infinity, in this case, return identity
        if N_POINTS_TWIST == 4:
            out += Script.parse_string("OP_2OVER OP_2OVER")
        else:
            out += pick(position=N_POINTS_TWIST - 1, nElements=N_POINTS_TWIST)
        for i in range(N_POINTS_TWIST - 1):
            out += Script.parse_string("OP_CAT")
        out += Script.parse_string("0x" + "00" * N_POINTS_TWIST + " OP_EQUAL OP_NOT")
        out += Script.parse_string("OP_IF")

        # Otherwise, check if P is point at infinity, in this case, return identity
        out += pick(position=N_POINTS_TWIST + N_POINTS_CURVE - 1, nElements=N_POINTS_CURVE)  # Pick P
        for i in range(N_POINTS_CURVE - 1):
            out += Script.parse_string("OP_CAT")
        out += Script.parse_string("0x" + "00" * N_POINTS_CURVE + " OP_EQUAL OP_NOT")
        out += Script.parse_string("OP_IF")

        # Execute pairing computation ----------------------------------------------------------------------------------

        # After this, the stack is: miller(P,Q)^-1 (t-1)Q miller(P,Q)
        out += self.miller_loop(modulo_threshold=modulo_threshold, check_constant=False, clean_constant=False)

        # This is where one would perform subgroup membership checks if they were needed
        # For Groth16, they are not, so we simply drop uQ
        out += roll(position=N_ELEMENTS_MILLER_OUTPUT + N_POINTS_TWIST - 1, nElements=N_POINTS_TWIST)
        out += Script.parse_string(" ".join(["OP_DROP"] * N_POINTS_TWIST))

        out += easy_exponentiation_with_inverse_check(take_modulo=True, check_constant=False, clean_constant=False)
        out += hard_exponentiation(
            take_modulo=True, modulo_threshold=modulo_threshold, check_constant=False, clean_constant=clean_constant
        )

        # --------------------------------------------------------------------------------------------------------------

        # Come here if P is point at infinity
        out += Script.parse_string("OP_ELSE")
        for i in range((N_POINTS_TWIST + N_POINTS_CURVE) // 2):
            out += Script.parse_string("OP_2DROP")
        out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * (N_ELEMENTS_MILLER_OUTPUT - 1)))
        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")
        out += Script.parse_string("OP_ENDIF")

        # Come here if Q is point at infinity
        out += Script.parse_string("OP_ELSE")
        if N_POINTS_TWIST == 4:
            out += Script.parse_string("OP_2DROP OP_2DROP OP_2DROP")
        else:
            for i in range(N_POINTS_TWIST // 2):
                out += Script.parse_string("OP_2DROP")
        out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * (N_ELEMENTS_MILLER_OUTPUT - 1)))
        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")
        out += Script.parse_string("OP_ENDIF")

        return optimise_script(out)

    def triple_pairing(
        self, modulo_threshold: int, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Pairing computation.

        NOTE: At the moment, this function does not handle the case where one of the Pi's or one of the Qi's is the
        point at infinity

        Input parameters:
            - Stack: [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]^-1 lambdas P1 P2 P3 Q1 Q2 Q3
            - Altstack:
        Output:
            - e(P1,Q1) * e(P2,Q2) * e(P3,Q3)
        Assuption on data:
            - Pi are points on E(F_q)
            - Qi are points on E'(F_q)
            - [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)] is the product of the outputs of the miller loops computed
            on Pi,Qi
        """
        q = self.MODULUS

        easy_exponentiation_with_inverse_check = self.easy_exponentiation_with_inverse_check
        hard_exponentiation = self.hard_exponentiation

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([q])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # After this, the stack is:
        # quadratic([miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)])^-1
        # quadratic([miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)])
        out += self.triple_miller_loop(modulo_threshold=modulo_threshold, check_constant=False, clean_constant=False)

        out += easy_exponentiation_with_inverse_check(take_modulo=True, check_constant=False, clean_constant=False)
        out += hard_exponentiation(
            take_modulo=True, modulo_threshold=modulo_threshold, check_constant=False, clean_constant=clean_constant
        )

        return optimise_script(out)

    def single_pairing_input(
        self,
        P: list[int],
        Q: list[int],
        lambdas_Q_exp_miller_loop: list[list[list[int]]],
        miller_output_inverse: list[int],
        load_q=True,
    ) -> Script:
        """Return the script needed to execute the single_pairing function above.

        Take P, Q, and the curve as input

        If P is the point at infinity, then it should be passed as [None, None]
        If Q is the point at infinity, then it should be passed as [None, None]
        """
        q = self.MODULUS
        N_POINTS_CURVE = self.N_POINTS_CURVE
        N_POINTS_TWIST = self.N_POINTS_TWIST

        is_P_infinity = all([el == None for el in P])
        is_Q_infinity = all([el == None for el in Q])

        out = nums_to_script([q]) if load_q else Script()

        if is_P_infinity and not is_Q_infinity:
            out += Script.parse_string(" ".join(["0x00"] * N_POINTS_CURVE))
            out += nums_to_script(Q)
        elif not is_P_infinity and is_Q_infinity:
            out += nums_to_script(P)
            out += Script.parse_string(" ".join(["0x00"] * N_POINTS_TWIST))
        elif is_P_infinity and is_Q_infinity:
            out += Script.parse_string(" ".join(["0x00"] * (N_POINTS_TWIST + N_POINTS_CURVE)))
        else:
            # Load inverse of output of Miller loop
            out += nums_to_script(miller_output_inverse)

            # Load the lambdas
            for i in range(len(lambdas_Q_exp_miller_loop) - 1, -1, -1):
                for j in range(len(lambdas_Q_exp_miller_loop[i]) - 1, -1, -1):
                    out += nums_to_script(lambdas_Q_exp_miller_loop[i][j])

            # Load P and Q
            out += nums_to_script(P)
            out += nums_to_script(Q)

        return out

    def triple_pairing_input(
        self,
        P1: list[int],
        P2: list[int],
        P3: list[int],
        Q1: list[int],
        Q2: list[int],
        Q3: list[int],
        lambdas_Q1_exp_miller_loop: list[list[list[int]]],
        lambdas_Q2_exp_miller_loop: list[list[list[int]]],
        lambdas_Q3_exp_miller_loop: list[list[list[int]]],
        miller_output_inverse: list[int],
        load_q=True,
    ) -> Script:
        """Return the script needed to execute the triple_pairing function above.

        Take Pi, Qi, the lamdbas for computing (t-1)Qi, and the inverse of the miller loop as input.
        """
        q = self.MODULUS
        lambdas = [lambdas_Q1_exp_miller_loop, lambdas_Q2_exp_miller_loop, lambdas_Q3_exp_miller_loop]

        out = nums_to_script([q]) if load_q else Script()

        # Load z inverse
        out += nums_to_script(miller_output_inverse)

        # Load lambdas
        for i in range(len(lambdas[0]) - 1, -1, -1):
            for j in range(len(lambdas[0][i]) - 1, -1, -1):
                for k in range(3):
                    out += nums_to_script(lambdas[k][i][j])

        out += nums_to_script(P1)
        out += nums_to_script(P2)
        out += nums_to_script(P3)
        out += nums_to_script(Q1)
        out += nums_to_script(Q2)
        out += nums_to_script(Q3)

        return out
