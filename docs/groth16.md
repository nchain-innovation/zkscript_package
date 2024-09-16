# Groth16

Leveraging the `PairingModel`, see docs on [pairing](./bilinear_pairings.md), we define a Groth16 class which, for any given `PairingModel`, construct the script that verifies a Groth16 zk proof.

Given a `PairingModel`, building the Groth16 object is very easy

```python
# Import the Groth16 class
from src.zkscript.groth16.model.groth16 import Groth16
# Import the PairingModel instantiations
from src.zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381 as bls12_381_pairing_model
# Import some auxiliary parameters
from src.zkscript.bilinear_pairings.bls12_381.parameters import a, r

bls12_381 = Groth16(
    pairing_model=bls12_381_pairing_model,
    curve_a=a,
    r=r
)

# The following is the script that verifies a Groth16 zk proof over BLS12-381 with 3 public inputs
bls12_381_groth16_verifier = bls12_381.groth16_verifier(
    modulo_threshold = 1,
    alpha_beta = [0] * 12,                      # Dummy pairing e(alpha,beta)
    minus_gamma = [[0,0],[0,0]],                # Dummy element -gamma in G2
    minus_delta = [[0,0],[0,0]],                # Dummy element -delta in G2
    gamma_abc = [[0,0],[0,0],[0,0],[0,0]],      # Dummy elements gamma_abc in G1
    check_constant = True,
    clean_constant = True,
)
```