from dataclasses import dataclass

import pytest
from elliptic_curves.fields.cubic_extension import cubic_extension_from_base_field_and_non_residue
from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.fields.quadratic_extension import quadratic_extension_from_base_field_and_non_residue
from tx_engine import Context

from src.zkscript.fields.fq2 import Fq2 as Fq2Script
from src.zkscript.fields.fq2 import Fq2 as Fq2ScriptModel
from src.zkscript.fields.fq2 import fq2_for_towering
from src.zkscript.fields.fq2_over_2_residue_equal_u import Fq2Over2ResidueEqualU as Fq2Over2ResidueEqualUScript
from src.zkscript.fields.fq4 import Fq4 as Fq4Script
from src.zkscript.fields.fq4 import Fq4 as Fq4ScriptModel
from src.zkscript.fields.fq4 import fq4_for_towering
from src.zkscript.fields.fq6_3_over_2 import Fq6 as Fq6Script
from src.zkscript.fields.fq6_3_over_2 import Fq6 as Fq6ScriptModel
from src.zkscript.fields.fq6_3_over_2 import fq6_for_towering
from src.zkscript.fields.fq12_2_over_3_over_2 import Fq12 as Fq12Script
from src.zkscript.fields.fq12_3_over_2_over_2 import Fq12Cubic as Fq12CubicScript
from src.zkscript.util.utility_scripts import nums_to_script
from tests.fields.util import check_constant, generate_unlock, generate_verify, save_scripts


