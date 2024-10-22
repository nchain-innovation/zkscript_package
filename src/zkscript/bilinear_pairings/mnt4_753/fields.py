"""Import finite field arithmetic for MNT4-753."""
from src.zkscript.bilinear_pairings.mnt4_753.parameters import GAMMAS, NON_RESIDUE_FQ, q
from src.zkscript.fields.fq2 import Fq2 as Fq2ScriptModel
from src.zkscript.fields.fq2 import fq2_for_towering
from src.zkscript.fields.fq2_over_2_residue_equal_u import Fq2Over2ResidueEqualU

# Fq2 class
Fq2Script = fq2_for_towering(Fq2ScriptModel.mul_by_u)
# Fq2 implementation
fq2_script = Fq2Script(q=q, non_residue=NON_RESIDUE_FQ)
# Fq4 implementation
fq4_script = Fq2Over2ResidueEqualU(q=q, base_field=fq2_script, gammas_frobenius=GAMMAS)
