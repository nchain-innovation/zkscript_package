# Find correct paths
import os
import sys

root = os.path.normpath(os.path.join(os.path.dirname(__file__),'../../../')) # root
sys.path.append(root)

from zkscript.groth16.model.groth16 import Groth16

from zkscript.bilinear_pairings.mnt4_753.mnt4_753 import mnt4_753 as mnt4_753_pairing_model
from zkscript.bilinear_pairings.mnt4_753.parameters import a, r

mnt4_753 = Groth16(
    pairing_model=mnt4_753_pairing_model,
    curve_a=a,
    r=r
)