@dataclass
class Fq2ResidueMinusOne:
    # Define Fq and Fq2
    q = 19
    Fq = base_field_from_modulus(q=q)
    non_residue = Fq(-1)
    Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq, non_residue=non_residue)
    # Define script run in tests
    test_script = Fq2Script(q=q, non_residue=non_residue.to_list()[0])
    # Define filename for saving scripts
    filename = "fq2_non_residue_is_minus_one"

    test_data = {
        "test_addition": [{"x": Fq2(Fq(5), Fq(10)), "y": Fq2(Fq(2), Fq(10)), "expected": Fq2(Fq(7), Fq(1))}],
        "test_subtraction": [{"x": Fq2(Fq(5), Fq(10)), "y": Fq2(Fq(2), Fq(10)), "expected": Fq2(Fq(3), Fq(0))}],
        "test_negation": [{"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(-5), Fq(-10))}],
        "test_scalar_mul": [{"x": Fq2(Fq(5), Fq(10)), "y": Fq(2), "expected": Fq2(Fq(10), Fq(1))}],
        "test_mul": [
            {"x": Fq2(Fq(5), Fq(10)), "y": Fq2(Fq(2), Fq(10)), "expected": Fq2(Fq(5), Fq(10)) * Fq2(Fq(2), Fq(10))}
        ],
        "test_square": [{"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(5), Fq(10)).power(2)}],
        "test_add_three": [
            {"x": Fq2(Fq(5), Fq(10)), "y": Fq2(Fq(2), Fq(10)), "z": Fq2(Fq(7), Fq(4)), "expected": Fq2(Fq(14), Fq(5))}
        ],
        "test_conjugate": [{"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(5), Fq(9))}],
        "test_mul_by_u": [{"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(5), Fq(10)) * Fq2.u()}],
        "test_mul_by_one_plus_u": [
            {"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(5), Fq(10)) * (Fq2.identity() + Fq2.u())}
        ],
    }


@dataclass
class Fq2ResidueNotMinusOne:
    # Define Fq and Fq2
    q = 19
    Fq = base_field_from_modulus(q=q)
    non_residue = Fq(3)
    Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq, non_residue=non_residue)
    # Define script run in tests
    test_script = Fq2Script(q=q, non_residue=non_residue.to_list()[0])
    # Define filename for saving scripts
    filename = "fq2_non_residue_is_not_minus_one"

    test_data = {
        "test_addition": [{"x": Fq2(Fq(5), Fq(10)), "y": Fq2(Fq(2), Fq(10)), "expected": Fq2(Fq(7), Fq(1))}],
        "test_subtraction": [{"x": Fq2(Fq(5), Fq(10)), "y": Fq2(Fq(2), Fq(10)), "expected": Fq2(Fq(3), Fq(0))}],
        "test_negation": [{"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(-5), Fq(-10))}],
        "test_scalar_mul": [{"x": Fq2(Fq(5), Fq(10)), "y": Fq(2), "expected": Fq2(Fq(10), Fq(1))}],
        "test_mul": [
            {"x": Fq2(Fq(5), Fq(10)), "y": Fq2(Fq(2), Fq(10)), "expected": Fq2(Fq(5), Fq(10)) * Fq2(Fq(2), Fq(10))}
        ],
        "test_square": [{"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(5), Fq(10)).power(2)}],
        "test_add_three": [
            {"x": Fq2(Fq(5), Fq(10)), "y": Fq2(Fq(2), Fq(10)), "z": Fq2(Fq(7), Fq(4)), "expected": Fq2(Fq(14), Fq(5))}
        ],
        "test_conjugate": [{"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(5), Fq(9))}],
        "test_mul_by_u": [{"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(5), Fq(10)) * Fq2.u()}],
        "test_mul_by_one_plus_u": [
            {"x": Fq2(Fq(5), Fq(10)), "expected": Fq2(Fq(5), Fq(10)) * (Fq2.identity() + Fq2.u())}
        ],
    }


@dataclass
class Fq4:
    # Define Fq and Fq2
    q = 19
    Fq = base_field_from_modulus(q=q)
    NON_RESIDUE = Fq(2)
    Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq4, non_residue = 1 + u
    NON_RESIDUE_FQ2 = Fq2(Fq(1), Fq(1))
    Fq4 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define fq2_script
    Fq2Script = fq2_for_towering(mul_by_non_residue=Fq2ScriptModel.mul_by_one_plus_u)
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_list()[0])
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
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "y": Fq4(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4))),
                "expected": Fq4(Fq2(Fq(2), Fq(3)), Fq2(Fq(5), Fq(7))),
            }
        ],
        "test_scalar_mul_fq": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "lam": Fq(10),
                "expected": Fq4(Fq2(Fq(10), Fq(10)), Fq2(Fq(1), Fq(11))),
            }
        ],
        "test_scalar_mul_fq2": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "lam": Fq2(Fq(2), Fq(3)),
                "expected": Fq2(Fq(2), Fq(3)) * Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
            }
        ],
        "test_mul": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "y": Fq4(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4))),
                "expected": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))) * Fq4(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4))),
            }
        ],
        "test_square": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "expected": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))) * Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
            }
        ],
        "test_add_three": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "y": Fq4(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4))),
                "z": Fq4(Fq2(Fq(4), Fq(7)), Fq2(Fq(1), Fq(2))),
                "expected": Fq4(Fq2(Fq(6), Fq(10)), Fq2(Fq(6), Fq(9))),
            }
        ],
        "test_frobenius": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "expected": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))).frobenius(1),
            }
        ],
        "test_frobenius_square": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "expected": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))).frobenius(2),
            }
        ],
        "test_frobenius_cube": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "expected": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))).frobenius(3),
            }
        ],
        "test_mul_by_u": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "expected": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))) * Fq4.u(),
            }
        ],
        "test_conjugate": [
            {
                "x": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "expected": Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))).conjugate(),
            }
        ],
    }


