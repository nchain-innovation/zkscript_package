# Knowledge of square root

This folder contains the code required to generate a ZKP of the knowledge of the square root of a number. More precisely, the code contained in [src/main.rs](./src/main.rs) constructs:
- a circuit `C(x,w)` that is satisfied if and only if `w^2 = x mod p`, where `p` is a prime hard-coded in the circuit
- given the parameters in `parameters.json`, the code performs the setup of Groth16 for the circuit `C` and generates a proof for the values of `square` and `root` contained in `parameters.json`

To generate the data needed to run (script.py)[../script.py], it is enough to modify the parameters contained in [parameters.json](./parameters.json) and then execute the command `cargo run`. It is possible to choose over which curve the Groth16 setup should be executed by changing the type definitions in [src/main.rs#L35](./src/main.rs#L35)