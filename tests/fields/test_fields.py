from dataclasses import dataclass

import pytest
from elliptic_curves.fields.cubic_extension import CubicExtension
from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.fields.quadratic_extension import QuadraticExtension
from tx_engine import Context

from src.zkscript.fields.fq2 import Fq2 as Fq2Script
from src.zkscript.fields.fq2_over_2_residue_equal_u import Fq2Over2ResidueEqualU as Fq2Over2ResidueEqualUScript
from src.zkscript.fields.fq3 import Fq3 as Fq3Script
from src.zkscript.fields.fq4 import Fq4 as Fq4Script
from src.zkscript.fields.fq6_3_over_2 import Fq6 as Fq6Script
from src.zkscript.fields.fq12_2_over_3_over_2 import Fq12 as Fq12Script
from src.zkscript.fields.fq12_3_over_2_over_2 import Fq12Cubic as Fq12CubicScript
from src.zkscript.util.utility_scripts import nums_to_script
from tests.fields.util import check_constant, generate_unlock, generate_verify, save_scripts


@dataclass
class Fq2ResidueMinusOne:
    # Define Fq and Fq2
    q = 19
    Fq = PrimeField(q)
    non_residue = Fq(-1)
    Fq2 = QuadraticExtension(base_field=Fq, non_residue=non_residue)
    # Define script run in tests
    test_script = Fq2Script(q=q, non_residue=non_residue.to_int())
    # Define filename for saving scripts
    filename = "fq2_non_residue_is_minus_one"

    test_data = {
        "test_addition": [
            {"x": [5, 10], "y": [2, -11], "expected": [7, 18], "positive_modulo": True},
            {"x": [5, 10], "y": [2, -11], "expected": [7, -1], "positive_modulo": False},
        ],
        "test_subtraction": [
            {"x": [5, 10], "y": [2, 11], "expected": [3, 18], "positive_modulo": True},
            {"x": [5, 10], "y": [2, 11], "expected": [3, -1], "positive_modulo": False},
        ],
        "test_negation": [
            {"x": [5, 10], "expected": [14, 9], "positive_modulo": True},
            {"x": [5, 10], "expected": [-5, -10], "positive_modulo": False},
        ],
        "test_base_field_scalar_mul": [
            {"x": [5, -10], "y": [2], "expected": [10, 18], "positive_modulo": True},
            {"x": [5, -10], "y": [2], "expected": [10, -1], "positive_modulo": False},
        ],
        "test_mul": [
            {"x": [3, 2], "y": [-6, 7], "expected": [6, 9], "positive_modulo": True},
            {"x": [3, 2], "y": [6, -7], "expected": [-6, -9], "positive_modulo": False},
        ],
        "test_square": [
            {"x": [1, -1], "expected": [0, 17], "positive_modulo": True},
            {"x": [1, -1], "expected": [0, -2], "positive_modulo": False},
        ],
        "test_cube": [
            {"x": [1, -1], "expected": [17, 17], "positive_modulo": True},
            {"x": [1, -1], "expected": [17, -2], "positive_modulo": False},
            {"x": [1, -3], "expected": [12, 18], "positive_modulo": True},
            {"x": [1, -3], "expected": [12, -1], "positive_modulo": False},
        ],
        "test_add_three": [
            {"x": [1, 2], "y": [-12, -3], "z": [18, -5], "expected": [7, 13], "positive_modulo": True},
            {"x": [1, 2], "y": [-12, -3], "z": [18, -5], "expected": [7, -6], "positive_modulo": False},
        ],
        "test_conjugate": [
            {"x": [5, 10], "expected": [5, 9], "positive_modulo": True},
            {"x": [5, 10], "expected": [5, -10], "positive_modulo": False},
        ],
        "test_mul_by_u": [
            {"x": [5, -10], "expected": [10, 5], "positive_modulo": True},
            {"x": [5, -10], "expected": [-9, 5], "positive_modulo": False},
        ],
        "test_mul_by_one_plus_u": [
            {"x": [5, -10], "expected": [15, 14], "positive_modulo": True},
            {"x": [5, -10], "expected": [-4, -5], "positive_modulo": False},
        ],
    }