@dataclass
class Fq2Over2ResidueEqualU:
    # Define Fq and Fq2
    q = 19
    Fq = base_field_from_modulus(q=q)
    NON_RESIDUE = Fq(2)
    Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq2Over2ResidueEqualU
    NON_RESIDUE_FQ2 = Fq2.u()
    Fq2Over2ResidueEqualU = quadratic_extension_from_base_field_and_non_residue(
        base_field=Fq2, non_residue=NON_RESIDUE_FQ2
    )
    # Define fq2_script
    Fq2Script = fq2_for_towering(mul_by_non_residue=Fq2ScriptModel.mul_by_one_plus_u)
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_list()[0])
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
                "x": Fq2Over2ResidueEqualU(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                "expected": Fq2Over2ResidueEqualU(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)))
                * Fq2Over2ResidueEqualU(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
            },
            {
                "x": Fq2Over2ResidueEqualU(Fq2(Fq(18), Fq(18)), Fq2(Fq(12), Fq(13))),
                "expected": Fq2Over2ResidueEqualU(Fq2(Fq(18), Fq(18)), Fq2(Fq(12), Fq(13)))
                * Fq2Over2ResidueEqualU(Fq2(Fq(18), Fq(18)), Fq2(Fq(12), Fq(13))),
            },
            {
                "x": Fq2Over2ResidueEqualU.identity(),
                "expected": Fq2Over2ResidueEqualU.identity(),
            },
            {
                "x": Fq2Over2ResidueEqualU.zero(),
                "expected": Fq2Over2ResidueEqualU.zero(),
            },
            {
                "x": Fq2Over2ResidueEqualU.u(),
                "expected": Fq2Over2ResidueEqualU.u() * Fq2Over2ResidueEqualU.u(),
            },
        ],
        "test_mul": [
            {
                "x": Fq2Over2ResidueEqualU(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4))),
                "y": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(1)), Fq2(Fq(4), Fq(3))),
                "expected": Fq2Over2ResidueEqualU(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4)))
                * Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(1)), Fq2(Fq(4), Fq(3))),
            },
            {
                "x": Fq2Over2ResidueEqualU(Fq2(Fq(0), Fq(3)), Fq2(Fq(5), Fq(0))),
                "y": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(7)), Fq2(Fq(11), Fq(13))),
                "expected": Fq2Over2ResidueEqualU(Fq2(Fq(0), Fq(3)), Fq2(Fq(5), Fq(0)))
                * Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(7)), Fq2(Fq(11), Fq(13))),
            },
            {
                "x": Fq2Over2ResidueEqualU(Fq2(Fq(4), Fq(1)), Fq2(Fq(3), Fq(0))),
                "y": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(0)), Fq2(Fq(11), Fq(13))),
                "expected": Fq2Over2ResidueEqualU(Fq2(Fq(4), Fq(1)), Fq2(Fq(3), Fq(0)))
                * Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(0)), Fq2(Fq(11), Fq(13))),
            },
            {
                "x": Fq2Over2ResidueEqualU.identity(),
                "y": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(7)), Fq2(Fq(11), Fq(13))),
                "expected": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(7)), Fq2(Fq(11), Fq(13))),
            },
            {
                "x": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(7)), Fq2(Fq(11), Fq(13))),
                "y": Fq2Over2ResidueEqualU.u(),
                "expected": Fq2Over2ResidueEqualU.u() * Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(7)), Fq2(Fq(11), Fq(13))),
            },
            {
                "x": Fq2Over2ResidueEqualU.zero(),
                "y": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(7)), Fq2(Fq(11), Fq(13))),
                "expected": Fq2Over2ResidueEqualU.zero(),
            },
            {
                "x": Fq2Over2ResidueEqualU(Fq2(Fq(7), Fq(5)), Fq2.zero()),
                "y": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(1)), Fq2(Fq(11), Fq(3))),
                "expected": Fq2Over2ResidueEqualU(Fq2(Fq(7), Fq(5)), Fq2.zero())
                * Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(1)), Fq2(Fq(11), Fq(3))),
            },
            {
                "x": Fq2Over2ResidueEqualU(Fq2.zero(), Fq2(Fq(3), Fq(0))),
                "y": Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(0)), Fq2.identity()),
                "expected": Fq2Over2ResidueEqualU(Fq2.zero(), Fq2(Fq(3), Fq(0)))
                * Fq2Over2ResidueEqualU(Fq2(Fq(2), Fq(0)), Fq2.identity()),
            },
        ],
    }


