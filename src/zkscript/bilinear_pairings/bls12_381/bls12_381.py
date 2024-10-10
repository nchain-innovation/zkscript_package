# Build pairing model for BLS12_381

from tx_engine import Script

from src.zkscript.bilinear_pairings.bls12_381.fields import fq2_script
from src.zkscript.bilinear_pairings.bls12_381.final_exponentiation import final_exponentiation
from src.zkscript.bilinear_pairings.bls12_381.line_functions import line_functions
from src.zkscript.bilinear_pairings.bls12_381.miller_output_operations import miller_output_ops
from src.zkscript.bilinear_pairings.bls12_381.parameters import (
    EXTENSION_DEGREE,
    N_ELEMENTS_EVALUATION_OUTPUT,
    N_ELEMENTS_EVALUATION_TIMES_EVALUATION,
    N_ELEMENTS_MILLER_OUTPUT,
    N_POINTS_CURVE,
    N_POINTS_TWIST,
    exp_miller_loop,
    q,
    twisted_a,
)
from src.zkscript.bilinear_pairings.model.model_definition import PairingModel
from src.zkscript.elliptic_curves.ec_operations_fq2 import EllipticCurveFq2

twisted_curve_operations = EllipticCurveFq2(q=q, curve_a=twisted_a, fq2=fq2_script)


def pad_eval_times_eval_to_miller_output() -> Script:
    out = Script()
    out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 6))
    out += Script.parse_string("OP_0 OP_0")
    out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 6))

    return out


bls12_381 = PairingModel(
    q=q,
    exp_miller_loop=exp_miller_loop,
    extension_degree=EXTENSION_DEGREE,
    n_points_curve=N_POINTS_CURVE,
    n_points_twist=N_POINTS_TWIST,
    n_elements_miller_output=N_ELEMENTS_MILLER_OUTPUT,
    n_elements_evaluation_output=N_ELEMENTS_EVALUATION_OUTPUT,
    n_elements_evaluation_times_evaluation=N_ELEMENTS_EVALUATION_TIMES_EVALUATION,
    point_doubling_twisted_curve=twisted_curve_operations.point_doubling,
    point_addition_twisted_curve=twisted_curve_operations.point_addition,
    point_negation_twisted_curve=twisted_curve_operations.point_negation,
    line_eval=line_functions.line_evaluation,
    line_eval_times_eval=miller_output_ops.line_eval_times_eval,
    line_eval_times_eval_times_eval=miller_output_ops.line_eval_times_eval_times_eval,
    line_eval_times_eval_times_eval_times_eval=miller_output_ops.line_eval_times_eval_times_eval_times_eval,
    line_eval_times_eval_times_eval_times_eval_times_eval_times_eval=miller_output_ops.line_eval_times_eval_times_eval_times_eval_times_eval_times_eval,
    line_eval_times_eval_times_miller_loop_output=miller_output_ops.line_eval_times_eval_times_miller_loop_output,
    miller_loop_output_square=miller_output_ops.square,
    miller_loop_output_mul=miller_output_ops.mul,
    miller_loop_output_times_eval=miller_output_ops.miller_loop_output_times_eval,
    miller_loop_output_times_eval_times_eval_times_eval=miller_output_ops.miller_loop_output_times_eval_times_eval_times_eval,
    miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval=miller_output_ops.miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval,
    pad_eval_times_eval_to_miller_output=pad_eval_times_eval_to_miller_output(),
    pad_eval_times_eval_times_eval_times_eval_to_miller_output=Script(),
    cyclotomic_inverse=final_exponentiation.cyclotomic_inverse,
    easy_exponentiation_with_inverse_check=final_exponentiation.easy_exponentiation_with_inverse_check,
    hard_exponentiation=final_exponentiation.hard_exponentiation,
)
