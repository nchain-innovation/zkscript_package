"""Bitcoin scripts that compute the product of three Miller loops."""

from tx_engine import Script

from src.zkscript.script_types.stack_elements import (
    StackEllipticCurvePoint,
    StackEllipticCurvePointProjective,
    StackFiniteFieldElement,
)
from src.zkscript.util.utility_functions import boolean_list_to_bitmask, optimise_script
from src.zkscript.util.utility_scripts import pick, roll, verify_bottom_constant


class TripleMillerLoopProj:
    """Triple Miller loop in projective coordinates."""

    def __one_step_without_addition_proj(
        self,
        loop_i: int,
        take_modulo: bool,
        P: list[StackEllipticCurvePoint],  # noqa: N803
        T: list[StackEllipticCurvePointProjective],  # noqa: N803
    ) -> Script:
        """Generate the script to perform one step in the calculation of the Miller loop.

        The function generates the script to perform one step in the calculation of the Miller loop when
        there is no addition to be computed and the gradients are already loaded on the stack.

        Args:
            loop_i (int): The step begin performed in the computation of the Miller loop.
            take_modulo (bool): Boolean value to decide if the modulo is taken after calculating the evaluations.
            P (list[StackEllipticCurvePoint]): List of the points P needed for the evaluations.
            T (list[StackEllipticCurvePoint]): List of the points T needed for the evaluations and the
                doublings. i-th step of the calculation of w*Q
        """
        out = Script()
        N_ELEMENTS_EVALUATION_OUTPUT_PROJ = self.N_ELEMENTS_EVALUATION_OUTPUT + 1
        N_ELEMENTS_MILLER_OUTPUT_PROJ = self.N_ELEMENTS_MILLER_OUTPUT + 1

        shift = 0 if loop_i == len(self.exp_miller_loop) - 2 else N_ELEMENTS_MILLER_OUTPUT_PROJ

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}, ev_(l_(T1,T1))(P1)]
        out += self.line_eval_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            is_tangent=True,
            P=P[0].shift(shift),
            T=T[0].shift(shift),
            rolling_option=0,
        )  # Compute ev_(l_(T1,T1))(P1)

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}, ev_(l_(T1,T1))(P1)]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}, ev_(l_(T1,T1))(P1)]
        out += self.line_eval_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            is_tangent=True,
            P=P[1].shift(N_ELEMENTS_EVALUATION_OUTPUT_PROJ + shift),
            T=T[1].shift(N_ELEMENTS_EVALUATION_OUTPUT_PROJ + shift),
            rolling_option=0,
        )  # Compute ev_(l_(T2,T2))(P2)

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}, ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2)]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}, ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2),
        #               ev_(l_(T3,T3))(P3)]
        out += self.line_eval_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            is_tangent=True,
            P=P[2].shift(2 * N_ELEMENTS_EVALUATION_OUTPUT_PROJ + shift),
            T=T[2].shift(2 * N_ELEMENTS_EVALUATION_OUTPUT_PROJ + shift),
            rolling_option=0,
        )  # Compute ev_(l_(T3,T3))(P3)

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}, ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2),
        #               ev_(l_(T3,T3))(P3)]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #               (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]

        out += self.rational_form(
            function_name="line_eval_times_eval",
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )  # Compute ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)

        out += self.rational_form(
            function_name="line_eval_times_eval_times_eval",
            take_modulo=take_modulo and loop_i == len(self.exp_miller_loop) - 2,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )  # Compute ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)

        if loop_i != len(self.exp_miller_loop) - 2:
            # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3,
            #               {f_i^2}, (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
            # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3,
            #               {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
            out += self.rational_form(
                function_name="miller_loop_output_times_eval_times_eval_times_eval",
                take_modulo=take_modulo,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute f_i * (t1 * t2 * t3)

        # stack in:     [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3,
        #                   {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        # altstack out: [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT_PROJ))

        # stack in:     [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        # altstack in:  [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, T2, T3, (2*T1)]
        # altstack out: [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]

        out += self.point_doubling_twisted_curve_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            P=T[0],
            rolling_option=1,
        )  # Compute 2*T1

        # stack in:     [P1, P2, P3, Q1, Q2, Q3, T2, T3, (2*T1)]
        # altstack in:  [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, T3, (2*T1), (2*T2)]
        # altstack out: [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        out += self.point_doubling_twisted_curve_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            P=T[1].shift(3 * self.extension_degree),
            rolling_option=1,
        )  # Compute 2*T2

        # stack in:     [P1, P2, P3, Q1, Q2, Q3, T3, (2*T1), (2*T2)]
        # altstack in:  [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3)]
        # altstack out: [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        out += self.point_doubling_twisted_curve_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            P=T[2].shift(6 * self.extension_degree),
            rolling_option=1,
        )  # Compute 2*T3

        # stack in:     [..., P1, P2, P3, Q1, Q2, Q3, T3, (2*T1), (2*T2), (2*T3)]
        # altstack in:  [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [..., P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3)
        #                   {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)]
        out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT_PROJ))

        return out

    def __one_step_with_addition_proj(
        self,
        loop_i: int,
        take_modulo: bool,
        P: list[StackEllipticCurvePoint],  # noqa: N803
        Q: list[StackEllipticCurvePoint],  # noqa: N803
        T: list[StackEllipticCurvePointProjective],  # noqa: N803
    ) -> Script:
        """Generate the script to perform one step in the calculation of the Miller loop.

        The function generates the script to perform one step in the calculation of the Miller loop when
        there is an addition to be computed and the gradients are already loaded on the stack.

        Args:
            loop_i (int): The step begin performed in the computation of the Miller loop.
            take_modulo (bool): Booleans that declare whether to take modulos after the evaluations.
            P (list[StackEllipticCurvePoint]): List of the points P needed for the evaluations.
            Q (list[StackEllipticCurvePoint]): List of the points Q needed for the evaluations and the
                additions.
            T (list[StackEllipticCurvePoint]): List of the points T needed for the evaluations and the
                doublings. i-th step of the calculation of w*Q

        """
        N_ELEMENTS_EVALUATION_OUTPUT_PROJ = self.N_ELEMENTS_EVALUATION_OUTPUT + 1
        N_ELEMENTS_MILLER_OUTPUT_PROJ = self.N_ELEMENTS_MILLER_OUTPUT + 1

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3),
        #               without_addition := {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)]

        out = self.__one_step_without_addition_proj(loop_i=loop_i, take_modulo=False, P=P, T=T)

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3), without_addition, ev_(l_(2*T1,± Q1))(P1)]

        out += self.line_eval_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            is_tangent=False,
            P=P[0].shift(N_ELEMENTS_MILLER_OUTPUT_PROJ),
            Q=Q[0].shift(N_ELEMENTS_MILLER_OUTPUT_PROJ).set_negate(self.exp_miller_loop[loop_i] == -1),
            T=T[0].shift(N_ELEMENTS_MILLER_OUTPUT_PROJ),
            rolling_option=0,
        )  # Compute ev_(l_(2*T1,± Q1))(P1)

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3), without_addition, ev_(l_(2*T1,± Q1))(P1)]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3), without_addition, ev_(l_(2*T1,± Q1))(P1),
        #               ev_(l_(2*T2,± Q2))(P2)]
        out += self.line_eval_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            is_tangent=False,
            P=P[1].shift(N_ELEMENTS_MILLER_OUTPUT_PROJ + N_ELEMENTS_EVALUATION_OUTPUT_PROJ),
            Q=Q[1]
            .shift(N_ELEMENTS_MILLER_OUTPUT_PROJ + N_ELEMENTS_EVALUATION_OUTPUT_PROJ)
            .set_negate(self.exp_miller_loop[loop_i] == -1),
            T=T[1].shift(N_ELEMENTS_MILLER_OUTPUT_PROJ + N_ELEMENTS_EVALUATION_OUTPUT_PROJ),
            rolling_option=0,
        )  # Compute ev_(l_(2*T2,± Q2))(P2)

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3), without_addition, ev_(l_(2*T1,± Q1))(P1)]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3), without_addition, ev_(l_(2*T1,± Q1))(P1),
        #               ev_(l_(2*T2,± Q2))(P2), ev_(l_(2*T3,± Q3))(P3)]

        out += self.line_eval_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            is_tangent=False,
            P=P[2].shift(N_ELEMENTS_MILLER_OUTPUT_PROJ + 2 * N_ELEMENTS_EVALUATION_OUTPUT_PROJ),
            Q=Q[2]
            .shift(N_ELEMENTS_MILLER_OUTPUT_PROJ + 2 * N_ELEMENTS_EVALUATION_OUTPUT_PROJ)
            .set_negate(self.exp_miller_loop[loop_i] == -1),
            T=T[2].shift(N_ELEMENTS_MILLER_OUTPUT_PROJ + 2 * N_ELEMENTS_EVALUATION_OUTPUT_PROJ),
            rolling_option=0,
        )  # Compute ev_(l_(2*T3,± Q3))(P3)

        # stack in:     [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3), without_addition,
        #                  ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3)]
        # altstack out: [without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]

        out += self.rational_form(
            function_name="line_eval_times_eval",
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )  # Compute ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)

        out += self.rational_form(
            function_name="line_eval_times_eval_times_eval",
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )  # Compute ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)

        out += self.rational_form(
            function_name="miller_loop_output_times_eval_times_eval_times_eval",
            take_modulo=take_modulo,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )  # without_addition * ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)

        out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT_PROJ))

        # stack in:     [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3)]
        # altstack in:  [without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, T2, T3, (2*T1 ± Q1)]
        # altstack out: [without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        out += self.point_addition_twisted_curve_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            P=T[0],
            Q=Q[0].set_negate(self.exp_miller_loop[loop_i] == -1),
            rolling_option=boolean_list_to_bitmask([True, False]),
        )

        # stack in:     [P1, P2, P3, Q1, Q2, Q3, (2*T2), (2*T3), (2*T1 ± Q1)]
        # altstack in:  [without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, T3, (2*T1 ± Q1), (2*T2 ± Q2)]
        # altstack out: [without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        out += self.point_addition_twisted_curve_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            P=T[1].shift(3 * self.extension_degree),
            Q=Q[1].set_negate(self.exp_miller_loop[loop_i] == -1),
            rolling_option=boolean_list_to_bitmask([True, False]),
        )

        # stack in:     [P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3)]
        # altstack in:  [without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3 ± Q3)]
        # altstack out: [without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        out += self.point_addition_twisted_curve_proj(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            P=T[2].shift(6 * self.extension_degree),
            Q=Q[2].set_negate(self.exp_miller_loop[loop_i] == -1),
            rolling_option=boolean_list_to_bitmask([True, False]),
        )

        # stack in:     [..., P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3 ± Q3)]
        # altstack in:  [without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        # stack out:    [..., P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3 ± Q3),
        #                    without_addition*ev_(l_(2*T1,± Q1))(P1)*ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3)]
        out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_ELEMENTS_MILLER_OUTPUT_PROJ))

        return out

    def triple_miller_loop_proj(
        self,
        modulo_threshold: int,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Evaluation of the product of three Miller loops.

        Stack input:
            - stack:    [q, ..., P1, P2, P3, Q1, Q2, Q3], `P` is a point on E(F_q), `Q` is a point on
                E'(F_q^{k/d})
            - altstack: []

        Stack output:
            - stack:    [q, ..., miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]
            - altstack: []

        Args:
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to evaluate the product of three Miller loops.

        Preconditions:
            - Pi are passed as couples of integers (minimally encoded, in little endian)
            - Qi are passed as couples of elements in F_q^{k/d}
            - miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)

        Notes:
            At the beginning of every iteration of the loop the stack is assumed to be:
                    [... P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i]
            where:
                - f_i is the value of the i-th step in the computation of
                    [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]
            If exp_miller_loop[loop_i] != 0, then the stack is:
                [... P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i]

            The computation at the i-th iteration of the loop is as follows:
                - if exp_miller_loop[loop_i] == 0, then:
                    - compute t_j = ev_l_(T_j,T,j)(P_j)
                    - compute 2 * T_j
                    - compute t_1 * t_2 * t_3
                    - compute f_i * (t_1 * t_2 * t_3) to get f_(i+1)
                - exp_miller_loop[loop_i] != 0, then:
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
        P = [
            StackEllipticCurvePoint(
                StackFiniteFieldElement(15 * self.extension_degree + i * self.N_POINTS_CURVE - 1, False, 1),
                StackFiniteFieldElement(15 * self.extension_degree + i * self.N_POINTS_CURVE - 2, False, 1),
            )
            for i in range(3, 0, -1)
        ]
        Q = [
            StackEllipticCurvePoint(
                StackFiniteFieldElement((2 * i + 3) * self.extension_degree - 1, False, self.extension_degree),
                StackFiniteFieldElement((2 * i + 2) * self.extension_degree - 1, False, self.extension_degree),
            )
            for i in range(6, 3, -1)
        ]
        T = [
            StackEllipticCurvePointProjective(
                StackFiniteFieldElement((3 * i) * self.extension_degree - 1, False, self.extension_degree),
                StackFiniteFieldElement((3 * i - 1) * self.extension_degree - 1, False, self.extension_degree),
                StackFiniteFieldElement((3 * i - 2) * self.extension_degree - 1, False, self.extension_degree),
            )
            for i in range(3, 0, -1)
        ]

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:  [P1, P2, P3, Q1, Q2, Q3]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        for i in range(3):
            for j in range(self.N_POINTS_TWIST):
                out += pick(position=3 * self.N_POINTS_TWIST - 1 + self.extension_degree * i, n_elements=1)
                out += Script.parse_string(
                    "OP_NEGATE" if self.exp_miller_loop[-1] == -1 and j >= self.N_POINTS_TWIST // 2 else ""
                )
            # convert Ti to projective coordinates
            out += Script.parse_string(f"OP_1 {'OP_0 ' * (self.extension_degree - 1)}"[:-1])

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, w*Q1, w*Q2, w*Q3, (miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))]

        for loop_i in range(len(self.exp_miller_loop) - 2, -1, -1):
            if loop_i != len(self.exp_miller_loop) - 2:
                # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, f_i]
                # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, f_i^2]
                out += self.rational_form(
                    function_name="miller_loop_output_square",
                    take_modulo=True,
                    check_constant=False,
                    clean_constant=False,
                )

            if self.exp_miller_loop[loop_i] == 0:
                # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}]
                # stack out: [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3),
                #               {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)]
                out += self.__one_step_without_addition_proj(
                    loop_i=loop_i,
                    take_modulo=False,
                    P=P,
                    T=T,
                )

            else:
                # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}]
                # stack out: [P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3 ± Q3),
                #               {f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501

                out += self.__one_step_with_addition_proj(
                    loop_i=loop_i,
                    take_modulo=False,
                    P=P,
                    Q=Q,
                    T=T,
                )

        # num = numerator of (miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)) in F_q^{k/d}
        # denom = denominator of (miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)) in F_q
        # stack in:  [P1, P2, P3, Q1, Q2, Q3, w*Q1, w*Q2, w*Q3, num, denom]
        # stack out: [(miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))]

        out += self.inverse_fq(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            rolling_option=1,
            mod_frequency=modulo_threshold // (self.modulus.bit_length() * 3 + 3),
        )
        out += self.scalar_multiplication_fq(
            take_modulo=True,
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            is_constant_reused=False,
            rolling_option=3,
        )

        for _ in range(
            3 * (self.N_POINTS_TWIST + self.extension_degree)  # Points wQi
            + 3 * self.N_POINTS_TWIST  # Points Qi
            + 3 * self.N_POINTS_CURVE  # Points Pi
        ):
            out += roll(position=self.N_ELEMENTS_MILLER_OUTPUT, n_elements=1)
            out += Script.parse_string("OP_DROP")

        return optimise_script(out)
