"""Export Groth16 verifier over BLS12-381."""

from src.zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381 as bls12_381_pairing_model
from src.zkscript.bilinear_pairings.bls12_381.parameters import a, r
from src.zkscript.groth16.model.groth16 import Groth16

bls12_381 = Groth16(pairing_model=bls12_381_pairing_model, curve_a=a, r=r)
