"""miller_loop module.

This module enables constructing Bitcoin scripts that compute the Miller loop.
"""
from math import ceil, log2

from tx_engine import Script

from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import nums_to_script, pick, roll, verify_bottom_constant


class MillerLoop:
    """Miller loop operation."""
    def miller_loop(
        self, modulo_threshold: int, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Evaluation of the Miller loop at points `P` and `Q`.

        Stack input:
            - stack:    [q, ..., lambdas, P, Q], `P` is a point on E(F_q), `Q` is a point on E'(F_q^{k/d}), `lambdas` is
                the sequence of gradients to compute the miller loop
            - altstack: []

        Stack output:
            - stack:    [q, ..., (t-1)Q, miller(P,Q)], `miller(P,Q)` is in F_q^k
            - altstack: []

        Args:
            modulo_threshold (int): The threshold after which we reduce the result with the modulo. Given as ??? length.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to evaluate the Miller loop at points `P` and `Q`.

        Preconditions:
            `P` and `Q` are not the point at infinity.

        Notes:
            Modulo operations to save space: notice that point calculations (doubling and addition) and updates of f
            (the return value of the Miller loop) come into contact when we compute line evaluations. Hence,
            we work as follows:
                - Carry out point evaluations
                - Carry out updates of f
                - Always mod out line evaluations
                - Mod out point evaluation if next line evaluation overflows
                - Mod out f if next multiplication with a line evaluation overflows
            To estimate the size increases, we use:
                - log2(f^2) <= log2(13*3) + 2*sizeF
                - log2(f * lineEvaluation) <= log2(13*3) + sizeF + log2(q)
                - log2(f * lineEvaluation * lineEvaluation) <= 2*log2(13*3) + sizeF + 2*log2(q)
                - P + Q has its worst computation at lambda verification:
                log2(lambda * (xP - xQ)) <= log2(q) + log2(2) + log2(max(xP,xQ)) (lambda is always assumed to be in Fq)
                - P + Q has its worst coordinate at y:
                log2(-y_P + (x_(P+Q) - x_P) * lambda) <= log2(max(2yP, 2 * lambda * x_(P+Q))
                    <= log2(max(2yP,4*x_(P+Q)))
                    <= log2(2*lambda*x_(P+Q))
                    <= log2(6) + log2(q) + log2(max(xP,xQ)),
                where we used x_(P+Q) = lambda^2 - xP - xQ,
                and log2(lambda^2 - xP - xQ) <= log2(3*max(xP,xQ)) <= log2(3) + log2(max(xP,xQ)) (lambda is always
                assumed to be in Fq)
        """
        q = self.MODULUS
        exp_miller_loop = self.exp_miller_loop
        point_doubling_twisted_curve = self.point_doubling_twisted_curve
        point_addition_twisted_curve = self.point_addition_twisted_curve
        point_negation_twisted_curve = self.point_negation_twisted_curve
        line_eval = self.line_eval
        line_eval_times_eval = self.line_eval_times_eval
        line_eval_times_eval_times_eval_times_eval = self.line_eval_times_eval_times_eval_times_eval
        line_eval_times_eval_times_miller_loop_output = self.line_eval_times_eval_times_miller_loop_output
        miller_loop_output_square = self.miller_loop_output_square
        miller_loop_output_times_eval = self.miller_loop_output_times_eval
        pad_eval_times_eval_to_miller_output = self.pad_eval_times_eval_to_miller_output
        pad_eval_times_eval_times_eval_times_eval_to_miller_output = (
            self.pad_eval_times_eval_times_eval_times_eval_to_miller_output
        )

        EXTENSION_DEGREE = self.EXTENSION_DEGREE
        N_POINTS_CURVE = self.N_POINTS_CURVE
        N_POINTS_TWIST = self.N_POINTS_TWIST
        N_ELEMENTS_MILLER_OUTPUT = self.N_ELEMENTS_MILLER_OUTPUT
        N_ELEMENTS_EVALUATION_OUTPUT = self.N_ELEMENTS_EVALUATION_OUTPUT
        N_ELEMENTS_EVALUATION_TIMES_EVALUATION = self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION

        """
        At the beginning of every iteration of the loop the stack is assumed to be: lambda_(2T) P Q -Q T f_i
        where f_i is the value of the Miller loop after the i-th iteration and lambda_2T is the gradient of the line
        tangent at T.
        If exp_miller_loop[i-1] != 0, then the stack is: lambda_(2T pm Q) lambda_(2T) P Q T f_i, where lambda_(2T pm Q)
        is the gradient of the line through 2T and pm Q.
        """

        out = verify_bottom_constant(q) if check_constant else Script()

        # After this, the stack is: xP yP xQ yQ xQ -yQ xT yT
        set_T = Script()
        set_T += pick(position=N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)
        set_T += point_negation_twisted_curve(take_modulo=False, check_constant=False, clean_constant=False)
        if exp_miller_loop[-1] == 1:
            set_T += pick(position=2 * N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)  # Pick Q
        elif exp_miller_loop[-1] == -1:
            set_T += pick(position=N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)  # Pick -Q
        else:
            raise ValueError("Last element of exp_miller_loop must be non-zero.")
        out += set_T

        clean_final = False
        BIT_SIZE_Q = ceil(log2(q))
        current_size_T = BIT_SIZE_Q
        current_size_F = BIT_SIZE_Q
        # After this, the stack is: P Q -Q (t-1)Q miller(P,Q)
        for i in range(len(exp_miller_loop) - 2, -1, -1):
            take_modulo_F = False
            take_modulo_T = False

            # Constants set up
            if i == 0:
                clean_final = clean_constant
                take_modulo_F = True
                take_modulo_T = True
            elif exp_miller_loop[i - 1] == 0:
                # In this case, the next iteration will have: f <-- f^2 * lineEvaluation and T <-- 2T.
                future_size_F = log2(13 * 3) + 2 * current_size_F + log2(13 * 3) + BIT_SIZE_Q
                if future_size_F > modulo_threshold:
                    take_modulo_F = True
                    current_size_F = BIT_SIZE_Q
                else:
                    current_size_F = future_size_F

                if current_size_T + BIT_SIZE_Q + log2(6) > modulo_threshold:
                    take_modulo_T = True
                    current_size_T = BIT_SIZE_Q
                else:
                    current_size_T = current_size_T + BIT_SIZE_Q + log2(6)
            else:
                # In this case, the next iteration will have:
                # f <-- f^2 * lineEvaluation * lineEvaluation and T <-- 2T \pm Q.
                future_size_F = log2(13 * 3) + 2 * current_size_F + 2 * log2(13 * 3) + 2 * BIT_SIZE_Q
                if future_size_F > modulo_threshold:
                    take_modulo_F = True
                    current_size_F = BIT_SIZE_Q
                else:
                    current_size_F = future_size_F

                if current_size_T + BIT_SIZE_Q + log2(6) > modulo_threshold:
                    take_modulo_T = True
                    current_size_T = BIT_SIZE_Q
                else:
                    current_size_T = current_size_T + BIT_SIZE_Q + log2(6)

            if i == len(exp_miller_loop) - 2:
                # First iteration, f_i is not there yet, so that stack is: lambda_(2T) P Q -Q T
                if exp_miller_loop[i] == 0:
                    # After this, the stack is: lambda_(2T) P Q -Q T 2T
                    stack_length_added = 0
                    out += pick(
                        position=(3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE) + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_2T
                    stack_length_added += EXTENSION_DEGREE
                    out += pick(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Pick T
                    stack_length_added += N_POINTS_TWIST
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_F, check_constant=False, clean_constant=False
                    )  # Compute 2T
                    stack_length_added = N_POINTS_TWIST
                    # After this, the stack is: P Q -Q 2T lambda_2T T P
                    out += roll(
                        position=(3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE) + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_2T
                    stack_length_added += EXTENSION_DEGREE
                    out += roll(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Roll T
                    stack_length_added += 0
                    out += pick(
                        position=(3 * N_POINTS_TWIST + N_POINTS_CURVE) + stack_length_added - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P
                    stack_length_added += N_POINTS_CURVE
                    # After this, the stack is P Q -Q 2T ev_(l_(T,T))(P)
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    stack_length_added = N_ELEMENTS_EVALUATION_OUTPUT
                    # After this, the stack is: P Q -Q 2T ev_(l_(T,T))(P)^2
                    out += pick(
                        position=N_ELEMENTS_EVALUATION_OUTPUT - 1, n_elements=N_ELEMENTS_EVALUATION_OUTPUT
                    )  # Duplicate ev_(l_(T,T))(P)
                    out += line_eval_times_eval(
                        take_modulo=take_modulo_F, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    # After this, the stack is: P Q -Q 2T Dense(ev_(l_(T,T))(P)^2)
                    out += pad_eval_times_eval_to_miller_output
                else:
                    # After this, the stack is: lambda_(2T pm Q) lambda_(2T) P Q -Q T 2T
                    stack_length_added = 0
                    out += pick(
                        position=(3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE) + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_2T
                    stack_length_added += EXTENSION_DEGREE
                    out += pick(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Pick T
                    stack_length_added += N_POINTS_TWIST
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_F, check_constant=False, clean_constant=False
                    )  # Compute 2T
                    stack_length_added = N_POINTS_TWIST
                    # After this, the stack is: lambda_(2T pm Q) P Q -Q 2T lambda_2T T P
                    out += roll(
                        position=(3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE) + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_2T
                    stack_length_added += EXTENSION_DEGREE
                    out += roll(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Roll T
                    stack_length_added += 0
                    out += pick(
                        position=(3 * N_POINTS_TWIST + N_POINTS_CURVE) + stack_length_added - 1,
                        n_elements=N_POINTS_CURVE,
                    )  # Pick P
                    stack_length_added = N_POINTS_TWIST + EXTENSION_DEGREE + N_POINTS_CURVE
                    # After this, the stack is lambda_(2T pm Q) P Q -Q 2T ev_(l_(T,T))(P)
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    stack_length_added = N_ELEMENTS_EVALUATION_OUTPUT
                    # After this, the stack is: lambda_(2T pm Q) P Q -Q 2T, altstack = [ev_(l_(T,T))(P)]
                    out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_EVALUATION_OUTPUT))
                    stack_length_added = 0
                    # After this, the stack is: lambda_(2T pm Q) P Q -Q 2T (2T \pm Q), altstack = [ev_(l_(T,T))(P)]
                    out += pick(
                        position=(3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE) + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2T pm Q)
                    stack_length_added += EXTENSION_DEGREE
                    out += pick(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Pick 2T
                    stack_length_added += N_POINTS_TWIST
                    if exp_miller_loop[i] == 1:
                        out += pick(
                            position=3 * N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST
                        )  # Pick Q
                        stack_length_added += N_POINTS_TWIST
                    else:
                        out += pick(2 * N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Pick -Q
                        stack_length_added += N_POINTS_TWIST
                    out += point_addition_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )
                    stack_length_added = N_POINTS_TWIST
                    # After this, the stack is: P Q -Q (2T \pm Q) ev_(l_(2T,\pm Q))(P), altstack = [ev_(l_(T,T))(P)]
                    out += roll(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2T pm Q)
                    stack_length_added += EXTENSION_DEGREE
                    out += roll(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Roll 2T
                    stack_length_added += 0
                    out += pick(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + stack_length_added - 1, n_elements=N_POINTS_CURVE
                    )  # Pick P
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    stack_length_added = N_ELEMENTS_EVALUATION_OUTPUT
                    # After this, the stack is: P Q -Q (2T \pm Q) [ev_(l_(2T,\pm Q))(P) * ev_(l_(T,T))(P)]
                    out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_EVALUATION_OUTPUT))
                    out += line_eval_times_eval(take_modulo=False, check_constant=False, clean_constant=False)
                    stack_length_added = N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                    # After this, the stack is: P Q -Q (2T \pm Q) [ev_(l_(2T,\pm Q))(P) * ev_(l_(T,T))(P)]^2
                    # Duplicate ev_(l_(2T,\pm Q))(P) * ev_(l_(T,T))(P)
                    out += pick(
                        position=N_ELEMENTS_EVALUATION_TIMES_EVALUATION - 1,
                        n_elements=N_ELEMENTS_EVALUATION_TIMES_EVALUATION,
                    )
                    out += line_eval_times_eval_times_eval_times_eval(
                        take_modulo=take_modulo_F, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    # After this, the stack is: P Q -Q (2T \pm Q) Dense([ev_(l_(2T,\pm Q))(P) * ev_(l_(T,T))(P)]^2)
                    out += pad_eval_times_eval_times_eval_times_eval_to_miller_output
            else:
                # Only needed in this case, otherwise the squaring has already been computed
                if i != len(exp_miller_loop) - 3:
                    # After this, the stack is: lambda_(2T) P Q -Q T f_i^2
                    out += miller_loop_output_square(take_modulo=False, check_constant=False, clean_constant=False)
                if exp_miller_loop[i] == 0:
                    # After this, the stack is: lambda_(2T) P Q -Q T f_i^2 ev_(l_(T,T))(P)
                    stack_length_added = 0
                    out += pick(
                        position=N_ELEMENTS_MILLER_OUTPUT + N_POINTS_TWIST + stack_length_added - 1,
                        n_elements=N_POINTS_TWIST,
                    )  # Pick T
                    stack_length_added += N_POINTS_TWIST
                    out += pick(
                        position=N_ELEMENTS_MILLER_OUTPUT
                        + 3 * N_POINTS_TWIST
                        + N_POINTS_CURVE
                        + EXTENSION_DEGREE
                        + stack_length_added
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_2T
                    stack_length_added += EXTENSION_DEGREE
                    out += roll(position=N_POINTS_TWIST + EXTENSION_DEGREE - 1, n_elements=N_POINTS_TWIST)  # Roll T
                    out += pick(
                        position=N_ELEMENTS_MILLER_OUTPUT
                        + 3 * N_POINTS_TWIST
                        + N_POINTS_CURVE
                        + stack_length_added
                        - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick P
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    stack_length_added = N_ELEMENTS_EVALUATION_OUTPUT
                    # After this, the stack is: lambda_(2T) P Q -Q T, altstack = [f_i^2 * ev_(l_(T,T))(P)]
                    out += miller_loop_output_times_eval(
                        take_modulo=take_modulo_F, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                    stack_length_added = 0
                    # After this, the stack is: P Q -Q 2T, altstack = [f_i^2 * ev_(l_(T,T))(P)]
                    out += roll(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_2T
                    stack_length_added += EXTENSION_DEGREE
                    out += roll(position=N_POINTS_TWIST + EXTENSION_DEGREE - 1, n_elements=N_POINTS_TWIST)  # Roll T
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=clean_final
                    )
                    stack_length_added = 0
                    # After this, the stack is: P Q -Q 2T, f_i^2 * ev_(l_(T,T))(P)
                    out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                    stack_length_added = N_ELEMENTS_MILLER_OUTPUT
                else:
                    # After this, the stack is: lambda_(2T \pm Q) lambda_(2T) P Q -Q T, altstack = [f_i^2]
                    stack_length_added = 0
                    out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                    # After this, the stack is: lambda_(2T \pm Q) lambda_(2T) P Q -Q T 2T, altstack = [f_i^2]
                    out += pick(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_2T
                    stack_length_added += EXTENSION_DEGREE
                    out += pick(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Pick T
                    stack_length_added += N_POINTS_TWIST
                    out += point_doubling_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )
                    stack_length_added = N_POINTS_TWIST
                    # After this, the stack is: lambda_(2T \pm Q) lambda_(2T) P Q -Q T 2T (2T \pm Q), altstack = [f_i^2]
                    out += pick(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + 2 * EXTENSION_DEGREE + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Pick lambda_(2T pm Q)
                    stack_length_added += EXTENSION_DEGREE
                    out += pick(position=EXTENSION_DEGREE + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)  # Pick 2T
                    stack_length_added += N_POINTS_TWIST
                    if exp_miller_loop[i] == 1:
                        out += pick(
                            position=3 * N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST
                        )  # Pick Q
                    else:
                        out += pick(
                            position=2 * N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST
                        )  # Pick -Q
                    out += point_addition_twisted_curve(
                        take_modulo=take_modulo_T, check_constant=False, clean_constant=False
                    )
                    stack_length_added = 2 * N_POINTS_TWIST
                    # After this, the stack is: lambda_(2T \pm Q) P Q -Q 2T (2T \pm Q) ev_(l_(T,T))(P),
                    # altstack = [f_i^2]
                    out += roll(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_2T
                    stack_length_added += EXTENSION_DEGREE
                    out += roll(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Roll T
                    stack_length_added += 0
                    out += pick(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + stack_length_added - 1, n_elements=N_POINTS_CURVE
                    )  # Pick P
                    stack_length_added += N_POINTS_CURVE
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    stack_length_added = N_ELEMENTS_EVALUATION_OUTPUT + N_POINTS_TWIST
                    # After this, the stack is: P Q -Q (2T \pm Q) ev_(l_(T,T))(P) ev_(l_(2T,\pm Q))(P),
                    # altstack = [f_i^2]
                    out += roll(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + EXTENSION_DEGREE + stack_length_added - 1,
                        n_elements=EXTENSION_DEGREE,
                    )  # Roll lambda_(2T pm Q)
                    stack_length_added += EXTENSION_DEGREE
                    out += roll(position=N_POINTS_TWIST + stack_length_added - 1, n_elements=N_POINTS_TWIST)  # Roll 2T
                    stack_length_added += 0
                    out += pick(
                        position=3 * N_POINTS_TWIST + N_POINTS_CURVE + stack_length_added - 1, n_elements=N_POINTS_CURVE
                    )  # Pick P
                    out += line_eval(
                        take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
                    )
                    stack_length_added = 2 * N_ELEMENTS_EVALUATION_OUTPUT
                    # After this, the stack is: P Q -Q (2T \pm Q) [ev_(l_(T,T))(P) * ev_(l_(2T,\pm Q))(P) * f_i^2]
                    out += line_eval_times_eval(take_modulo=False, check_constant=False, clean_constant=False)
                    out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT))
                    out += line_eval_times_eval_times_miller_loop_output(
                        take_modulo=take_modulo_F,
                        check_constant=False,
                        clean_constant=clean_final,
                        is_constant_reused=False,
                    )

        # After this, the stack is: (t-1)Q miller(P,Q)
        out += roll(
            position=N_ELEMENTS_MILLER_OUTPUT + 3 * N_POINTS_TWIST + N_POINTS_CURVE - 1,
            n_elements=2 * N_POINTS_TWIST + N_POINTS_CURVE,
        )
        out += Script.parse_string(" ".join(["OP_DROP"] * (2 * N_POINTS_TWIST + N_POINTS_CURVE)))

        return optimise_script(out)

    def miller_loop_input_data(
        self, point_p: list[int], point_q: list[int], lambdas_q_exp_miller_loop: list[list[list[int]]]
    ) -> Script:
        """Input data required to execute the function `miller_loop`.

        Args:
            point_p (list[int]): Point `P` at which the Miller loop is evaluated.
            point_q (list[int]): Point `Q` at which the Miller loop is evaluated.
            lambdas_q_exp_miller_loop (list[list[list[int]]]): lambdas needed to compute the multiplication (t-1)Q. See
                unrolled_multiplication_input.

        Returns:
            Script pushing the input data required to execute the function `miller_loop`.
        """
        out = nums_to_script([self.MODULUS])
        for i in range(len(lambdas_q_exp_miller_loop) - 1, -1, -1):
            for j in range(len(lambdas_q_exp_miller_loop[i]) - 1, -1, -1):
                out += nums_to_script(lambdas_q_exp_miller_loop[i][j])

        out += nums_to_script(point_p)
        out += nums_to_script(point_q)

        return out
