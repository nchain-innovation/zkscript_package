# Export finite field arithmetic for MNT4_753

# Find correct paths
import os
import sys

root = os.path.normpath(os.path.join(os.path.dirname(__file__),'../../../')) # root
sys.path.append(root)

from zkscript.bilinear_pairings.mnt4_753.parameters import *

from zkscript.fields.fq2 import Fq2 as Fq2ScriptModel, fq2_for_towering
from zkscript.fields.fq4 import Fq4 as Fq4ScriptModel

# Fq2 class
Fq2Script = fq2_for_towering(Fq2ScriptModel.mul_by_u)
# Fq2 implementation
fq2_script = Fq2Script(q=q,non_residue=NON_RESIDUE_FQ)
# Fq4 implementation
fq4_script = Fq4ScriptModel(
    q=q,
    base_field=fq2_script,
    gammas_frobenius=GAMMAS
)