@dataclass
class Fq6ThreeOverTwo:
    # Define Fq and Fq2
    q = 19
    Fq = base_field_from_modulus(q=q)
    NON_RESIDUE = Fq(3)
    Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq6
    NON_RESIDUE_FQ2 = Fq2(Fq(1), Fq(1))
    Fq6 = cubic_extension_from_base_field_and_non_residue(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define fq2_script
    Fq2Script = fq2_for_towering(mul_by_non_residue=Fq2ScriptModel.mul_by_one_plus_u)
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_list()[0])
    # Define script run in tests
    test_script = Fq6Script(q=q, base_field=fq2_script)
    # Define filename for saving scripts
    filename = "fq6_3_over_2"

    test_data = {
        "test_addition": [
            {
                "x": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                "y": Fq6(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4)), Fq2(Fq(8), Fq(12))),
                "expected": Fq6(Fq2(Fq(2), Fq(3)), Fq2(Fq(5), Fq(7)), Fq2(Fq(15), Fq(4))),
            }
        ],
        "test_subtraction": [
            {
                "x": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                "y": Fq6(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(9)), Fq2(Fq(2), Fq(4))),
                "expected": Fq6(Fq2(Fq(0), Fq(18)), Fq2(Fq(18), Fq(13)), Fq2(Fq(5), Fq(7))),
            }
        ],
        "test_negation": [
            {
                "x": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                "expected": Fq6(Fq2(Fq(18), Fq(18)), Fq2(Fq(17), Fq(16)), Fq2(Fq(12), Fq(8))),
            }
        ],
        "test_scalar_mul_fq": [
            {
                "x": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                "lam": Fq(10),
                "expected": Fq6(Fq2(Fq(10), Fq(10)), Fq2(Fq(1), Fq(11)), Fq2(Fq(13), Fq(15))),
            }
        ],
        "test_scalar_mul_fq2": [
            {
                "x": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                "lam": Fq2(Fq(2), Fq(3)),
                "expected": Fq2(Fq(2), Fq(3)) * Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
            }
        ],
        "test_mul": [
            {
                "x": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                "y": Fq6(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4)), Fq2(Fq(8), Fq(12))),
                "expected": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11)))
                * Fq6(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4)), Fq2(Fq(8), Fq(12))),
            }
        ],
        "test_square": [
            {
                "x": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                "expected": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))).power(2),
            }
        ],
        "test_mul_by_v": [
            {
                "x": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                "expected": Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))) * Fq6.v(),
            }
        ],
    }


@dataclass
class Fq12TwoOverThreeOverTwo:
    # Define Fq and Fq2
    q = 19
    Fq = base_field_from_modulus(q=q)
    NON_RESIDUE = Fq(3)
    Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq6
    NON_RESIDUE_FQ2 = Fq2(Fq(1), Fq(1))
    Fq6 = cubic_extension_from_base_field_and_non_residue(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define Fq12
    NON_RESIDUE_FQ6 = Fq6.v()
    Fq12 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq6, non_residue=NON_RESIDUE_FQ6)
    # Define fq2_script
    Fq2Script = fq2_for_towering(mul_by_non_residue=Fq2ScriptModel.mul_by_one_plus_u)
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_list()[0])
    # Define fq6_script
    Fq6Script = fq6_for_towering(mul_by_non_residue=Fq6ScriptModel.mul_by_v)
    fq6_script = Fq6Script(q=q, base_field=fq2_script)
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
                "x": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ),
                "y": Fq12(
                    Fq6(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4)), Fq2(Fq(8), Fq(12))),
                    Fq6(Fq2(Fq(1), Fq(10)), Fq2(Fq(5), Fq(16)), Fq2(Fq(11), Fq(12))),
                ),
                "expected": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                )
                * Fq12(
                    Fq6(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4)), Fq2(Fq(8), Fq(12))),
                    Fq6(Fq2(Fq(1), Fq(10)), Fq2(Fq(5), Fq(16)), Fq2(Fq(11), Fq(12))),
                ),
            }
        ],
        "test_square": [
            {
                "x": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ),
                "expected": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ).power(2),
            }
        ],
        "test_conjugate": [
            {
                "x": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ),
                "expected": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ).conjugate(),
            }
        ],
        "test_frobenius": [
            {
                "x": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ),
                "expected": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ).frobenius(1),
            }
        ],
        "test_frobenius_square": [
            {
                "x": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ),
                "expected": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ).frobenius(2),
            }
        ],
        "test_frobenius_cube": [
            {
                "x": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ),
                "expected": Fq12(
                    Fq6(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3)), Fq2(Fq(7), Fq(11))),
                    Fq6(Fq2(Fq(5), Fq(3)), Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ).frobenius(3),
            }
        ],
    }


