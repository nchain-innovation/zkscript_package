"""Bitcoin scripts that compute the product of three Miller loops."""

from math import ceil, log2

from tx_engine import Script

from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import pick, roll, verify_bottom_constant


class TripleMillerLoop:
    """Triple Miller loop."""

    def __one_step_without_addition(
        self,
        i: int,
        take_modulo: list[bool],
        positive_modulo: bool,
        verify_gradients: int,
        clean_constant: bool,
        gradients_doubling: list[StackFiniteFieldElement],
        P: list[StackEllipticCurvePoint],  # noqa: N803
        T: list[StackEllipticCurvePoint],  # noqa: N803
    ) -> Script:
        """Generate the script to perform one step in the calculation of the Miller loop.

        The function generates the script to perform one step in the calculation of the Miller loop when
        there is no addition to be computed.

        Args:
            i (int): The step begin performed in the computation of the Miller loop.
            take_modulo (list[bool]): List of two booleans that declare whether to take modulos after
                calculating the evaluations and the points doubling.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            verify_gradients (int): Bitmask detailing which gradients used in this step of the Miller loop should
                be verified.
            clean_constant (bool): Whether to clean the constant at the end of the execution of the
                Miller loop.
            gradients_doubling (list[StackFiniteFieldElement]): List of gradients needed for doubling.
            P (list[StackEllipticCurvePoint]): List of the points P needed for the evaluations.
            T (list[StackEllipticCurvePoint]): List of the points T needed for the evaluations and the
                doublings. i-th step of the calculation of w*Q

        """
        shift = 0 if i == len(self.exp_miller_loop) - 2 else self.N_ELEMENTS_MILLER_OUTPUT
        out = Script()
        # stack in:  [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}]
        # stack out: [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #               ev_(l_(T1,T1))(P1)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_doubling[0].shift(shift),
            P=P[0].shift(shift),
            Q=T[0].shift(shift),
            rolling_options=0,
        )  # Compute ev_(l_(T1,T1))(P1)
        # stack in:  [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #               ev_(l_(T1,T1))(P1)]
        # stack out: [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #               ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_doubling[1].shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            P=P[1].shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            Q=T[1].shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            rolling_options=0,
        )  # Compute ev_(l_(T2,T2))(P2)
        # stack in:  [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #               ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2)]
        # stack out: [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #               ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2), ev_(l_(T3,T3))(P3)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_doubling[2].shift(2 * self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            P=P[2].shift(2 * self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            Q=T[2].shift(2 * self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            rolling_options=0,
        )  # Compute ev_(l_(T3,T3))(P3)
        # stack in:  [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #               ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2), ev_(l_(T3,T3))(P3)]
        # stack out: [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #               (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        out += self.line_eval_times_eval(
            take_modulo=False, positive_modulo=False, check_constant=False, clean_constant=False
        )  # Compute ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)
        out += self.line_eval_times_eval_times_eval(
            take_modulo=take_modulo[0] if i == len(self.exp_miller_loop) - 2 else False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )  # Compute ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)
        if i != len(self.exp_miller_loop) - 2:
            # stack in:  [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3,
            #               {f_i^2}, (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
            # stack out: [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3,
            #               {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
            out += self.miller_loop_output_times_eval_times_eval_times_eval(
                take_modulo=take_modulo[0],
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute f_i * (t1 * t2 * t3)
        # stack in:     [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3,
        #                   {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        # altstack out: [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * self.N_ELEMENTS_MILLER_OUTPUT))
        # stack in:     [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        # altstack in:  [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T2, T3, (2*T1)]
        # altstack out: [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        out += self.point_doubling_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=False,
            verify_gradient=verify_gradients & 1,
            gradient=gradients_doubling[0],
            P=T[0],
            rolling_options=3,
        )  # Compute 2*T1
        # stack in:     [gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T2, T3, (2*T1)]
        # altstack in:  [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T3, (2*T1), (2*T2)]
        # altstack out: [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        out += self.point_doubling_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=False,
            verify_gradient=(verify_gradients >> 1) & 1,
            gradient=gradients_doubling[1],
            P=T[1].shift(self.N_POINTS_TWIST),
            rolling_options=3,
        )  # Compute 2*T2
        # stack in:     [gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T3, (2*T1), (2*T2)]
        # altstack in:  [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, T3, (2*T1), (2*T2), (2*T3)]
        # altstack out: [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        out += self.point_doubling_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=(i == 0) and clean_constant,
            verify_gradient=(verify_gradients >> 2) & 1,
            gradient=gradients_doubling[2],
            P=T[2].shift(2 * self.N_POINTS_TWIST),
            rolling_options=3,
        )  # Compute 2*T3
        # stack in:     [P1, P2, P3, Q1, Q2, Q3, T3, (2*T1), (2*T2), (2*T3)]
        # altstack in:  [{f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3))]
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, T3, (2*T1), (2*T2), (2*T3)
        #                   {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)]
        out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * self.N_ELEMENTS_MILLER_OUTPUT))

        return out

    def __one_step_with_addition(
        self,
        i: int,
        take_modulo: list[bool],
        positive_modulo: bool,
        verify_gradients: int,
        clean_constant: bool,
        gradients_doubling: list[StackFiniteFieldElement],
        gradients_addition: list[StackFiniteFieldElement],
        P: list[StackEllipticCurvePoint],  # noqa: N803
        Q: list[StackEllipticCurvePoint],  # noqa: N803
        T: list[StackEllipticCurvePoint],  # noqa: N803
    ) -> Script:
        """Generate the script to perform one step in the calculation of the Miller loop.

        The function generates the script to perform one step in the calculation of the Miller loop when
        there is addition to be computed.

        Args:
            i (int): The step begin performed in the computation of the Miller loop.
            take_modulo (list[bool]): List of two booleans that declare whether to take modulos after
                calculating the evaluations and the points doubling.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            verify_gradients (int): Bitmask detailing which gradients used in this step of the Miller loop should
                be verified.
            clean_constant (bool): Whether to clean the constant at the end of the execution of the
                Miller loop.
            gradients_doubling (list[StackFiniteFieldElement]): List of gradients needed for doubling.
            gradients_addition (list[StackFiniteFieldElement]): List of gradients needed for addition.
            P (list[StackEllipticCurvePoint]): List of the points P needed for the evaluations.
            Q (list[StackEllipticCurvePoint]): List of the points Q needed for the evaluations and the
                additions.
            T (list[StackEllipticCurvePoint]): List of the points T needed for the evaluations and the
                doublings. i-th step of the calculation of w*Q

        """
        shift = 0 if i == len(self.exp_miller_loop) - 2 else self.N_ELEMENTS_MILLER_OUTPUT
        out = Script()
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2) gradient_(2*T3) P1, P2, P3, Q1, Q2, Q3, T1, T2, T3 {f_i^2}]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   ev_(l_(T1,T1))(P1)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_doubling[0].shift(shift),
            P=P[0].shift(shift),
            Q=T[0].shift(shift),
            rolling_options=0,
        )  # Compute ev_(l_(T1,T1))(P1)
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   ev_(l_(T1,T1))(P1)]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_doubling[1].shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            P=P[1].shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            Q=T[1].shift(self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            rolling_options=0,
        )  # Compute ev_(l_(T2,T2))(P2)
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   ev_(l_(T1,T1))(P1), ev_(l_(T2,T2))(P2)]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2))]
        out += self.line_eval_times_eval(
            take_modulo=False, positive_modulo=False, check_constant=False, clean_constant=False
        )
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2))]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)), ev_(l_(T3,T3))(P3)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_doubling[2].shift(self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + shift),
            P=P[2].shift(self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + shift),
            Q=T[2].shift(self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + shift),
            rolling_options=0,
        )  # Compute ev_(l_(T3,T3))(P3)
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)), ev_(l_(T3,T3))(P3)]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       ev_(l_(T3,T3))(P3), ev_(l_(2*T1,± Q1))(P1)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_addition[0].shift(
                self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + self.N_ELEMENTS_EVALUATION_OUTPUT + shift
            ),
            P=P[0].shift(self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            Q=Q[0]
            .shift(self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + self.N_ELEMENTS_EVALUATION_OUTPUT + shift)
            .set_negate(self.exp_miller_loop[i] == -1),
            rolling_options=0,
        )  # Compute ev_(l_(2*T1,± Q1))(P1)
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       ev_(l_(T3,T3))(P3), ev_(l_(2*T1,± Q1))(P1)]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       (ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1))]
        out += self.line_eval_times_eval(
            take_modulo=False, positive_modulo=False, check_constant=False, clean_constant=False
        )
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       (ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1))]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       (ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)),
        #                           ev_(l_(2*T2,± Q2))(P2)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_addition[1].shift(2 * self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + shift),
            P=P[1].shift(2 * self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + shift),
            Q=Q[1]
            .shift(2 * self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + shift)
            .set_negate(self.exp_miller_loop[i] == -1),
            rolling_options=0,
        )
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       (ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)),
        #                           ev_(l_(2*T2,± Q2))(P2)]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       (ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)),
        #                           ev_(l_(2*T2,± Q2))(P2), ev_(l_(2*T3,± Q3))(P3)]
        out += self.line_eval(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            gradient=gradients_addition[2].shift(
                2 * self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + self.N_ELEMENTS_EVALUATION_OUTPUT + shift
            ),
            P=P[2].shift(2 * self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + self.N_ELEMENTS_EVALUATION_OUTPUT + shift),
            Q=Q[2]
            .shift(2 * self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION + self.N_ELEMENTS_EVALUATION_OUTPUT + shift)
            .set_negate(self.exp_miller_loop[i] == -1),
            rolling_options=0,
        )
        # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       (ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)),
        #                           ev_(l_(2*T2,± Q2))(P2), ev_(l_(2*T3,± Q3))(P3)]
        # stack out: [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                   (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                       (ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)),
        #                           (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]
        out += self.line_eval_times_eval(
            take_modulo=False, positive_modulo=False, check_constant=False, clean_constant=False
        )
        # stack in:    [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #                   gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2},
        #                       (ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)),
        #                           (ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)),
        #                               (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]
        # stack out:    [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #                   gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        # altstack out: [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        out += self.line_eval_times_eval_times_eval_times_eval(
            take_modulo=False, positive_modulo=False, check_constant=False, clean_constant=False
        )
        out += self.line_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
            take_modulo=take_modulo[0] if i == len(self.exp_miller_loop) - 2 else False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )
        if i != len(self.exp_miller_loop) - 2:
            out += self.miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval(
                take_modulo=take_modulo[0],
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
        out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * self.N_ELEMENTS_MILLER_OUTPUT))
        # stack in:     [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
        #                   gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        # altstack in:  [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        # stack out:    [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3),
        #                   gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T2, T3, (2*T1)]
        # altstack out: [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        out += self.point_doubling_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            verify_gradient=verify_gradients & 1,
            gradient=gradients_doubling[0],
            P=T[0],
            rolling_options=3,
        )  # Compute 2 * T1
        # stack in:     [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3),
        #                   gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T2, T3, 2*T1]
        # altstack in:  [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        # stack out:    [gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3),
        #                   gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T2, T3, (2*T1 ± Q1)]
        # altstack out: [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        out += self.point_addition_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=False,
            verify_gradient=verify_gradients & 1,
            gradient=gradients_addition[0].shift(-self.EXTENSION_DEGREE),
            P=Q[0].set_negate(self.exp_miller_loop[i] == -1),
            Q=T[0].shift(-2 * self.N_POINTS_TWIST),
            rolling_options=5,
        )
        # stack in:     [gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3),
        #                   gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T2, T3, (2*T1 ± Q1)]
        # altstack in:  [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        # stack out:    [gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3),
        #                   gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T3, (2*T1 ± Q1), (2*T2)]
        # altstack out: [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        out += self.point_doubling_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            verify_gradient=(verify_gradients >> 1) & 1,
            gradient=gradients_doubling[1],
            P=T[1].shift(self.N_POINTS_TWIST),
            rolling_options=3,
        )  # Compute 2 * T2
        # stack in:     [gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3),
        #                   gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T3, (2*T1 ± Q1), (2*T2)]
        # altstack in:  [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        # stack out:    [gradient_(2* T3 ± Q3), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T3, (2*T1 ± Q1), (2*T2 ± Q2)]
        # altstack out: [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        out += self.point_addition_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=False,
            verify_gradient=(verify_gradients >> 1) & 1,
            gradient=gradients_addition[1].shift(-2 * self.EXTENSION_DEGREE),
            P=Q[1].set_negate(self.exp_miller_loop[i] == -1),
            Q=T[1].shift(-self.N_POINTS_TWIST),
            rolling_options=5,
        )
        # stack in:     [gradient_(2* T3 ± Q3), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T3, (2*T1 ± Q1), (2*T2 ± Q2)]
        # altstack in:  [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        # stack out:    [gradient_(2* T3 ± Q3), P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3)]
        # altstack out: [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        out += self.point_doubling_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            verify_gradient=(verify_gradients >> 2) & 1,
            gradient=gradients_doubling[2],
            P=T[2].shift(2 * self.N_POINTS_TWIST),
            rolling_options=3,
        )  # Compute 2 * T3
        # stack in:     [gradient_(2* T3 ± Q3), P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3)]
        # altstack in:  [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3 ± Q3)]
        # altstack out: [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        out += self.point_addition_twisted_curve(
            take_modulo=take_modulo[1],
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=(i == 0) and clean_constant,
            verify_gradient=(verify_gradients >> 2) & 1,
            gradient=gradients_addition[2].shift(-3 * self.EXTENSION_DEGREE),
            P=Q[2].set_negate(self.exp_miller_loop[i] == -1),
            Q=T[2],
            rolling_options=5,
        )
        # stack in:     [P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3 ± Q3)]
        # altstack in:  [{f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        # stack out:    [P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3 ± Q3),
        #                    {f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
        out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * self.N_ELEMENTS_MILLER_OUTPUT))

        return out

    def triple_miller_loop(
        self,
        modulo_threshold: int,
        positive_modulo: bool = True,
        verify_gradients: int = 7,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Evaluation of the product of three Miller loops.

        Stack input:
            - stack:    [q, ..., gradients, P1, P2, P3, Q1, Q2, Q3], `P` is a point on E(F_q), `Q` is a point on
                E'(F_q^{k/d})
            - altstack: []

        Stack output:
            - stack:    [q, ..., miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]
            - altstack: []

        Args:
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            verify_gradients (int): Bitmask detailing which of the gradients used in the Miller loop should
                be verified. Defaults to `7` (all the gradients are verified).
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
            [... gradient_(2*T1) gradient_(2*T2) gradient_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i]
            where:
                - gradient_(2*Tj) is the gradient of the line tangent at Tj.
                - f_i is the value of the i-th step in the computation of
                    [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]
            If exp_miller_loop[i] != 0, then the stack is:
                [... gradient_(2* T1 pm Q1) gradient_(2* T2 pm Q2) gradient_(2* T3 pm Q3) gradient_(2*T1)
                    gradient_(2*T2) gradient_(2*T3) P1 P2 P3 Q1 Q2 Q3 -Q1 -Q2 -Q3 T1 T2 T3 f_i]
            where:
                - gradient_(2* Tj pm Qj) is the gradient of the line through 2 * Tj and (pm Qj)

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
        gradients_addition = [
            StackFiniteFieldElement(
                6 * self.N_POINTS_TWIST + 3 * self.N_POINTS_CURVE + i * self.EXTENSION_DEGREE - 1,
                False,
                self.EXTENSION_DEGREE,
            )
            for i in range(6, 3, -1)
        ]
        gradients_doubling = [
            StackFiniteFieldElement(
                6 * self.N_POINTS_TWIST + 3 * self.N_POINTS_CURVE + i * self.EXTENSION_DEGREE - 1,
                False,
                self.EXTENSION_DEGREE,
            )
            for i in range(3, 0, -1)
        ]
        P = [
            StackEllipticCurvePoint(
                StackFiniteFieldElement(
                    6 * self.N_POINTS_TWIST + i * self.N_POINTS_CURVE - 1, False, self.N_POINTS_CURVE // 2
                ),
                StackFiniteFieldElement(
                    6 * self.N_POINTS_TWIST + (i - 1) * self.N_POINTS_CURVE + self.N_POINTS_CURVE // 2 - 1,
                    False,
                    self.N_POINTS_CURVE // 2,
                ),
            )
            for i in range(3, 0, -1)
        ]
        Q = [
            StackEllipticCurvePoint(
                StackFiniteFieldElement(i * self.N_POINTS_TWIST - 1, False, self.N_POINTS_TWIST // 2),
                StackFiniteFieldElement(
                    (i - 1) * self.N_POINTS_TWIST + self.N_POINTS_TWIST // 2 - 1, False, self.N_POINTS_TWIST // 2
                ),
            )
            for i in range(6, 3, -1)
        ]
        T = [
            StackEllipticCurvePoint(
                StackFiniteFieldElement(i * self.N_POINTS_TWIST - 1, False, self.N_POINTS_TWIST // 2),
                StackFiniteFieldElement(
                    (i - 1) * self.N_POINTS_TWIST + self.N_POINTS_TWIST // 2 - 1, False, self.N_POINTS_TWIST // 2
                ),
            )
            for i in range(3, 0, -1)
        ]

        BIT_SIZE_Q = ceil(log2(self.MODULUS))
        size_point_multiplication = BIT_SIZE_Q
        size_miller_output = BIT_SIZE_Q

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack in:  [P1, P2, P3, Q1, Q2, Q3]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        for _ in range(3):
            for j in range(self.N_POINTS_TWIST):
                out += pick(position=3 * self.N_POINTS_TWIST - 1, n_elements=1)
                out += Script.parse_string(
                    "OP_NEGATE" if self.exp_miller_loop[-1] == -1 and j >= self.N_POINTS_TWIST // 2 else ""
                )

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3]
        # stack out: [P1, P2, P3, Q1, Q2, Q3, w*Q1, w*Q2, w*Q3, (miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))]
        for i in range(len(self.exp_miller_loop) - 2, -1, -1):
            positive_modulo_i = positive_modulo if i == 0 else False
            clean_constant_i = clean_constant if i == 0 else False

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
                True,
            )

            if i != len(self.exp_miller_loop) - 2:
                # stack in:  [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, f_i]
                # stack out: [P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, f_i^2]
                out += self.miller_loop_output_square(take_modulo=False, check_constant=False, clean_constant=False)
            if self.exp_miller_loop[i] == 0:
                # stack in:  [gradient_(2*T1), gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3,
                #               {f_i^2}]
                # stack out: [P1, P2, P3, Q1, Q2, Q3, (2*T1), (2*T2), (2*T3),
                #               {f_i^2} * (ev_(l_(T1,T1))(P1) * ev_(l_(T2,T2))(P2) * ev_(l_(T3,T3))(P3)]
                out += self.__one_step_without_addition(
                    i=i,
                    take_modulo=[take_modulo_miller_loop_output, take_modulo_point_multiplication],
                    positive_modulo=positive_modulo_i,
                    verify_gradients=verify_gradients,
                    clean_constant=clean_constant_i,
                    gradients_doubling=gradients_doubling,
                    P=P,
                    T=T,
                )
            else:
                # stack in:  [gradient_(2* T1 ± Q1), gradient_(2* T2 ± Q2), gradient_(2* T3 ± Q3), gradient_(2*T1),
                #               gradient_(2*T2), gradient_(2*T3), P1, P2, P3, Q1, Q2, Q3, T1, T2, T3, {f_i^2}]
                # stack out: [P1, P2, P3, Q1, Q2, Q3, (2*T1 ± Q1), (2*T2 ± Q2), (2*T3 ± Q3),
                #               {f_i^2}*(ev_(l_(T1,T1))(P1)*ev_(l_(T2,T2))(P2)) *(ev_(l_(T3,T3))(P3)*ev_(l_(2*T1,± Q1))(P1)) * (ev_(l_(2*T2,± Q2))(P2)*ev_(l_(2*T3,± Q3))(P3))]  # noqa: E501
                out += self.__one_step_with_addition(
                    i=i,
                    take_modulo=[take_modulo_miller_loop_output, take_modulo_point_multiplication],
                    positive_modulo=positive_modulo_i,
                    verify_gradients=verify_gradients,
                    clean_constant=clean_constant_i,
                    gradients_doubling=gradients_doubling,
                    gradients_addition=gradients_addition,
                    P=P,
                    Q=Q,
                    T=T,
                )

        # stack in:  [P1, P2, P3, Q1, Q2, Q3, w*Q1, w*Q2, w*Q3, (miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))]
        # stack out: [(miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))]
        out += roll(
            position=6 * self.N_POINTS_TWIST + 3 * self.N_POINTS_CURVE + self.N_ELEMENTS_MILLER_OUTPUT - 1,
            n_elements=6 * self.N_POINTS_TWIST + 3 * self.N_POINTS_CURVE,
        )
        out += Script.parse_string(" ".join(["OP_DROP"] * (6 * self.N_POINTS_TWIST + 3 * self.N_POINTS_CURVE)))

        return optimise_script(out)