@dataclass
class Fq2ResidueNotMinusOne:
    # Define Fq and Fq2
    q = 19
    Fq = PrimeField(q)
    non_residue = Fq(3)
    Fq2 = QuadraticExtension(base_field=Fq, non_residue=non_residue)
    # Define script run in tests
    test_script = Fq2Script(q=q, non_residue=non_residue.to_int())
    # Define filename for saving scripts
    filename = "fq2_non_residue_is_not_minus_one"

    test_data = {
        "test_addition": [
            {"x": [5, 10], "y": [2, -11], "expected": [7, 18], "positive_modulo": True},
            {"x": [5, 10], "y": [2, -11], "expected": [7, -1], "positive_modulo": False},
        ],
        "test_subtraction": [
            {"x": [5, 10], "y": [2, 11], "expected": [3, 18], "positive_modulo": True},
            {"x": [5, 10], "y": [2, 11], "expected": [3, -1], "positive_modulo": False},
        ],
        "test_negation": [
            {"x": [5, 10], "expected": [14, 9], "positive_modulo": True},
            {"x": [5, 10], "expected": [-5, -10], "positive_modulo": False},
        ],
        "test_base_field_scalar_mul": [
            {"x": [5, -10], "y": [2], "expected": [10, 18], "positive_modulo": True},
            {"x": [5, -10], "y": [2], "expected": [10, -1], "positive_modulo": False},
        ],
        "test_mul": [
            {"x": [3, 2], "y": [-6, 7], "expected": [5, 9], "positive_modulo": True},
            {"x": [3, 2], "y": [6, -7], "expected": [-5, -9], "positive_modulo": False},
        ],
        "test_square": [
            {"x": [1, -1], "expected": [4, 17], "positive_modulo": True},
            {"x": [1, -1], "expected": [4, -2], "positive_modulo": False},
        ],
        "test_cube": [
            {"x": [1, -1], "expected": [10, -6], "positive_modulo": False},
            {"x": [1, -1], "expected": [10, 13], "positive_modulo": True},
            {"x": [1, -3], "expected": [6, 5], "positive_modulo": True},
            {"x": [1, -3], "expected": [6, -14], "positive_modulo": False},
        ],
        "test_add_three": [
            {"x": [1, 2], "y": [-12, -3], "z": [18, -5], "expected": [7, 13], "positive_modulo": True},
            {"x": [1, 2], "y": [-12, -3], "z": [18, -5], "expected": [7, -6], "positive_modulo": False},
        ],
        "test_conjugate": [
            {"x": [5, 10], "expected": [5, 9], "positive_modulo": True},
            {"x": [5, 10], "expected": [5, -10], "positive_modulo": False},
        ],
        "test_mul_by_u": [
            {"x": [5, -10], "expected": [8, 5], "positive_modulo": True},
            {"x": [5, -10], "expected": [-11, 5], "positive_modulo": False},
        ],
        "test_mul_by_one_plus_u": [
            {"x": [5, -10], "expected": [13, 14], "positive_modulo": True},
            {"x": [5, -10], "expected": [-6, -5], "positive_modulo": False},
        ],
    }