@dataclass
class Fq12ThreeOverTwoOverTwo:
    # Define Fq and Fq2
    q = 19
    Fq = base_field_from_modulus(q=q)
    NON_RESIDUE = Fq(2)
    Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq, non_residue=NON_RESIDUE)
    # Define Fq4
    NON_RESIDUE_FQ2 = Fq2(Fq(1), Fq(1))
    Fq4 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq2, non_residue=NON_RESIDUE_FQ2)
    # Define Fq12
    NON_RESIDUE_FQ4 = Fq4.u()
    Fq12 = cubic_extension_from_base_field_and_non_residue(base_field=Fq4, non_residue=NON_RESIDUE_FQ4)
    # Define fq2_script
    Fq2Script = fq2_for_towering(mul_by_non_residue=Fq2ScriptModel.mul_by_one_plus_u)
    fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE.to_list()[0])
    # Define fq4_script
    Fq4Script = fq4_for_towering(mul_by_non_residue=Fq4ScriptModel.mul_by_u)
    fq4_script = Fq4Script(q=q, base_field=fq2_script)
    # Define script run in tests
    test_script = Fq12CubicScript(q=q, fq2=fq2_script, fq4=fq4_script)
    # Define filename for saving scripts
    filename = "fq12_3_over_2_over_2"

    test_data = {
        "test_mul": [
            {
                "x": Fq12(
                    x0=Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                    x1=Fq4(Fq2(Fq(7), Fq(11)), Fq2(Fq(5), Fq(3))),
                    x2=Fq4(Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ),
                "y": Fq12(
                    x0=Fq4(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4))),
                    x1=Fq4(Fq2(Fq(8), Fq(12)), Fq2(Fq(1), Fq(10))),
                    x2=Fq4(Fq2(Fq(5), Fq(16)), Fq2(Fq(11), Fq(12))),
                ),
                "expected": Fq12(
                    x0=Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                    x1=Fq4(Fq2(Fq(7), Fq(11)), Fq2(Fq(5), Fq(3))),
                    x2=Fq4(Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                )
                * Fq12(
                    x0=Fq4(Fq2(Fq(1), Fq(2)), Fq2(Fq(3), Fq(4))),
                    x1=Fq4(Fq2(Fq(8), Fq(12)), Fq2(Fq(1), Fq(10))),
                    x2=Fq4(Fq2(Fq(5), Fq(16)), Fq2(Fq(11), Fq(12))),
                ),
            }
        ],
        "test_square": [
            {
                "x": Fq12(
                    Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                    Fq4(Fq2(Fq(7), Fq(11)), Fq2(Fq(5), Fq(3))),
                    Fq4(Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ),
                "expected": Fq12(
                    Fq4(Fq2(Fq(1), Fq(1)), Fq2(Fq(2), Fq(3))),
                    Fq4(Fq2(Fq(7), Fq(11)), Fq2(Fq(5), Fq(3))),
                    Fq4(Fq2(Fq(8), Fq(17)), Fq2(Fq(15), Fq(6))),
                ).power(2),
            }
        ],
    }


def extract_test_case(config, data):
    x_in_data = "x" in data
    y_in_data = "y" in data
    z_in_data = "z" in data
    lam_in_data = "lam" in data

    test = None

    if x_in_data and not y_in_data and not z_in_data and not lam_in_data:
        test = (config, data["x"], data["expected"])
    elif x_in_data and y_in_data and not z_in_data and not lam_in_data:
        test = (config, data["x"], data["y"], data["expected"])
    elif x_in_data and y_in_data and z_in_data and not lam_in_data:
        test = (config, data["x"], data["y"], data["z"], data["expected"])
    elif x_in_data and not y_in_data and not z_in_data and lam_in_data:
        test = (config, data["x"], data["lam"], data["expected"])

    return test


def generate_test_cases(test_name):
    # Parse and return config and the test_data for each config
    configurations = [
        Fq2ResidueMinusOne,
        Fq2ResidueNotMinusOne,
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
    assert len(context.get_altstack()) == 0

    if clean_constant:
        assert len(context.get_stack()) == 1
    else:
        assert len(context.get_stack()) == 2


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "y", "expected"), generate_test_cases("test_addition"))
def test_addition(config, x, y, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    lock = config.test_script.add(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "addition")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "y", "expected"), generate_test_cases("test_subtraction"))
def test_subtraction(config, x, y, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    lock = config.test_script.subtract(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "subtraction")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "expected"), generate_test_cases("test_negation"))
def test_negation(config, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.negate(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "negation")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "y", "expected"), generate_test_cases("test_scalar_mul"))
def test_scalar_mul(config, x, y, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    lock = config.test_script.scalar_mul(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "scalar multiplication")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "y", "expected"), generate_test_cases("test_mul"))
def test_mul(config, x, y, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    lock = config.test_script.mul(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "multiplication")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "expected"), generate_test_cases("test_square"))
def test_square(config, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.square(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "square")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "y", "z", "expected"), generate_test_cases("test_add_three"))
def test_add_three(config, x, y, z, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)
    unlock += generate_unlock(z)

    lock = config.test_script.add_three(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "add three")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "expected"), generate_test_cases("test_conjugate"))
