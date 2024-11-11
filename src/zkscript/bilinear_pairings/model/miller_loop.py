"""Bitcoin scripts that compute the Miller loop."""

from math import ceil, log2

from tx_engine import Script

from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import move, pick, roll, verify_bottom_constant


class MillerLoop:
    """Miller loop operation."""
    def __one_step_without_addition(
        self,
        i: int,
        take_modulo: list[bool],
        positive_modulo: bool,
        clean_constant: bool,
        gradient_doubling: StackFiniteFieldElement,
        P: StackEllipticCurvePoint,  # noqa: N803
        T: StackEllipticCurvePoint,  # noqa: N803
    ) -> Script:
        """Generate the script to perform one step in the calculation of the Miller loop.

        The function generates the script to perform one step in the calculation of the Miller loop when
        there is no addition to be computed.

        Args:
            i (int): The step begin performed in the computation of the Miller loop.
            take_modulo (List[bool]): List of two booleans that declare whether to take modulos after
                calculating the evaluations and the points doubling.
            clean_constant (bool): Whether to clean the constant at the end of the execution of the
                Miller loop.
            gradient_doubling (StackFiniteFieldElement): List of gradients needed for doubling.
            P (StackEllipticCurvePoint): List of the points P needed for the evaluations.
            T (StackEllipticCurvePoint): List of the points T needed for the evaluations and the
                doublings. i-th step of the calculation of w*Q

        """
        shift = 0 if i == len(self.exp_miller_loop) - 2 else self.N_ELEMENTS_MILLER_OUTPUT
        out = Script()
        # stack in:  [gradient_(2T), P, Q, T, {f_i^2}]
        # stack out: [gradient_(2T), P, Q, T, {f_i^2}, ev_(l_(T,T))(P)]
        out += self.line_eval(
            take_modulo=True,
            check_constant=False,
            clean_constant=False,
            gradient=gradient_doubling.shift(shift),
            P=P.shift(shift),
            Q=T.shift(shift),
            rolling_options=0,
        )  # Compute ev_(l_(T,T))(P)
        if i != len(self.exp_miller_loop) - 2:
            # stack in:  [gradient_(2T), P, Q, T, {f_i^2}, ev_(l_(T,T))(P)]
            # stack out: [gradient_(2T), P, Q, T, ({f_i^2} * ev_(l_(T,T))(P))]
            out += self.miller_loop_output_times_eval(
                take_modulo=take_modulo[0], positive_modulo=positive_modulo and (i==0), check_constant=False, clean_constant=False, is_constant_reused=False
            )
        # stack in:  [gradient_(2T), P, Q, T, ({f_i^2} * ev_(l_(T,T))(P))]
        # stack out: [gradient_(2T), P, Q, T]
        # altstack out: [({f_i^2} * ev_(l_(T,T))(P))]
        out += Script.parse_string(
            " ".join(
                ["OP_TOALTSTACK"]
                * (
                    self.N_ELEMENTS_MILLER_OUTPUT
                    if i != len(self.exp_miller_loop) - 2
                    else self.N_ELEMENTS_EVALUATION_OUTPUT
                )
            )
        )
        # stack in:     [gradient_(2T), P, Q, T]
        # altstack in:  [({f_i^2} * ev_(l_(T,T))(P))]
        # stack out:    [P, Q, 2T]
        # altstack out: [({f_i^2} * ev_(l_(T,T))(P))]
        out += self.point_doubling_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=positive_modulo and (i==0),
            check_constant=False,
            clean_constant=(i == 0) and clean_constant,
            verify_gradient=True,
            gradient=gradient_doubling,
            P=T,
            rolling_options=3,
        )
        # stack in:    [P, Q, 2T]
        # altstack in: [({f_i^2} * ev_(l_(T,T))(P))]
        # stack out:   [P, Q, 2T, ({f_i^2} * ev_(l_(T,T))(P))]
        out += Script.parse_string(
            " ".join(
                ["OP_FROMALTSTACK"]
                * (
                    self.N_ELEMENTS_MILLER_OUTPUT
                    if i != len(self.exp_miller_loop) - 2
                    else self.N_ELEMENTS_EVALUATION_OUTPUT
                )
            )
        )
        return out

    def __one_step_with_addition(
        self,
        i: int,
        take_modulo: list[bool],
        positive_modulo: bool,
        clean_constant: bool,
        gradient_doubling: StackFiniteFieldElement,
        gradient_addition: StackFiniteFieldElement,
        P: StackEllipticCurvePoint,  # noqa: N803
        Q: StackEllipticCurvePoint,  # noqa: N803
        T: StackEllipticCurvePoint,  # noqa: N803
    ) -> Script:
        """Generate the script to perform one step in the calculation of the Miller loop.

        The function generates the script to perform one step in the calculation of the Miller loop when
        there is addition to be computed.

        Args:
            i (int): The step begin performed in the computation of the Miller loop.
            take_modulo (List[bool]): List of two booleans that declare whether to take modulos after
                calculating the evaluations and the points doubling.
            clean_constant (bool): Whether to clean the constant at the end of the execution of the
                Miller loop.
            gradient_doubling (StackFiniteFieldElement): List of gradients needed for doubling.
            gradient_addition (StackFiniteFieldElement): List of gradients needed for addition.
            P (StackEllipticCurvePoint): List of the points P needed for the evaluations.
            Q (StackEllipticCurvePoint): List of the points Q needed for the evaluations and the
                additions.
            T (StackEllipticCurvePoint): List of the points T needed for the evaluations and the
                doublings. i-th step of the calculation of w*Q

        """
        shift = 0 if i == len(self.exp_miller_loop) - 2 else self.N_ELEMENTS_MILLER_OUTPUT
        out = Script()
        # stack in:  [gradient_(2T ± Q), gradient_(2T), P, Q, T, {f_i^2}]
        # stack out: [gradient_(2T ± Q), gradient_(2T), P, Q, T, {f_i^2}, ev_(l_(T,T))(P)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            gradient=gradient_doubling.shift(shift),
            P=P.shift(shift),
            Q=T.shift(shift),
            rolling_options=0,
        )  # Compute ev_(l_(T,T))(P)
        # stack in:  [gradient_(2T ± Q), gradient_(2T), P, Q, T, {f_i^2}, ev_(l_(T,T))(P)]
        # stack out: [gradient_(2T ± Q), gradient_(2T), P, Q, T, {f_i^2}, ev_(l_(T,T))(P), ev_(l_(2T, ± Q))(P)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            gradient=gradient_addition.shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            P=P.shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            Q=Q.shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift).set_negate(self.exp_miller_loop[i] == -1),
            rolling_options=0,
        )  # Compute ev_(l_(2T, ±Q))(P)
        # stack in:  [gradient_(2T ± Q), gradient_(2T), P, Q, T, {f_i^2}, ev_(l_(T,T))(P), ev_(l_(2T, ± Q))(P)]
        # stack out: [gradient_(2T ± Q), gradient_(2T), P, Q, T, {f_i^2}, (ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        out += self.line_eval_times_eval(
            take_modulo=take_modulo[0] if i == len(self.exp_miller_loop) - 2 else False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )
        if i != len(self.exp_miller_loop) - 2:
            # stack in:  [gradient_(2T ± Q), gradient_(2T), P, Q, T, {f_i^2}, (ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
            # stack out: [gradient_(2T ± Q), gradient_(2T), P, Q, T,
            #               ({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
            out += self.miller_loop_output_times_eval_times_eval(
                take_modulo=take_modulo[0],
                positive_modulo=positive_modulo and (i==0),
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
        # stack in:     [gradient_(2T ± Q), gradient_(2T), P, Q, T, ({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        # stack out:    [gradient_(2T ± Q), gradient_(2T), P, Q, T]
        # altstack out: [({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        out += Script.parse_string(
            " ".join(
                ["OP_TOALTSTACK"]
                * (
                    self.N_ELEMENTS_MILLER_OUTPUT
                    if i != len(self.exp_miller_loop) - 2
                    else self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                )
            )
        )
        # stack in:     [gradient_(2T ± Q), gradient_(2T), P, Q, T]
        # altstack in:  [({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        # stack out:    [gradient_(2T ± Q), P, Q, 2T]
        # altstack out: [({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        out += self.point_doubling_twisted_curve(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            verify_gradient=True,
            gradient=gradient_doubling,
            P=T,
            rolling_options=3,
        )  # Compute 2T
        # stack in:     [gradient_(2T ± Q), P, Q, 2T]
        # altstack in:  [({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        # stack out:    [P, Q, (2T ± Q)]
        # altstack out: [({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        out += self.point_addition_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=positive_modulo and (i==0),
            check_constant=False,
            clean_constant=(i == 0) and clean_constant,
            verify_gradient=True,
            gradient=gradient_addition.shift(-self.EXTENSION_DEGREE),
            P=Q.set_negate(self.exp_miller_loop[i] == -1),
            Q=T,
            rolling_options=5,
        )  # Compute (2T ± Q)
        # stack in:     [P, Q, (2T ± Q)]
        # altstack in:  [({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        # stack out:    [P, Q, (2T ± Q), ({f_i^2} * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2]
        # altstack out: []
        out += Script.parse_string(
            " ".join(
                ["OP_FROMALTSTACK"]
                * (
                    self.N_ELEMENTS_MILLER_OUTPUT
                    if i != len(self.exp_miller_loop) - 2
                    else self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION
                )
            )
        )
        return out

    def miller_loop(
        self,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
    ) -> Script:
        """Evaluation of the Miller loop at points `P` and `Q`.

        Stack input:
            - stack:    [q, ..., gradients, P, Q], `P` is a point on E(F_q), `Q` is a point on E'(F_q^{k/d}), `gradients` is
                the sequence of gradients to compute the miller loop
            - altstack: []

        Stack output:
            - stack:    [q, ..., wQ, miller(P,Q)], `miller(P,Q) = f_(w,Q)(P)` is in F_q^k
            - altstack: []

        Args:
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.

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
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack in:  [P, Q]
        # stack out: [P, Q, T]
        for j in range(self.N_POINTS_TWIST):
            out += pick(position=self.N_POINTS_TWIST - 1, n_elements=1)
            if self.exp_miller_loop[-1] == -1 and j >= self.N_POINTS_TWIST // 2:
                out += Script.parse_string("OP_NEGATE")

        BIT_SIZE_Q = ceil(log2(self.MODULUS))
        size_point_multiplication = BIT_SIZE_Q
        size_miller_output = BIT_SIZE_Q

        gradient_addition = StackFiniteFieldElement(
            2 * self.N_POINTS_TWIST + self.N_POINTS_CURVE + 2 * self.EXTENSION_DEGREE - 1, False, self.EXTENSION_DEGREE
        )
        gradient_doubling = StackFiniteFieldElement(
            2 * self.N_POINTS_TWIST + self.N_POINTS_CURVE + self.EXTENSION_DEGREE - 1, False, self.EXTENSION_DEGREE
        )
        P = StackEllipticCurvePoint(
            StackFiniteFieldElement(2 * self.N_POINTS_TWIST + self.N_POINTS_CURVE - 1, False, self.N_POINTS_CURVE // 2),
            StackFiniteFieldElement(
                2 * self.N_POINTS_TWIST + self.N_POINTS_CURVE // 2 - 1, False, self.N_POINTS_CURVE // 2
            ),
        )
        Q = StackEllipticCurvePoint(
            StackFiniteFieldElement(2 * self.N_POINTS_TWIST - 1, False, self.N_POINTS_TWIST // 2),
            StackFiniteFieldElement(
                self.N_POINTS_TWIST + self.N_POINTS_TWIST // 2 - 1, False, self.N_POINTS_TWIST // 2
            ),
        )
        T = StackEllipticCurvePoint(
            StackFiniteFieldElement(self.N_POINTS_TWIST - 1, False, self.N_POINTS_TWIST // 2),
            StackFiniteFieldElement(self.N_POINTS_TWIST // 2 - 1, False, self.N_POINTS_TWIST // 2),
        )
        # stack in:  [P, Q, T]
        # stack out: [w*Q, miller(P,Q)]
        for i in range(len(self.exp_miller_loop) - 2, -1, -1):
            positive_modulo_i = False

            # Constants set up
            if i == 0:
                positive_modulo_i = positive_modulo

            (
                take_modulo_miller_loop_output,
                take_modulo_point_multiplication,
                size_miller_output,
                size_point_multiplication,
            ) = self.size_estimation_miller_loop(
                self.MODULUS,
                modulo_threshold,
                i,
                self.exp_miller_loop,
                size_miller_output,
                size_point_multiplication,
                False,
            )

            if i == len(self.exp_miller_loop) - 3:
                if self.exp_miller_loop[i + 1] == 0:
                    # stack in:  [P, Q, T, ev_(l_(T,T))(P)]
                    # stack out: [P, Q, T, Dense(ev_(l_(T,T))(P)^2)]
                    out += pick(
                        position=self.N_ELEMENTS_EVALUATION_OUTPUT - 1, n_elements=self.N_ELEMENTS_EVALUATION_OUTPUT
                    )  # Duplicate ev_(l_(T,T))(P)
                    out += self.line_eval_times_eval(
                        take_modulo=take_modulo_miller_loop_output,
                        positive_modulo=False,
                        check_constant=False,
                        clean_constant=False,
                        is_constant_reused=False,
                    )
                    out += self.pad_eval_times_eval_to_miller_output
                else:
                    # stack in:  [P, Q, T, ev_(l_(T,T))(P), ev_(l_(2T, ± Q))(P)]
                    # stack out: [P, Q, T, Dense((ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))^2)]
                    out += pick(
                        position=self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION - 1,
                        n_elements=self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION,
                    )
                    out += self.line_eval_times_eval_times_eval_times_eval(
                        take_modulo=take_modulo_miller_loop_output, positive_modulo=False, check_constant=False, clean_constant=False
                    )
                    out += self.pad_eval_times_eval_times_eval_times_eval_to_miller_output

            if i < len(self.exp_miller_loop) - 3:
                # stack in:  [gradient_(2T), P, Q, T, f_i]
                # stack out: [gradient_(2T), P, Q, T, f_i^2]
                out += self.miller_loop_output_square(take_modulo=True, check_constant=False, clean_constant=False, positive_modulo=False)

            if self.exp_miller_loop[i] == 0:
                # stack in:  [gradient_(2T), P, Q, T, f_i^2]
                # stack out: [P, Q, 2T, (f_i^2 * ev_(l_(T,T))(P))]
                out += self.__one_step_without_addition(
                    i,
                    [take_modulo_miller_loop_output, take_modulo_point_multiplication],
                    positive_modulo_i,
                    clean_constant,
                    gradient_doubling,
                    P,
                    T,
                )
            else:
                # stack in:  [gradient_(2T ± Q), gradient_(2T), P, Q, T, f_i^2]
                # stack out: [P, Q, (2T ± Q), (f_i^2 * ev_(l_(T,T))(P) * ev_(l_(2T, ± Q))(P))]
                out += self.__one_step_with_addition(
                    i,
                    [take_modulo_miller_loop_output, take_modulo_point_multiplication],
                    positive_modulo_i,
                    clean_constant,
                    gradient_doubling,
                    gradient_addition,
                    P,
                    Q,
                    T,
                )

        # stack in:  [P, Q, w*Q, miller(P,Q)]
        # stack out: [w*Q, miller(P,Q)]
        out += move(Q.shift(self.N_ELEMENTS_MILLER_OUTPUT), roll)  # Roll Q
        out += move(P.shift(self.N_ELEMENTS_MILLER_OUTPUT), roll)  # Roll P
        out += Script.parse_string(" ".join(["OP_DROP"] * (self.N_POINTS_TWIST + self.N_POINTS_CURVE)))

        return optimise_script(out)
