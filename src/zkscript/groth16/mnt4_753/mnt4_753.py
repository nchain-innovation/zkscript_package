"""Export Groth16 verifier over MNT4-753."""

from src.zkscript.bilinear_pairings.mnt4_753.mnt4_753 import mnt4_753 as mnt4_753_pairing_model
from src.zkscript.bilinear_pairings.mnt4_753.parameters import a, r
from src.zkscript.groth16.model.groth16 import Groth16

mnt4_753 = Groth16(pairing_model=mnt4_753_pairing_model, curve_a=a, r=r)
