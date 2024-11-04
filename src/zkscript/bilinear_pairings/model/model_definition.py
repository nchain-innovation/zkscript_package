"""Pairing Model."""

from src.zkscript.bilinear_pairings.model.miller_loop import MillerLoop
from src.zkscript.bilinear_pairings.model.pairing import Pairing
from src.zkscript.bilinear_pairings.model.triple_miller_loop import TripleMillerLoop


class PairingModel(MillerLoop, TripleMillerLoop, Pairing):
    """Pairing Model."""

    def __init__(
        self,
        q,
        exp_miller_loop,
        extension_degree,
        n_points_curve,
        n_points_twist,
        n_elements_miller_output,
        n_elements_evaluation_output,
        n_elements_evaluation_times_evaluation,
        point_doubling_twisted_curve,
        point_addition_twisted_curve,
        line_eval,
        line_eval_times_eval,
        line_eval_times_eval_times_eval,
        line_eval_times_eval_times_eval_times_eval,
        line_eval_times_eval_times_eval_times_eval_times_eval_times_eval,
        line_eval_times_eval_times_miller_loop_output,
        miller_loop_output_square,
        miller_loop_output_mul,
        miller_loop_output_times_eval,
        miller_loop_output_times_eval_times_eval,
        miller_loop_output_times_eval_times_eval_times_eval,
        miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval,
        pad_eval_times_eval_to_miller_output,
        pad_eval_times_eval_times_eval_times_eval_to_miller_output,
        cyclotomic_inverse,
        easy_exponentiation_with_inverse_check,
        hard_exponentiation,
    ):
        """Initialise the pairing model.

        Args:
            q: Characteristic of the field over which the pairing is defined.
            exp_miller_loop: Expansion of value over which the Miller loop is carried out.
            extension_degree: Extension degree.
            n_points_curve: Number of integers needed to define a point on the base curve.
            n_points_twist: Number of integers needed to define a point on the twisted curve.
            n_elements_miller_output: Number of integers needed to write the Miller output.
            n_elements_evaluation_output: Number of integers needed to write the result of a line evaluation.
            n_elements_evaluation_times_evaluation: Number of integers needed to write the result of the product of two
                line evaluations.
            point_doubling_twisted_curve: Script to perform point doubling on the twisted curve.
            point_addition_twisted_curve: Script to perform point addition on the twisted curve.
            point_negation_twisted_curve: Script to negate a point on the twisted curve.
            line_eval: Script for line evaluation.
            line_eval_times_eval: Script for product of two line evaluations.
            line_eval_times_eval_times_eval: Script for product of three line evaluations, assuming the first product
                has been calculated: the script computes ev * t1, where t1 = ev * ev.
            line_eval_times_eval_times_eval_times_eval: Script for product of four line evaluations, assuming each
                couple of products has been calculated: the script computes t1 * t2, where t1 = ev * ev, t2 = ev * ev.
            line_eval_times_eval_times_eval_times_eval_times_eval_times_eval: Script of product of six line
                evaluations, assuming each couple of products has been calculated: the script computes t1 * t4, where
                t1 = ev * ev, t4 = t2 * t3, t2 = ev * ev, t3 = ev * ev.
            line_eval_times_eval_times_miller_loop_output: Script to compute the multiplication of the product of two
                line evaluations and the Miller output: the script computes t1 * t2, where
                t1 = ev * ev, t2 = miller_output.
            miller_loop_output_square: Script to compute the square of the Miller output.
            miller_loop_output_mul: Script to compute the multiplication of the Miller output with another element in
                F_q^k.
            miller_loop_output_times_eval: Script to compute the multiplication of the Miller output with a line
                evaluation.
            miller_loop_output_times_eval_times_eval: Script to compute the multiplication of the Miller output with 
                a product of two line evaluations: the script computes t1 * t2, where
                t1 = miller_output, t2 = ev * ev
            miller_loop_output_times_eval_times_eval_times_eval: Script to compute the multiplication of the Miller
                output with a product of three line evaluations: the script computes t1 * t2,
                where t1 = miller_output, t2 = ev * ev * ev.
            miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval: Script to compute
                the multiplication of the Miller output with a product of six line evaluations: the script computes
                t1 * t2, where t1 = miller_output, t2 = ev * ev * ev * ev * ev * ev.
            pad_eval_times_eval_to_miller_output: Script to pad a product of two line evaluations to a Miller output.
            pad_eval_times_eval_times_eval_times_eval_to_miller_output: Script to pad a product of four line evaluations
                to a Miller output.
            cyclotomic_inverse: Script to compute the inverse of an element in the cyclotomic subgroup.
            easy_exponentiation_with_inverse_check: Script to compute easy exponentiation with inverse check.
            hard_exponentiation: Script to compute hard exponentiation.
        """
        self.MODULUS = q
        self.exp_miller_loop = exp_miller_loop
        self.EXTENSION_DEGREE = extension_degree
        self.N_POINTS_CURVE = n_points_curve
        self.N_POINTS_TWIST = n_points_twist
        self.N_ELEMENTS_MILLER_OUTPUT = n_elements_miller_output
        self.N_ELEMENTS_EVALUATION_OUTPUT = n_elements_evaluation_output
        self.N_ELEMENTS_EVALUATION_TIMES_EVALUATION = n_elements_evaluation_times_evaluation
        self.point_doubling_twisted_curve = point_doubling_twisted_curve
        self.point_addition_twisted_curve = point_addition_twisted_curve
        self.line_eval = line_eval
        self.line_eval_times_eval = line_eval_times_eval
        self.line_eval_times_eval_times_eval = line_eval_times_eval_times_eval
        self.line_eval_times_eval_times_eval_times_eval = line_eval_times_eval_times_eval_times_eval
        self.line_eval_times_eval_times_eval_times_eval_times_eval_times_eval = (
            line_eval_times_eval_times_eval_times_eval_times_eval_times_eval
        )
        self.line_eval_times_eval_times_miller_loop_output = line_eval_times_eval_times_miller_loop_output
        self.miller_loop_output_square = miller_loop_output_square
        self.miller_loop_output_mul = miller_loop_output_mul
        self.miller_loop_output_times_eval = miller_loop_output_times_eval
        self.miller_loop_output_times_eval_times_eval = miller_loop_output_times_eval_times_eval
        self.miller_loop_output_times_eval_times_eval_times_eval = miller_loop_output_times_eval_times_eval_times_eval
        self.miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval = (
            miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval
        )
        self.pad_eval_times_eval_to_miller_output = pad_eval_times_eval_to_miller_output
        self.pad_eval_times_eval_times_eval_times_eval_to_miller_output = (
            pad_eval_times_eval_times_eval_times_eval_to_miller_output
        )
        self.cyclotomic_inverse = cyclotomic_inverse
        self.easy_exponentiation_with_inverse_check = easy_exponentiation_with_inverse_check
        self.hard_exponentiation = hard_exponentiation
