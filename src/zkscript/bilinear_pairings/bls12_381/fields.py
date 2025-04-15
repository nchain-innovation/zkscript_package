"""Import finite field arithmetic for BLS12-381."""

from types import MethodType

from tx_engine import Script

from src.zkscript.bilinear_pairings.bls12_381.parameters import GAMMAS, NON_RESIDUE_FQ, q
from src.zkscript.fields.fq2 import Fq2
from src.zkscript.fields.fq4 import Fq4
from src.zkscript.fields.fq6_3_over_2 import Fq6
from src.zkscript.fields.fq12_2_over_3_over_2 import Fq12
from src.zkscript.fields.fq12_3_over_2_over_2 import Fq12Cubic
from src.zkscript.util.utility_scripts import roll

# Fq2 implementation, NON_RESIDUE = -1
fq2_script = Fq2(q=q, non_residue=NON_RESIDUE_FQ, mul_by_fq2_non_residue=Fq2.mul_by_one_plus_u)
# Fq4 implementation, FQ2_NON_RESIDUE = u
fq4_script = Fq4(q=q, base_field=fq2_script, mul_by_fq4_non_residue=Fq4.mul_by_u)
# Fq6 implementation, FQ2_NON_RESIDUE = 1 + u
fq6_script = Fq6(q=q, base_field=fq2_script, mul_by_fq6_non_residue=Fq6.mul_by_v)
# Fq12 implementation, NON_RESIDUE_OVER_FQ6 = v
fq12_script = Fq12(q=q, fq2=fq2_script, fq6=fq6_script, gammas_frobenius=GAMMAS)


def to_quadratic(
    self,  # noqa: ARG001
) -> Script:
    """Convert an element of Fq12Cubic (cubic extension of F_q^4) to Fq12 (quadratic extension of F_q^6).

    Stack input:
        - stack:    [q, ..., x := ((a,b),(c,d),(e,f))], `x` is a triplet of elements of F_q^4
        - altstack: []

    Stack output:
        - stack:    [q, ..., x := ((a,e,d),(c,b,f))], `x` is a couple of elements of F_q^6
        - altstack: []

    Returns:
        Script to convert an element of Fq12Cubic to Fq12.

    Notes:
        The isomorphism is:
            Fq12Cubic = F_q^4[r] / (r^3 - s)
                = F_q[u,s,r] / (u^2 + 1, s^2 - xi, r^3 - s), xi = 1 + u
                = F_q[u,t] / (t^6 - xi)
                = F_q[u,v,w] / (u^2 + 1, v^3 - xi, w^2 - v)
                = F_q^6[w] / (w^2 - v)
                = Fq12
        Hence, we convert as follows: ((a,b),(c,d),(e,f)) --> ((a,e,d),(c,b,f))
    """
    out = Script()

    # After this, the stack is: b c d e f a
    out += roll(position=11, n_elements=2)

    # After this, the stack is b c d f a e
    out += Script.parse_string("OP_2ROT")

    # After this, the stack is b c f a e d
    out += roll(position=7, n_elements=2)

    # After this, the stack is b f a e d c
    out += roll(position=9, n_elements=2)

    # After this, the stack is f a e d c b
    out += roll(position=11, n_elements=2)

    # After this, the stack is a e d c b f
    out += roll(position=11, n_elements=2)

    return out


# Fq12Cubic implementation: FQ4_NON_RESIDUE = 1 + u
fq12cubic_script = Fq12Cubic(q=q, fq4=fq4_script)
fq12cubic_script.to_quadratic = MethodType(to_quadratic, fq12cubic_script)