def test_conjugate(config, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.conjugate(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "conjugate")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "expected"), generate_test_cases("test_mul_by_u"))
def test_mul_by_u(config, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.mul_by_u(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "multiplication by u")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "expected"), generate_test_cases("test_mul_by_one_plus_u"))
def test_mul_by_one_plus_u(config, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.mul_by_one_plus_u(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "multiplication by one plus u")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "lam", "expected"), generate_test_cases("test_scalar_mul_fq"))
def test_scalar_mul_fq(config, x, lam, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(lam)

    lock = config.test_script.fq_scalar_mul(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "scalar multiplication fq")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "lam", "expected"), generate_test_cases("test_scalar_mul_fq2"))
def test_scalar_mul_fq2(config, x, lam, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(lam)

    lock = config.test_script.scalar_mul(
        take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "scalar multiplication fq2")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "expected"), generate_test_cases("test_frobenius"))
def test_frobenius(config, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.frobenius_odd(
        n=1, take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "frobenius")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "expected"), generate_test_cases("test_frobenius_square"))
def test_frobenius_square(config, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.frobenius_even(
        n=2, take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "frobenius square")


@pytest.mark.parametrize("clean_constant", [True, False])
@pytest.mark.parametrize("is_constant_reused", [True, False])
@pytest.mark.parametrize(("config", "x", "expected"), generate_test_cases("test_frobenius_cube"))
def test_frobenius_cube(config, x, expected, clean_constant, is_constant_reused, save_to_json_folder):
    unlock = nums_to_script([config.q])
    unlock += generate_unlock(x)

    lock = config.test_script.frobenius_odd(
        n=3, take_modulo=True, check_constant=True, clean_constant=clean_constant, is_constant_reused=is_constant_reused
    )
    if is_constant_reused:
        lock += check_constant(config.q)
    lock += generate_verify(expected)

    verify_script(lock, unlock, clean_constant)

    if save_to_json_folder and clean_constant and not is_constant_reused:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "frobenius cube")