@dataclass
class Fq3:
    # Define Fq and Fq2
    q = 19
    Fq = PrimeField(q)
    non_residue = Fq(3)
    Fq3 = CubicExtension(base_field=Fq, non_residue=non_residue)
    # Define script run in tests
    test_script = Fq3Script(q=q, non_residue=non_residue.to_int())
    # Define filename for saving scripts
    filename = "fq3"

    test_data = {
        "test_addition": [
            {"x": [5, 10, 7], "y": [2, -11, 8], "expected": [7, 18, 15], "positive_modulo": True},
            {"x": [5, 10, 7], "y": [2, -11, 8], "expected": [7, -1, 15], "positive_modulo": False},
        ],
        "test_subtraction": [
            {"x": [5, 10, 7], "y": [2, 11, 8], "expected": [3, 18, 18], "positive_modulo": True},
            {"x": [5, 10, 7], "y": [2, 11, 8], "expected": [3, -1, -1], "positive_modulo": False},
        ],
        "test_base_field_scalar_mul": [
            {"x": [5, -10, 11], "y": [2], "expected": [10, 18, 3], "positive_modulo": True},
            {"x": [5, -10, -11], "y": [2], "expected": [10, -1, -3], "positive_modulo": False},
        ],
        "test_mul": [
            {"x": [3, 2, 8], "y": [-6, 7, 10], "expected": [1, 2, 15], "positive_modulo": True},
            {"x": [3, 2, 8], "y": [6, -7, -10], "expected": [-1, -2, 4], "positive_modulo": False},
        ],
        "test_square": [
            {"x": [1, -1, 4], "expected": [15, 8, 9], "positive_modulo": True},
            {"x": [1, -1, 4], "expected": [-4, 8, 9], "positive_modulo": False},
        ],
    }


