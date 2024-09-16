# Knowledge of SHA256 preimage

This folder contains the code required to generate a ZKP of the knowledge of the preimage of SHA256 hash. More precisely, the code contained in [src/main.rs](./src/main.rs) constructs:
- a circuit `C(x,w)` that is satisfied if and only if `SHA256(w) = x`
- given the parameters in `parameters.json`, the code performs the setup of Groth16 for the circuit `C` and generates a proof for the value of `preimage`

To generate the data needed to run (script.py)[../script.py], it is enough to modify the parameter contained in [parameters.json](./parameters.json) and then execute the command `cargo run`. 

**Note:** It is currently possible to perform the Groth16 setup only with `BLS12-381`.