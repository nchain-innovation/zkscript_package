"""Import finite field arithmetic for MNT4-753."""

from src.zkscript.bilinear_pairings.mnt4_753.parameters import GAMMAS, NON_RESIDUE_FQ, q
from src.zkscript.fields.fq import Fq
from src.zkscript.fields.fq2 import Fq2
from src.zkscript.fields.fq2_over_2_residue_equal_u import Fq2Over2ResidueEqualU

# Fq implementation
fq_script = Fq(q=q)
# Fq2 implementation
fq2_script = Fq2(q=q, non_residue=NON_RESIDUE_FQ, mul_by_fq2_non_residue=Fq2.mul_by_u)
# Fq4 implementation
fq4_script = Fq2Over2ResidueEqualU(q=q, base_field=fq2_script, gammas_frobenius=GAMMAS)
