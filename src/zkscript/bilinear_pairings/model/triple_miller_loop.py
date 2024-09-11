# Math
from math import ceil, log, log2

# from src.tx_engine.engine.script import Script
from tx_engine import Script

from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import nums_to_script, pick, roll


class TripleMillerLoop:
    def triple_miller_loop(
        self, modulo_threshold: int, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Evaluate the miller loop.

        Input parameters:
            - Stack: q .. lambdas P1 P2 P3 Q1 Q2 Q3
            - Altstack: []
        Output:
            - miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)
        Assumption on data:
            - Pi are passed as couples of integers (minimally encoded, in little endian)
            - Qi are passed as couples of elements in Fq2 (see Fq2.py)
            - miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3) is in Fq4
        """
        q = self.MODULUS
        exp_miller_loop = self.exp_miller_loop
        point_doubling_twisted_curve = self.point_doubling_twisted_curve
        point_addition_twisted_curve = self.point_addition_twisted_curve
        point_negation_twisted_curve = self.point_negation_twisted_curve
        line_eval = self.line_eval
        line_eval_times_eval = self.line_eval_times_eval
        line_eval_times_eval_times_eval = self.line_eval_times_eval_times_eval
        line_eval_times_eval_times_eval_times_eval = self.line_eval_times_eval_times_eval_times_eval
        line_eval_times_eval_times_eval_times_eval_times_eval_times_eval = (
            self.line_eval_times_eval_times_eval_times_eval_times_eval_times_eval
        )
        miller_loop_output_square = self.miller_loop_output_square
        miller_loop_output_times_eval_times_eval_times_eval = self.miller_loop_output_times_eval_times_eval_times_eval
        miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval = (
            self.miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval
        )

        EXTENSION_DEGREE = self.EXTENSION_DEGREE
        N_POINTS_CURVE = self.N_POINTS_CURVE
        N_POINTS_TWIST = self.N_POINTS_TWIST
        N_ELEMENTS_MILLER_OUTPUT = self.N_ELEMENTS_MILLER_OUTPUT
        N_ELEMENTS_EVALUATION_OUTPUT = self.N_ELEMENTS_EVALUATION_OUTPUT
        N_ELEMENTS_EVALUATION_TIMES_EVALUATION = self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION

        """
        At the beginning of every iteration of the loop the stack is assumed to be:
            lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i
        where:
            - lambda_(2*Tj) is the gradient of the line tangent at Tj.
            - f_i is the value of the i-th step in the computation of [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]
        If exp_miller_loop[i] != 0, then the stack is:
            lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1
            P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i
        where:
            - lambda_(2* Tj pm Qj) is the gradient of the line through 2 * Tj and (pm Qj)

        The computation at the i-th iteration of the loop is as follows:
            - if exp_miller_loop[i] == 0, then:
                - compute t_j = ev_l_(T_j,T,j)(P_j)
                - compute 2 * T_j
                - compute t_1 * t_2 * t_3
                - compute f_i * (t_1 * t_2 * t_3) to get f_(i+1)
            - exp_miller_loop[i] != 0, then:
                - compute t_j = ev_l_(T_j,T,j)(P_j)
                - compute 2 * T_j
                - compute (2 * T_j) pm Q_j
                - compute t'_j = ev_l_((2 * T_j),pm Q_j)(P_j)
                - compute t_1 * t_2
                - compute t_3 * t_1'
                - compute t'_2 * t_'3
                - compute (t_1 * t_2) * (t_3 * t_1') * (t'_2 * t_'3)
                - compute f_i * (t_1 * t_2) * (t_3 * t_1') * (t'_2 * t_'3) to get f_(i+1)

        Modulo operations are carried out as in a similar fashion to a single miller loop, with the only difference
        being that the update of f is now always of the form: f <-- f^2 * Dense
        """

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([q])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # After this, the stack is: xP1 yP1 xP2 yP2 xP3 yP3 xQ1 yQ1 xQ2 yQ2 xQ3 yQ3 xQ1 -yQ1 xQ2 -yQ2 xQ3 -yQ3
        set_Qs = pick(position=3 * N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)
        set_Qs += point_negation_twisted_curve(take_modulo=False, check_constant=False, clean_constant=False)
        set_Qs += pick(position=3 * N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)
        set_Qs += point_negation_twisted_curve(take_modulo=False, check_constant=False, clean_constant=False)
        set_Qs += pick(position=3 * N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)
        set_Qs += point_negation_twisted_curve(take_modulo=False, check_constant=False, clean_constant=False)

        # After this, the stack is: xP1 yP1 xP2 yP2 xP3 yP3 xQ1 yQ1 xQ2 yQ2 xQ3 yQ3 xQ1 -yQ1 xQ2 -yQ2 xQ3 -yQ3 xT1 yT1
        # xT2 yT2 xT3 yT3
        set_Ts = Script()
        if exp_miller_loop[-1] == 1:
            set_Ts += pick(position=6 * N_POINTS_TWIST - 1, n_elements=3 * N_POINTS_TWIST)  # Pick Q1, Q2, Q3
        elif exp_miller_loop[-1] == -1:
            set_Ts += pick(position=3 * N_POINTS_TWIST - 1, n_elements=3 * N_POINTS_TWIST)  # Pick -Q1, -Q2, -Q3
        else:
            raise ValueError("Last element of exp_miller_loop must be non-zero.")

        out += set_Qs + set_Ts

        clean_final = False
        BIT_SIZE_Q = ceil(log2(q))
        current_size_T = BIT_SIZE_Q
        current_size_F = BIT_SIZE_Q
        # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 uQ1 uQ2 uQ3 [miller(P1,Q1) * miller(P2,Q2) *
        # miller(P3,Q3)]
        for i in range(len(exp_miller_loop) - 2, -1, -1):
            take_modulo_F = False
            take_modulo_T = False

            # Constants set up
            if i == 0:
                clean_final = clean_constant
                take_modulo_F = True
                take_modulo_T = True
            else:
                # Next iteration will have: f <-- f^2 * Dense and T_i <-- 2T_i or T_i <-- 2T_i pm Q_i.
                multiplier = 3 if exp_miller_loop[i] == 0 else 6
                future_size_F = (
                    multiplier * log2(13 * 3) + multiplier * BIT_SIZE_Q + (ceil(log2(13 * 3)) + 2 * current_size_F)
                )
                if future_size_F > modulo_threshold:
                    take_modulo_F = True
                    current_size_F = BIT_SIZE_Q
                else:
                    current_size_F = future_size_F

                if current_size_T + BIT_SIZE_Q + log(6) > modulo_threshold:
                    take_modulo_T = True
                    current_size_T = BIT_SIZE_Q
                else:
                    current_size_T = current_size_T + BIT_SIZE_Q + log(6)

            if i == len(exp_miller_loop) - 2:
                # In this case, f is not there, so we need to take that into account
                if exp_miller_loop[i] == 0:
                    # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                    # T1 T2 T3 t_1
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 3 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T1)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += pick(
                        position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Pick T1
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += pick(
                        position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + STACK_LENGTH_ADDED - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P1
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t_1 = ev_(l_(T1,T1))(P_1)
                    # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                    # T1 T2 T3 t_1 t_2
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 2 * EXTENSION_DEGREE
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T2)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += pick(
                        position=2 * N_POINTS_TWIST + N_ELEMENTS_EVALUATION_OUTPUT + STACK_LENGTH_ADDED - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick T2
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 2 * N_POINTS_CURVE
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P2
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t_2 = ev_(l_(T2,T2))(P_2)
                    # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                    # T1 T2 T3 t_1 t_2 t_3
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + EXTENSION_DEGREE
                        + 2 * N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T3)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += pick(
                        position=N_POINTS_TWIST + 2 * N_ELEMENTS_EVALUATION_OUTPUT + STACK_LENGTH_ADDED - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick T3
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + N_POINTS_CURVE
                        + 2 * N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P3
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t_3 = ev_(l_(T3,T3))(P_3)
                    # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                    # T1 T2 T3 (t_1 * t_2 * t_3)
                    out += line_eval_times_eval(
                        take_modulo=False, check_constant=False, clean_constant=False
                    )  # Compute t2 * t3
                    out += line_eval_times_eval_times_eval(
                        take_modulo=False, check_constant=False, clean_constant=False
                    )  # Compute t1 * (t2 * t3)
                    # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                    # T1 T2 T3, altstack = [(t_1 * t_2 * t_3)]
                    out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                    # After this, the stack is: lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T2 T3 (2*T1),
                    # altstack = [(t_1 * t_2 * t_3)]
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 3 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2*T1)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += roll(
                        position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Roll T1
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )  # Compute 2*T1
                    # After this, the stack is: lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T3 (2*T1) (2*T2),
                    # altstack = [(t_1 * t_2 * t_3)]
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 2 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2*T2)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += roll(
                        position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Roll T2
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )  # Compute 2*T2
                    # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 (2*T1) (2*T2) (2*T3),
                    # altstack = [(t_1 * t_2 * t_3)]
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2*T3)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += roll(
                        position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Roll T3
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=clean_final
                    )  # Compute 2*T3
                    # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 (2*T1) (2*T2) (2*T3) (t_1 * t_2 * t_3)
                    out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                else:
                    # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3)
                    # lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 t_1
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 3 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T1)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += pick(
                        position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Pick T1
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += pick(
                        position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + STACK_LENGTH_ADDED - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P1
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t_1 = ev_(l_(T1,T1))(P_1)
                    # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3)
                    # lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 (t_1 * t_2)
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 2 * EXTENSION_DEGREE
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T2)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += pick(
                        position=2 * N_POINTS_TWIST + N_ELEMENTS_EVALUATION_OUTPUT + STACK_LENGTH_ADDED - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick T2
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 2 * N_POINTS_CURVE
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P2
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t_2 = ev_(l_(T2,T2))(P_2)
                    out += line_eval_times_eval(
                        take_modulo=False, check_constant=False, clean_constant=False
                    )  # Compute t1 * t2
                    # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3)
                    # lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 (t_1 * t_2) t_3
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + EXTENSION_DEGREE
                        + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T3)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += pick(
                        position=N_POINTS_TWIST + N_ELEMENTS_EVALUATION_TIMES_EVALUATION + STACK_LENGTH_ADDED - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick T3
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + N_POINTS_CURVE
                        + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P3
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t_3 = ev_(l_(T3,T3))(P_3)
                    # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3)
                    # lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3
                    # (t_1 * t_2) (t_3 * t'_1)
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + 6 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T1 pm Q)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    if exp_miller_loop[i] == 1:
                        out += pick(
                            position=9 * N_POINTS_TWIST
                            + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                            + N_ELEMENTS_EVALUATION_OUTPUT
                            + STACK_LENGTH_ADDED
                            - 1,
                            n_elements=N_POINTS_TWIST,
                        )  # Pick Q1
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    elif exp_miller_loop[i] == -1:
                        out += pick(
                            position=6 * N_POINTS_TWIST
                            + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                            + N_ELEMENTS_EVALUATION_OUTPUT
                            + STACK_LENGTH_ADDED
                            - 1,
                            n_elements=N_POINTS_TWIST,
                        )  # Pick -Q1
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    else:
                        raise ValueError
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P1
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t'_1 = ev_(l_(2*T1,pm Q1))(P_1)
                    out += line_eval_times_eval(
                        take_modulo=False, check_constant=False, clean_constant=False
                    )  # Compute t_3 * t'_1
                    # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3)
                    # lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3
                    # (t_1 * t_2) (t_3 * t'_1) t'_2
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + 5 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T2 pm Q)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    if exp_miller_loop[i] == 1:
                        out += pick(
                            position=8 * N_POINTS_TWIST
                            + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                            + STACK_LENGTH_ADDED
                            - 1,
                            n_elements=N_POINTS_TWIST,
                        )  # Pick Q2
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    elif exp_miller_loop[i] == -1:
                        out += pick(
                            position=5 * N_POINTS_TWIST
                            + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                            + STACK_LENGTH_ADDED
                            - 1,
                            n_elements=N_POINTS_TWIST,
                        )  # Pick -Q2
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    else:
                        raise ValueError
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 2 * N_POINTS_CURVE
                        + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P2
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t'_2 = ev_(l_(2*T2,pm Q2))(P_2)
                    # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3)
                    # lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3
                    # (t_1 * t_2) (t_3 * t'_1) (t'_2 * t'_3)
                    STACK_LENGTH_ADDED = 0
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + 4 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2*T3 pm Q)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    if exp_miller_loop[i] == 1:
                        out += pick(
                            position=7 * N_POINTS_TWIST
                            + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                            + N_ELEMENTS_EVALUATION_OUTPUT
                            + STACK_LENGTH_ADDED
                            - 1,
                            n_elements=N_POINTS_TWIST,
                        )  # Pick Q3
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    elif exp_miller_loop[i] == -1:
                        out += pick(
                            position=4 * N_POINTS_TWIST
                            + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                            + N_ELEMENTS_EVALUATION_OUTPUT
                            + STACK_LENGTH_ADDED
                            - 1,
                            n_elements=N_POINTS_TWIST,
                        )  # Pick -Q3
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    else:
                        raise ValueError
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + N_POINTS_CURVE
                        + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P3
                    STACK_LENGTH_ADDED += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )  # Compute t'_3 = ev_(l_(2*T3,pm Q3))(P_3)
                    out += line_eval_times_eval(
                        take_modulo=False, check_constant=False, clean_constant=False
                    )  # Compute t'_2 * t'_3
                    # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3)
                    # lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3
                    # [(t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                    # Compute (t_3 * t'_1) * (t'_2 * t'_3)
                    out += line_eval_times_eval_times_eval_times_eval(
                        take_modulo=False, check_constant=False, clean_constant=False
                    )
                    # Compute (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)
                    out += line_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
                        take_modulo=False, check_constant=False, clean_constant=False
                    )
                    # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3)
                    # lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3,
                    # altstack = [(t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                    out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                    # After this, the stack is: lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T2) lambda_(2*T3)
                    # P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T2 T3 (2*T1 pm Q1),
                    # altstack = [(t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 3 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2*T1)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += roll(
                        position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Roll T1
                    STACK_LENGTH_ADDED += 0
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )  # Compute 2 * T1
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 5 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2* T1 pm Q1)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    if EXTENSION_DEGREE == 2 and N_POINTS_TWIST == 4:
                        out += Script.parse_string("OP_2ROT OP_2ROT")  # Bring 2*T1 on top of the stack
                    else:
                        out += roll(
                            position=EXTENSION_DEGREE + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST
                        )  # Bring 2*T1 on top of the stack
                    if exp_miller_loop[i] == 1:
                        out += pick(
                            position=9 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                        )  # Pick Q1
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    elif exp_miller_loop[i] == -1:
                        out += pick(
                            position=6 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                        )  # Pick -Q1
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    else:
                        raise ValueError
                    out += point_addition_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )
                    # After this, the stack is: lambda_(2* T3 pm Q3) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T3
                    # (2*T1 pm Q1) (2*T2 pm Q2),
                    # altstack = [(t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 2 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2*T2)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += roll(
                        position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Roll T2
                    STACK_LENGTH_ADDED += 0
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )  # Compute 2 * T2
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST
                        + 3 * N_POINTS_CURVE
                        + 3 * EXTENSION_DEGREE
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2* T2 pm Q2)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    if EXTENSION_DEGREE == 2 and N_POINTS_TWIST == 4:
                        out += Script.parse_string("OP_2ROT OP_2ROT")  # Bring 2*T2 on top of the stack
                    else:
                        out += roll(
                            position=EXTENSION_DEGREE + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST
                        )  # Bring 2*T2 on top of the stack
                    if exp_miller_loop[i] == 1:
                        out += pick(
                            position=8 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                        )  # Pick Q2
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    elif exp_miller_loop[i] == -1:
                        out += pick(
                            position=5 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                        )  # Pick -Q2
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    else:
                        raise ValueError
                    out += point_addition_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )
                    # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 (2*T1 pm Q1) (2*T2 pm Q2) (2*T3 pm Q3),
                    # altstack = [(t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2*T3)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    out += roll(
                        position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Roll T3
                    STACK_LENGTH_ADDED += 0
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )  # Compute 2 * T3
                    STACK_LENGTH_ADDED = 0
                    out += roll(
                        position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2* T3 pm Q3)
                    STACK_LENGTH_ADDED += EXTENSION_DEGREE
                    if EXTENSION_DEGREE == 2 and N_POINTS_TWIST == 4:
                        out += Script.parse_string("OP_2ROT OP_2ROT")  # Bring 2*T3 on top of the stack
                    else:
                        out += roll(
                            position=EXTENSION_DEGREE + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST
                        )  # Bring 2*T3 on top of the stack
                    if exp_miller_loop[i] == 1:
                        out += pick(
                            position=7 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                        )  # Pick Q3
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    elif exp_miller_loop[i] == -1:
                        out += pick(
                            position=4 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                        )  # Pick -Q3
                        STACK_LENGTH_ADDED += N_POINTS_TWIST
                    else:
                        raise ValueError
                    out += point_addition_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )
                    # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T2 T3
                    # (2*T1 pm Q1) (2*T2 pm Q2) (2*T3 pm Q3) [(t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                    out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
            elif exp_miller_loop[i] == 0:
                # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1
                # T2 T3 f_i^2
                STACK_LENGTH_ADDED = 0
                out += miller_loop_output_square(take_modulo=False, check_constant=False, clean_constant=False)
                # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1
                # T2 T3 f_i^2 t_1
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + 3 * EXTENSION_DEGREE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T1)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += pick(
                    position=3 * N_POINTS_TWIST + N_ELEMENTS_MILLER_OUTPUT + STACK_LENGTH_ADDED - 1,
                    n_elements=N_POINTS_TWIST,
                )  # Pick T1
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P1
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t_1 = ev_(l_(T1,T1))(P_1)
                # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                # T1 T2 T3 f_i^2 t_1 t_2
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + 2 * EXTENSION_DEGREE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T2)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += pick(
                    position=2 * N_POINTS_TWIST
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_TWIST,
                )  # Pick T2
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 2 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P2
                STACK_LENGTH_ADDED += N_POINTS_CURVE
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t_2 = ev_(l_(T2,T2))(P_2)
                # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                # T1 T2 T3 f_i^2 t_1 t_2 t_3
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + EXTENSION_DEGREE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + 2 * N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T3)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += pick(
                    position=N_POINTS_TWIST
                    + N_ELEMENTS_MILLER_OUTPUT
                    + 2 * N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_TWIST,
                )  # Pick T3
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + 2 * N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P3
                STACK_LENGTH_ADDED += N_POINTS_CURVE
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t_3 = ev_(l_(T3,T3))(P_3)
                # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                # T1 T2 T3 (f_i^2 * t_1 * t_2 * t_3)
                out += line_eval_times_eval(
                    take_modulo=False, check_constant=False, clean_constant=False
                )  # Compute t2 * t3
                out += line_eval_times_eval_times_eval(
                    take_modulo=False, check_constant=False, clean_constant=False
                )  # Compute t1 * (t2 * t3)
                # Compute f_i * (t1 * t2 * t3)
                out += miller_loop_output_times_eval_times_eval_times_eval(
                    take_modulo=take_modulo_F, check_constant=False, clean_constant=False, is_constant_reused=False
                )
                # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                # T1 T2 T3, altstack = [(f_i^2 * t_1 * t_2 * t_3)]
                out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                # After this, the stack is: lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T2 T3 (2*T1),
                # altstack = [(f_i^2 * t_1 * t_2 * t_3)]
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + 3 * EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2*T1)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += roll(position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST)  # Roll T1
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += point_doubling_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                )  # Compute 2*T1
                # After this, the stack is: lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T3 (2*T1) (2*T2),
                # altstack = [(f_i^2 * t_1 * t_2 * t_3)]
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + 2 * EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2*T2)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += roll(position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST)  # Roll T2
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += point_doubling_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                )  # Compute 2*T2
                # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 (2*T1) (2*T2) (2*T3),
                # altstack = [(f_i^2 * t_1 * t_2 * t_3)]
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2*T3)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += roll(position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST)  # Roll T3
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += point_doubling_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=clean_final
                )  # Compute 2*T3
                # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 (2*T1) (2*T2) (2*T3) (f_i^2 * t_1 * t_2 * t_3)
                out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
            else:
                # After this, the stack is: lambda_(2*T1) lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3
                # T1 T2 T3 f_i^2
                out += miller_loop_output_square(take_modulo=False, check_constant=False, clean_constant=False)
                # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1)
                # lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i^2 t_1
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + 3 * EXTENSION_DEGREE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T1)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += pick(
                    position=3 * N_POINTS_TWIST + N_ELEMENTS_MILLER_OUTPUT + STACK_LENGTH_ADDED - 1,
                    n_elements=N_POINTS_TWIST,
                )  # Pick T1
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P1
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t_1 = ev_(l_(T1,T1))(P_1)
                # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1)
                # lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i^2 (t_1 * t_2)
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + 2 * EXTENSION_DEGREE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T2)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += pick(
                    position=2 * N_POINTS_TWIST
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_TWIST,
                )  # Pick T2
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 2 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P2
                STACK_LENGTH_ADDED += N_POINTS_CURVE
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t_2 = ev_(l_(T2,T2))(P_2)
                out += line_eval_times_eval(
                    take_modulo=False, check_constant=False, clean_constant=False
                )  # Compute t1 * t2
                # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1)
                # lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i^2 (t_1 * t_2) t_3
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + EXTENSION_DEGREE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T3)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += pick(
                    position=N_POINTS_TWIST
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_TWIST,
                )  # Pick T3
                STACK_LENGTH_ADDED += N_POINTS_TWIST
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P3
                STACK_LENGTH_ADDED += N_POINTS_CURVE
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t_3 = ev_(l_(T3,T3))(P_3)
                # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1)
                # lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i^2 (t_1 * t_2) (t_3 * t'_1)
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + 6 * EXTENSION_DEGREE
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T1 pm Q)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                if exp_miller_loop[i] == 1:
                    out += pick(
                        position=9 * N_POINTS_TWIST
                        + N_ELEMENTS_MILLER_OUTPUT
                        + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick Q1
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                elif exp_miller_loop[i] == -1:
                    out += pick(
                        position=6 * N_POINTS_TWIST
                        + N_ELEMENTS_MILLER_OUTPUT
                        + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick -Q1
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                else:
                    raise ValueError
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P1
                STACK_LENGTH_ADDED += N_POINTS_CURVE
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t'_1 = ev_(l_(2*T1,pm Q1))(P_1)
                out += line_eval_times_eval(
                    take_modulo=False, check_constant=False, clean_constant=False
                )  # Compute t_3 * t'_1
                # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1)
                # lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i^2 (t_1 * t_2) (t_3 * t'_1) t'_2
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + 5 * EXTENSION_DEGREE
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T2 pm Q)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                if exp_miller_loop[i] == 1:
                    out += pick(
                        position=8 * N_POINTS_TWIST
                        + N_ELEMENTS_MILLER_OUTPUT
                        + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick Q2
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                elif exp_miller_loop[i] == -1:
                    out += pick(
                        position=5 * N_POINTS_TWIST
                        + N_ELEMENTS_MILLER_OUTPUT
                        + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick -Q2
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                else:
                    raise ValueError
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 2 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P2
                STACK_LENGTH_ADDED += N_POINTS_CURVE
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t'_2 = ev_(l_(2*T2,pm Q2))(P_2)
                # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1)
                # lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i^2
                # (t_1 * t_2) (t_3 * t'_1) (t'_2 * t'_3)
                STACK_LENGTH_ADDED = 0
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + 3 * N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + 4 * EXTENSION_DEGREE
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Pick lambda_(2*T3 pm Q)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                if exp_miller_loop[i] == 1:
                    out += pick(
                        position=7 * N_POINTS_TWIST
                        + N_ELEMENTS_MILLER_OUTPUT
                        + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick Q3
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                elif exp_miller_loop[i] == -1:
                    out += pick(
                        position=4 * N_POINTS_TWIST
                        + N_ELEMENTS_MILLER_OUTPUT
                        + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                        + N_ELEMENTS_EVALUATION_OUTPUT
                        + STACK_LENGTH_ADDED
                        - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick -Q3
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                else:
                    raise ValueError
                out += pick(
                    position=9 * N_POINTS_TWIST
                    + N_POINTS_CURVE
                    + N_ELEMENTS_MILLER_OUTPUT
                    + 2 * N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    + N_ELEMENTS_EVALUATION_OUTPUT
                    + STACK_LENGTH_ADDED
                    - 1,
                    n_elements=N_POINTS_CURVE,
                )  # Pick P3
                STACK_LENGTH_ADDED += N_POINTS_CURVE
                out += line_eval(
                    take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute t'_3 = ev_(l_(2*T3,pm Q3))(P_3)
                out += line_eval_times_eval(
                    take_modulo=False, check_constant=False, clean_constant=False
                )  # Compute t'_2 * t'_3
                # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1)
                # lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3
                # [f_i^2 * (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                # Compute (t_3 * t'_1) * (t'_2 * t'_3)
                out += line_eval_times_eval_times_eval_times_eval(
                    take_modulo=False, check_constant=False, clean_constant=False
                )
                # Compute (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)
                out += line_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
                    take_modulo=False, check_constant=False, clean_constant=False
                )
                out += miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
                    take_modulo=take_modulo_F, check_constant=False, clean_constant=False, is_constant_reused=False
                )  # Compute [f_i * (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                # After this, the stack is: lambda_(2* T1 pm Q1) lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T1)
                # lambda_(2*T2) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3,
                # altstack = [f_i^2 * (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                # After this, the stack is: lambda_(2* T2 pm Q2) lambda_(2* T3 pm Q3) lambda_(2*T2) lambda_(2*T3)
                # P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T2 T3 (2*T1 pm Q1),
                # altstack = [f_i^2 * (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + 3 * EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2*T1)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += roll(position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST)  # Roll T1
                STACK_LENGTH_ADDED += 0
                out += point_doubling_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                )  # Compute 2 * T1
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + 5 * EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2* T1 pm Q1)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                if EXTENSION_DEGREE == 2 and N_POINTS_TWIST == 4:
                    out += Script.parse_string("OP_2ROT OP_2ROT")  # Bring 2*T1 on top of the stack
                else:
                    out += roll(
                        position=EXTENSION_DEGREE + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST
                    )  # Bring 2*T1 on top of the stack
                if exp_miller_loop[i] == 1:
                    out += pick(
                        position=9 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Pick Q1
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                elif exp_miller_loop[i] == -1:
                    out += pick(
                        position=6 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Pick -Q1
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                else:
                    raise ValueError
                out += point_addition_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                )
                # After this, the stack is: lambda_(2* T3 pm Q3) lambda_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T3
                # (2*T1 pm Q1) (2*T2 pm Q2),
                # altstack = [f_i^2 * (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + 2 * EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2*T2)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += roll(position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST)  # Roll T2
                STACK_LENGTH_ADDED += 0
                out += point_doubling_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                )  # Compute 2 * T2
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + 3 * EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2* T2 pm Q2)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                if EXTENSION_DEGREE == 2 and N_POINTS_TWIST == 4:
                    out += Script.parse_string("OP_2ROT OP_2ROT")  # Bring 2*T2 on top of the stack
                else:
                    out += roll(
                        position=EXTENSION_DEGREE + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST
                    )  # Bring 2*T2 on top of the stack
                if exp_miller_loop[i] == 1:
                    out += pick(
                        position=8 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Pick Q2
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                elif exp_miller_loop[i] == -1:
                    out += pick(
                        position=5 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Pick -Q2
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                else:
                    raise ValueError
                out += point_addition_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                )
                # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 (2*T1 pm Q1) (2*T2 pm Q2) (2*T3 pm Q3),
                # altstack = [f_i^2 * (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2*T3)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                out += roll(position=3 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST)  # Roll T3
                STACK_LENGTH_ADDED += 0
                out += point_doubling_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                )  # Compute 2 * T3
                STACK_LENGTH_ADDED = 0
                out += roll(
                    position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + EXTENSION_DEGREE + STACK_LENGTH_ADDED - 1,
                    n_elements=EXTENSION_DEGREE,
                )  # Roll lambda_(2* T3 pm Q3)
                STACK_LENGTH_ADDED += EXTENSION_DEGREE
                if EXTENSION_DEGREE == 2 and N_POINTS_TWIST == 4:
                    out += Script.parse_string("OP_2ROT OP_2ROT")  # Bring 2*T3 on top of the stack
                else:
                    out += roll(
                        position=EXTENSION_DEGREE + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST
                    )  # Bring 2*T3 on top of the stack
                if exp_miller_loop[i] == 1:
                    out += pick(
                        position=7 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Pick Q3
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                elif exp_miller_loop[i] == -1:
                    out += pick(
                        position=4 * N_POINTS_TWIST + STACK_LENGTH_ADDED - 1, n_elements=N_POINTS_TWIST
                    )  # Pick -Q3
                    STACK_LENGTH_ADDED += N_POINTS_TWIST
                else:
                    raise ValueError
                out += point_addition_twisted_curve(
                    take_modulo=take_modulo_T, check_constant=False, clean_constant=clean_final
                )
                # After this, the stack is: P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T2 T3 (2*T1 pm Q1) (2*T2 pm Q2) (2*T3 pm Q3)
                # [f_i^2 * (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                # Roll [f_i^2 * (t_1 * t_2) * (t_3 * t'_1) * (t'_2 * t'_3)]
                out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))

        # After this, the stack is: [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]
        out += roll(
            position=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE + N_ELEMENTS_MILLER_OUTPUT - 1,
            n_elements=9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE,
        )
        out += Script.parse_string(" ".join(["OP_DROP"] * (9 * N_POINTS_TWIST + 3 * N_POINTS_CURVE)))
        # ----------------------------------------------

        return optimise_script(out)

    def triple_miller_loop_input(
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
    ) -> Script:
        """Return the script needed to execute the triple_miller_loop function above.

        Take Pi, Qi, and the lamdbas for computing (t-1)Qi as input
        """
        q = self.MODULUS
        lambdas = [lambdas_Q1_exp_miller_loop, lambdas_Q2_exp_miller_loop, lambdas_Q3_exp_miller_loop]

        out = nums_to_script([q])
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
