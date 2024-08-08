# Find correct paths
import os
import sys

root = os.path.normpath(os.path.join(os.path.dirname(__file__),'../../../')) # root
sys.path.append(root)

from zkscript.groth16.model.groth16 import Groth16

from zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381 as bls12_381_pairing_model
from zkscript.bilinear_pairings.bls12_381.parameters import a, r

bls12_381 = Groth16(
    pairing_model=bls12_381_pairing_model,
    curve_a=a,
    r=r
)