@dataclass
class Fq4:
    # Define Fq and Fq2
    q = 19
    Fq = PrimeField(q)
    NON_RESIDUE = Fq(2)
    Fq2 = QuadraticExtension(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq4, non_residue = 1 + u
    NON_RESIDUE_FQ2 = Fq2(Fq(1), Fq(1))
    Fq4 = QuadraticExtension(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define fq2_script
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_int(), mul_by_fq2_non_residue=Fq2Script.mul_by_one_plus_u)
    gammas_frobenius = []
    for j in range(1, 4):
        gammas_frobenius.append(NON_RESIDUE_FQ2.power((q**j - 1) // 2).to_list())
    # Define script run in tests
    test_script = Fq4Script(q=q, base_field=fq2_script, gammas_frobenius=gammas_frobenius)
    # Define filename for saving scripts
    filename = "fq4"

    test_data = {
        "test_addition": [
            {
                "x": [1, 1, 2, 3],
                "y": [1, 2, 3, -4],
                "expected": [2, 3, 5, 18],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3],
                "y": [1, 2, 3, -4],
                "expected": [2, 3, 5, -1],
                "positive_modulo": False,
            },
        ],
        "test_base_field_scalar_mul": [
            {"x": [1, 2, -2, -1], "lam": [10], "expected": [10, 1, 18, 9], "positive_modulo": True},
            {"x": [1, 2, -2, -1], "lam": [10], "expected": [10, 1, -1, -10], "positive_modulo": False},
        ],
        "test_scalar_mul_fq2": [
            {
                "x": [1, 2, -1, -2],
                "lam": [1, -1],
                "expected": [16, 1, 3, 18],
                "positive_modulo": True,
            },
            {
                "x": [1, 2, -1, -2],
                "lam": [1, -1],
                "expected": [-3, 1, 3, -1],
                "positive_modulo": False,
            },
        ],
        "test_mul": [
            {
                "x": [8, 8, 8, -8],
                "y": [-2, 2, 2, 2],
                "expected": [0, 3, 0, 7],
                "positive_modulo": True,
            },
            {
                "x": [8, 8, 8, -8],
                "y": [-2, 2, 2, 2],
                "expected": [0, -16, 0, 7],
                "positive_modulo": False,
            },
        ],
        "test_square": [
            {
                "x": [1, -1, 2, -3],
                "expected": [1, 8, 16, 9],
                "positive_modulo": True,
            },
            {
                "x": [1, -1, 2, -3],
                "expected": [1, 8, 16, -10],
                "positive_modulo": False,
            },
        ],
        "test_add_three": [
            {
                "x": [1, 2, 4, 8],
                "y": [1, 2, -9, -18],
                "z": [-3, 2, 4, 5],
                "expected": [18, 6, 18, 14],
                "positive_modulo": True,
            },
            {
                "x": [1, 2, 4, 8],
                "y": [1, 2, -9, -18],
                "z": [-3, 2, 4, 5],
                "expected": [-1, 6, -1, -5],
                "positive_modulo": False,
            },
        ],
        "test_frobenius": [
            {
                "x": [1, 1, 2, 3],
                "expected": [1, 18, 11, 14],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3],
                "expected": [1, -1, -8, 14],
                "positive_modulo": False,
            },
        ],
        "test_frobenius_square": [
            {
                "x": [-10, -3, 5, 6],
                "expected": [9, 16, 14, 13],
                "positive_modulo": True,
            },
            {
                "x": [-10, -3, 5, 6],
                "expected": [-10, -3, 14, 13],
                "positive_modulo": False,
            },
        ],
        "test_frobenius_cube": [
            {
                "x": [-10, -3, 5, 6],
                "expected": [9, 3, 10, 13],
                "positive_modulo": True,
            },
            {
                "x": [-10, -3, 5, 6],
                "expected": [-10, 3, 10, -6],
                "positive_modulo": False,
            },
        ],
        "test_mul_by_u": [
            {
                "x": [-1, -2, 3, 4],
                "expected": [11, 7, 18, 17],
                "positive_modulo": True,
            },
            {
                "x": [-1, -2, 3, 4],
                "expected": [11, 7, -1, -2],
                "positive_modulo": False,
            },
        ],
        "test_conjugate": [
            {
                "x": [-1, -2, 3, 4],
                "expected": [18, 17, 16, 15],
                "positive_modulo": True,
            },
            {
                "x": [-1, -2, 3, 4],
                "expected": [-1, -2, -3, -4],
                "positive_modulo": False,
            },
        ],
    }


@dataclass
class Fq2Over2ResidueEqualU:
    # Define Fq and Fq2
    q = 19
    Fq = PrimeField(q)
    NON_RESIDUE = Fq(2)
    Fq2 = QuadraticExtension(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq2Over2ResidueEqualU
    NON_RESIDUE_FQ2 = Fq2.u()
    Fq2Over2ResidueEqualU = QuadraticExtension(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define fq2_script
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_int(), mul_by_fq2_non_residue=Fq2Script.mul_by_one_plus_u)
    gammas_frobenius = []
    for j in range(1, 4):
        gammas_frobenius.append(NON_RESIDUE_FQ2.power((q**j - 1) // 2).to_list())
    # Define script run in tests
    test_script = Fq2Over2ResidueEqualUScript(q=q, base_field=fq2_script, gammas_frobenius=gammas_frobenius)
    # Define filename for saving scripts
    filename = "fq2_over_2_residue_equal_u"

    test_data = {
        "test_square": [
            {
                "x": [1, -2, 3, -4],
                "expected": [18, 18, 0, 18],
                "positive_modulo": True,
            },
            {
                "x": [4, -2, -1, -3],
                "expected": [17, 3, 16, -1],
                "positive_modulo": False,
            },
            {
                "x": [1, 0, 0, 0],
                "expected": [1, 0, 0, 0],
                "positive_modulo": True,
            },
            {
                "x": [1, -1, -1, 1],
                "expected": [18, 1, 13, 4],
                "positive_modulo": True,
            },
            {
                "x": [1, -1, -1, 1],
                "expected": [-1, 1, -6, 4],
                "positive_modulo": False,
            },
        ],
        "test_mul": [
            {
                "x": [1, -2, 3, -4],
                "y": [5, 6, -3, -4],
                "expected": [0, 0, 18, 0],
                "positive_modulo": True,
            },
            {
                "x": [1, -2, 3, -4],
                "y": [5, 6, -3, -4],
                "expected": [0, 0, -1, 0],
                "positive_modulo": False,
            },
            {
                "x": [4, -2, -1, -3],
                "y": [5, 3, -3, -4],
                "expected": [15, 10, 0, 10],
                "positive_modulo": True,
            },
            {
                "x": [4, -2, -1, -3],
                "y": [5, 3, -3, -4],
                "expected": [15, 10, 0, -9],
                "positive_modulo": False,
            },
        ],
    }


@dataclass
class Fq6ThreeOverTwo:
    # Define Fq and Fq2
    q = 19
    Fq = PrimeField(q)
    NON_RESIDUE = Fq(3)
    Fq2 = QuadraticExtension(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq6
    NON_RESIDUE_FQ2 = Fq2(Fq(1), Fq(1))
    Fq6 = CubicExtension(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define fq2_script
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_int(), mul_by_fq2_non_residue=Fq2Script.mul_by_one_plus_u)
    # Define script run in tests
    test_script = Fq6Script(q=q, base_field=fq2_script)
    # Define filename for saving scripts
    filename = "fq6_3_over_2"

    test_data = {
        "test_addition": [
            {
                "x": [1, -3, 10, 18, -8, -1],
                "y": [4, 5, -13, -5, 8, 2],
                "expected": [5, 2, 16, 13, 0, 1],
                "positive_modulo": True,
            },
            {
                "x": [1, -3, 10, 18, -8, -1],
                "y": [4, 5, -13, -5, 8, 2],
                "expected": [5, 2, -3, 13, 0, 1],
                "positive_modulo": False,
            },
        ],
        "test_subtraction": [
            {
                "x": [1, -3, 10, 18, -8, -1],
                "y": [4, 5, -13, -5, 8, 2],
                "expected": [16, 11, 4, 4, 3, 16],
                "positive_modulo": True,
            },
            {
                "x": [1, -3, 10, 18, -8, -1],
                "y": [4, 5, -13, -5, 8, 2],
                "expected": [-3, -8, 4, 4, -16, -3],
                "positive_modulo": False,
            },
        ],
        "test_negation": [
            {"x": [1, -3, 10, 18, -8, -1], "expected": [18, 3, 9, 1, 8, 1], "positive_modulo": True},
            {"x": [1, -3, 10, 18, -8, -1], "expected": [-1, 3, -10, -18, 8, 1], "positive_modulo": False},
        ],
        "test_base_field_scalar_mul": [
            {
                "x": [1, -2, -3, 4, 5, -6],
                "lam": [4],
                "expected": [4, 11, 7, 16, 1, 14],
                "positive_modulo": True,
            },
            {
                "x": [1, -2, -3, 4, 5, -6],
                "lam": [4],
                "expected": [4, -8, -12, 16, 1, -5],
                "positive_modulo": False,
            },
        ],
        "test_scalar_mul_fq2": [
            {
                "x": [1, -2, -3, 4, 5, -6],
                "lam": [1, 3],
                "expected": (2, 1, 14, 14, 8, 9),
                "positive_modulo": True,
            },
            {
                "x": [1, -2, -3, 4, 5, -6],
                "lam": [1, 3],
                "expected": (-17, 1, 14, -5, -11, 9),
                "positive_modulo": False,
            },
        ],
        "test_mul": [
            {
                "x": [1, 3, -4, 5, -11, 9],
                "y": [0, 3, 9, -5, -10, 7],
                "expected": [17, 10, 16, 9, 4, 9],
                "positive_modulo": True,
            },
            {
                "x": [1, 3, -4, 5, -11, 9],
                "y": [0, 3, 9, -5, -10, 7],
                "expected": [17, -9, -3, 9, 4, 9],
                "positive_modulo": False,
            },
            {
                "x": [1, -1, -3, -4, 5, -6],
                "y": [0, 0, 1, 0, 0, 0],
                "expected": [6, 18, 1, 18, 16, 15],
                "positive_modulo": True,
            },
            {
                "x": [1, -1, -3, -4, 5, -6],
                "y": [0, 0, 1, 0, 0, 0],
                "expected": [-13, -1, 1, -1, -3, -4],
                "positive_modulo": False,
            },
        ],
        "test_square": [
            {
                "x": [1, 3, -5, -6, -9, 4],
                "expected": [7, 1, 4, 15, 16, 14],
                "positive_modulo": True,
            },
            {
                "x": [1, 3, -5, -6, -9, 4],
                "expected": [7, 1, -15, 15, 16, 14],
                "positive_modulo": False,
            },
        ],
    }


@dataclass
class Fq12TwoOverThreeOverTwo:
    # Define Fq and Fq2
    q = 19
    Fq = PrimeField(q)
    NON_RESIDUE = Fq(3)
    Fq2 = QuadraticExtension(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq6
    NON_RESIDUE_FQ2 = Fq2(Fq(1), Fq(1))
    Fq6 = CubicExtension(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define Fq12
    NON_RESIDUE_FQ6 = Fq6.v()
    Fq12 = QuadraticExtension(base_field=Fq6, non_residue=NON_RESIDUE_FQ6)
    # Define fq2_script
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_int(), mul_by_fq2_non_residue=Fq2Script.mul_by_one_plus_u)
    # Define fq6_script
    fq6_script = Fq6Script(q=q, base_field=fq2_script, mul_by_fq6_non_residue=Fq6Script.mul_by_v)
    # Define gammas for Frobenius
    gammas_frobenius = []
    for j in range(1, 12):
        inner_list = []
        for i in range(1, 6):
            inner_list.append(NON_RESIDUE_FQ2.power(i * (q**j - 1) // 6).to_list())
        gammas_frobenius.append(inner_list)
    # Define script run in tests
    test_script = Fq12Script(q=q, fq2=fq2_script, fq6=fq6_script, gammas_frobenius=gammas_frobenius)
    # Define filename for saving scripts
    filename = "fq12_2_over_3_over_2"

    test_data = {
        "test_mul": [
            {
                "x": [1, 1, 2, 3, 7, 11, 5, 3, 8, -2, 15, 6],
                "y": [1, 2, 3, 4, 8, -7, 1, -9, 5, -3, 11, -7],
                "expected": [0, 13, 1, 8, 8, 7, 7, 11, 1, 18, 15, 12],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3, 7, 11, 5, 3, 8, -2, 15, 6],
                "y": [1, 2, 3, 4, 8, -7, 1, -9, 5, -3, 11, -7],
                "expected": [0, -6, -18, -11, 8, -12, 7, 11, -18, -1, -4, 12],
                "positive_modulo": False,
            },
        ],
        "test_square": [
            {
                "x": [1, 1, 2, 3, 7, -8, 5, 3, 8, -2, -4, 6],
                "expected": [17, 6, 8, 12, 2, 0, 12, 8, 7, 10, 7, 6],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3, 7, -8, 5, 3, 8, -2, -4, 6],
                "expected": [17, 6, 8, 12, 2, 0, -7, 8, 7, -9, -12, 6],
                "positive_modulo": False,
            },
        ],
        "test_conjugate": [
            {
                "x": [1, 1, 2, 3, 7, 11, 5, 3, 8, 17, 15, 6],
                "expected": [1, 1, 2, 3, 7, 11, 14, 16, 11, 2, 4, 13],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3, 7, 11, 5, 3, 8, 17, 15, 6],
                "expected": [1, 1, 2, 3, 7, 11, -5, -3, -8, -17, -15, -6],
                "positive_modulo": False,
            },
        ],
        "test_frobenius": [
            {
                "x": [1, 1, 2, 3, 7, 11, -14, -16, -12, -2, -4, -13],
                "expected": [1, 18, 1, 15, 0, 9, 15, 0, 3, 4, 2, 11],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3, 7, 11, -14, -16, -12, -2, -4, -13],
                "expected": [1, -1, -18, -4, 0, -10, 15, 0, 3, -15, 2, -8],
                "positive_modulo": False,
            },
        ],
        "test_frobenius_square": [
            {
                "x": [1, 1, 2, 3, 7, 11, -14, -16, -12, -2, -4, -13],
                "expected": [1, 1, 14, 2, 1, 7, 17, 14, 7, 17, 10, 4],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3, 7, 11, -14, -16, -12, -2, -4, -13],
                "expected": [1, 1, 14, 2, 1, 7, -2, -5, -12, -2, -9, -15],
                "positive_modulo": False,
            },
        ],
        "test_frobenius_cube": [
            {
                "x": [1, 1, 2, 3, 7, 11, -14, -16, -12, -2, -4, -13],
                "expected": [1, 18, 7, 10, 0, 4, 13, 0, 3, 4, 14, 1],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3, 7, 11, -14, -16, -12, -2, -4, -13],
                "expected": [1, -1, -12, -9, 0, -15, 13, 0, 3, -15, 14, -18],
                "positive_modulo": False,
            },
        ],
    }


@dataclass
class Fq12ThreeOverTwoOverTwo:
    # Define Fq and Fq2
    q = 19
    Fq = PrimeField(q)
    NON_RESIDUE = Fq(2)
    Fq2 = QuadraticExtension(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq4
    NON_RESIDUE_FQ2 = Fq2(Fq(1), Fq(1))
    Fq4 = QuadraticExtension(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define Fq12
    NON_RESIDUE_FQ4 = Fq4.u()
    Fq12 = CubicExtension(base_field=Fq4, non_residue=NON_RESIDUE_FQ4)
    # Define fq2_script
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_int(), mul_by_fq2_non_residue=Fq2Script.mul_by_one_plus_u)
    # Define fq4_script
    fq4_script = Fq4Script(q=q, base_field=fq2_script, mul_by_fq4_non_residue=Fq4Script.mul_by_u)
    # Define script run in tests
    test_script = Fq12CubicScript(q=q, fq4=fq4_script)
    # Define filename for saving scripts
    filename = "fq12_3_over_2_over_2"

    test_data = {
        "test_mul": [
            {
                "x": [1, 1, 2, 4, 8, 12, -18, -9, -14, -3, 11, 12],
                "y": [1, 1, 2, 3, 7, 11, -14, -16, 8, -2, -4, 6],
                "expected": [8, 14, 3, 9, 15, 17, 11, 11, 12, 10, 13, 18],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 4, 8, 12, -18, -9, -14, -3, 11, 12],
                "y": [1, 1, 2, 3, 7, 11, -14, -16, 8, -2, -4, 6],
                "expected": [8, 14, -16, -10, -4, -2, 11, 11, 12, 10, -6, -1],
                "positive_modulo": False,
            },
        ],
        "test_square": [
            {
                "x": [1, 1, 2, 3, -12, -8, -14, -16, 8, 17, -4, -13],
                "expected": [0, 1, 11, 17, 6, 1, 18, 15, 2, 10, 17, 6],
                "positive_modulo": True,
            },
            {
                "x": [1, 1, 2, 3, -12, -8, -14, -16, 8, 17, -4, -13],
                "expected": [0, -18, 11, 17, -13, -18, 18, 15, 2, 10, 17, 6],
                "positive_modulo": False,
            },
        ],
    }


def extract_test_case(config, data):
    x_in_data = "x" in data
    y_in_data = "y" in data
    z_in_data = "z" in data
    lam_in_data = "lam" in data

    test = None

    if x_in_data and not y_in_data and not z_in_data and not lam_in_data:
        test = (config, data["positive_modulo"], data["x"], data["expected"])
    elif x_in_data and y_in_data and not z_in_data and not lam_in_data:
        test = (config, data["positive_modulo"], data["x"], data["y"], data["expected"])
    elif x_in_data and y_in_data and z_in_data and not lam_in_data:
        test = (config, data["positive_modulo"], data["x"], data["y"], data["z"], data["expected"])
    elif x_in_data and not y_in_data and not z_in_data and lam_in_data:
        test = (config, data["positive_modulo"], data["x"], data["lam"], data["expected"])

    return test


def generate_test_cases(test_name):
    # Parse and return config and the test_data for each config
    configurations = [
        Fq2ResidueMinusOne,
        Fq2ResidueNotMinusOne,
        Fq3,
        Fq4,
        Fq2Over2ResidueEqualU,
        Fq6ThreeOverTwo,
        Fq12TwoOverThreeOverTwo,
        Fq12ThreeOverTwoOverTwo,
    ]

    test_cases = [
        extract_test_case(config, test_data)
        for config in configurations
        if test_name in config.test_data
        for test_data in config.test_data[test_name]
    ]

    # Remove any None values returned by extract_test_case
    return [case for case in test_cases if case]


def verify_script(lock, unlock, clean_constant):
    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert context.get_altstack().size() == 0

    if clean_constant:
        assert context.get_stack().size() == 1
    else:
        assert context.get_stack().size() == 2


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "y", "expected"), generate_test_cases("test_addition"))
def test_addition(config, positive_modulo, x, y, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    lock = config.test_script.add(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "addition")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "y", "expected"), generate_test_cases("test_subtraction"))
def test_subtraction(config, positive_modulo, x, y, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    lock = config.test_script.subtract(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "subtraction")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_negation"))
def test_negation(config, positive_modulo, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.negate(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "negation")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "y", "expected"), generate_test_cases("test_mul"))
def test_mul(config, positive_modulo, x, y, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    lock = config.test_script.mul(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "multiplication")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_square"))
def test_square(config, positive_modulo, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.square(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "square")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize("scalar", [1, -1, 6, -6, 9, -9, 2, -2])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_cube"))
def test_cube(config, positive_modulo, x, expected, clean_constant, is_constant_reused, scalar, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.cube(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
        scalar=scalar,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    expected = [i * scalar for i in expected]
    expected = [i % config.q if positive_modulo or i > 0 else (i % config.q) - config.q for i in expected]

    lock += generate_verify(expected)
    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "cube")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(
    ("config", "positive_modulo", "x", "y", "z", "expected"), generate_test_cases("test_add_three")
)
def test_add_three(config, positive_modulo, x, y, z, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)
    unlock += generate_unlock(z)
    lock = config.test_script.add_three(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "add three")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_conjugate"))
def test_conjugate(config, positive_modulo, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.conjugate(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "conjugate")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_mul_by_u"))
def test_mul_by_u(config, positive_modulo, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.mul_by_u(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "multiplication by u")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_mul_by_one_plus_u"))
def test_mul_by_one_plus_u(
    config, positive_modulo, x, expected, clean_constant, is_constant_reused, save_to_json_folder
):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.mul_by_one_plus_u(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "multiplication by one plus u")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(
    ("config", "positive_modulo", "x", "lam", "expected"), generate_test_cases("test_base_field_scalar_mul")
)
def test_base_field_scalar_mul(
    config, positive_modulo, x, lam, expected, clean_constant, is_constant_reused, save_to_json_folder
):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(lam)

    lock = config.test_script.base_field_scalar_mul(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "scalar multiplication fq")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(
    ("config", "positive_modulo", "x", "lam", "expected"), generate_test_cases("test_scalar_mul_fq2")
)
def test_scalar_mul_fq2(
    config, positive_modulo, x, lam, expected, clean_constant, is_constant_reused, save_to_json_folder
):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(lam)
    lock = config.test_script.scalar_mul(
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "scalar multiplication fq2")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_frobenius"))
def test_frobenius(config, positive_modulo, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.frobenius_odd(
        n=1,
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "frobenius")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_frobenius_square"))
def test_frobenius_square(
    config, positive_modulo, x, expected, clean_constant, is_constant_reused, save_to_json_folder
):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.frobenius_even(
        n=2,
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "frobenius square")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "positive_modulo", "x", "expected"), generate_test_cases("test_frobenius_cube"))
def test_frobenius_cube(config, positive_modulo, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.frobenius_odd(
        n=3,
        take_modulo=True,
        positive_modulo=positive_modulo,
        check_constant=True,
        clean_constant=clean_constant,
        is_constant_reused=is_constant_reused,
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "frobenius cube")
