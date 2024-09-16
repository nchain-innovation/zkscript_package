# Bilinear pairings

The zk Script Library contains a model implementation of bilinear pairings. Namely, we have built script models for the `MillerLoop`, `TripleMillerLoop`, and `Pairing`, which can be used to instatiate bilinear pairings over any pairing-friendly curve, with the only overhead of having to define a `PairingModel` object.

*NOTE*: The current implementation only supports curves for which the bilinear pairing is computed with a single Miller loop, and which do not require further multiplications at the end of the Miller loop (e.g., BLS12 and MNT4 are supported).

A `PairingModel` object is defined by a the following series of attributes:
- `q`: the modulus over which the pairing-friendly curve is defined
- `exp_t_minus_one`: the signed binary decomposition of the trace minus one (the bits over which the Miller loop is executed)
- `extension_degree`: the extension degree of the field over which the twisted curve lives (equal to `EMBEDDING_DEGREE / TWIST_DEGREE`)
- `n_points_curve`: number of points needed to define a point on the curve
- `n_points_twist`: number of points needed to define a point on the twisted curve
- `n_elements_miller_output`: number of elements needed to define the output of the Miller loop
- `n_elements_evaluation_output`: number of elements needed to define the output of a line evaluation
- `n_elements_evaluation_times_evaluation`: number of elements needed to define the output of the product of two line evaluations
- `point_doubling_twisted_curve`: script implementing point doubling over the twisted curve
- `point_addition_twisted_curve`: script implementing point addition over the twisted curve
- `point_negation_twisted_curve`: script implementing point negation over the twisted curve
- `line_eval`: script implementing line evaluation
- `line_eval_times_eval`: script computing the product of two line evaluations
- `line_eval_times_eval_times_eval`: script computing the product `t1 * ev`, where `ev` is a line evaluation, and `t1 = ev * ev`
- `line_eval_times_eval_times_eval_times_eval`: script computing the product `t1 * t2`, where `t1 = ev * ev`, `t2 = ev * ev`
- `line_eval_times_eval_times_eval_times_eval_times_eval_times_eval`: script computing the product `t1 * t4`, where `t1 = ev * ev`, `t4 = t2 * t3`, `t2 = ev * ev`, `t3 = ev * ev`
- `line_eval_times_eval_times_miller_loop_output`: script computing the product `t1 * t2`, where `t1 = ev * ev`, `t2` is an element of the same type as the Miller output (i.e., an element in `Fqk`, where `k` is the `EMBEDDING_DEGREE`)
- `miller_loop_output_square`: script computing the square of an element `t1` in `Fqk`, where `k` is the `EMBEDDING_DEGREE`
- `miller_loop_output_mul`: script computing the product of two elements `t1`, `t2` in `Fqk`, where `k` is the `EMBEDDING_DEGREE`
- `miller_loop_output_times_eval`: script computing the product `t1 * ev`, where `t1` is an element in `Fqk`, where `k` is the `EMBEDDING_DEGREE`
- `miller_loop_output_times_eval_times_eval_times_eval`: script computing the product `t1 * t2`, where `t2 = ev * ev * ev` and `t1` is an element in `Fqk`, where `k` is the `EMBEDDING_DEGREE`
- `miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval`: script computing the product `t1 * t2`, where `t1` is an element in `Fqk`, where `k` is the `EMBEDDING_DEGREE`, and `t2 = (ev * ev * ev * ev * ev * ev)`
- `pad_eval_times_eval_to_miller_output`: script to pad a the product of two line evaluatios (which in principle it could be a sparse element) to an element in `Fqk`, where `k` is the `EMBEDDING_DEGREE`
- `pad_eval_times_eval_times_eval_times_eval_to_miller_output`: script to pad the product of four line evaluations (which in principle it could be a sparse element) to an element in `Fqk`, where `k` is the `EMBEDDING_DEGREE`
- `cyclotomic_inverse`: script to compute the cyclotomic inverse of an element `f` in `Fqk` which belongs to the cyclotomic subgroup, i.e., such that `f^{Phi_k(q)} = 1`
- `easy_exponentiation_with_inverse_check`: script to compute the easy part of the exponentiation, leveraging an inverse computed off-chain
- `hard_exponentiation`: script to compute the hard part of the exponentiation
- `miller_loop_implementation`: **NO DOCUMENTATION BECAUSE IT WILL BE REMOVED**
- `triple_miller_loop_implementation`: : **NO DOCUMENTATION BECAUSE IT WILL BE REMOVED**

Note that we are slightly abusing language here: when we write __script__ we really mean __function that outputs a script__. Each of these functions has a determined signature, and each script produced by these functions has a determined set of input data:
- **Function signatures**: all the functions take three parameters:
    - `take_modulo`: whether the script which is the output of the function takes the modulo at the end of script execution
    - `check_constant`: whether the script which is the output of the function checks if the constant used for modulo operations is the correct one
    - `clean_constant`: whether the script which is the output of the function cleans the constant used for modulo operations
- **Script input**: below is a table explaining the input expected by each input (note if `q` does not need to be added each time the script is executed, it can be loaded in the unlocking script and fetched by the scripts):

| Script | Expected input|
| ------ | ------------- |
|`point_doubling_twisted_curve`: `P` to `2P`| `q .. lambda_2P P`|
|`point_addition_twisted_curve`: `P,Q` to `P + Q`| `q .. lambda_(P+Q) P Q`|
|`point_negation_twisted_curve`: `P` to `-P`| `q .. P`|
|`line_eval`: `T,Q,P` to `eval_(l_(T,Q))(P)`, where `l_(T,Q)` is the line through `T,Q`| `q .. lambda_(T,Q) Q P`|
|`line_eval_times_eval`| `q .. ev ev`|
|`line_eval_times_eval_times_eval`| `q .. t1 ev`|
|`line_eval_times_eval_times_eval_times_eval`| `q .. t1 t2`|
|`line_eval_times_eval_times_eval_times_eval_times_eval_times_eval`| `q .. t1 t4`|
|`line_eval_times_eval_times_miller_loop_output`| `q .. t1 t2`|
|`miller_loop_output_square`| `q .. t1`|
|`miller_loop_output_mul`| `q .. t1 t2`|
|`miller_loop_output_times_eval`| `q .. t1 ev`|
|`miller_loop_output_times_eval_times_eval_times_eval`| `q .. t1 t2`|
|`miller_loop_output_times_eval_times_eval_times_eval_times_eval_times_eval_times_eval`| `q .. t1 t2`|
|`pad_eval_times_eval_to_miller_output`: `ev` to element in `Fqk`| `q .. ev`|
|`pad_eval_times_eval_times_eval_times_eval_to_miller_output`: `t1 = ev * ev * ev * ev` to element in `Fqk`| `q .. t1`|
|`cyclotomic_inverse`: `f` to `f^{-1}`| `q .. f`|
|`easy_exponentiation_with_inverse_check`: `f` to `f^{(q^k-1)/Phi_k(q)}`| `q .. f^{-1} f`|
|`hard_exponentiation`: `f` to `f^{Phi_k(q) / r}`| `q .. f`|

## Use an instance of PairingModel

The Bitcoin Script Library contains two instantiations of PairingModel. One for [BLS12-381](../lib/bilinear_pairings/bls12_381/bls12_381.py), and the other for [MNT5-753](../lib/bilinear_pairings/mnt4_753/mnt4_753.py). Below is some example code for using these instantiations.

```python
# Import the PairingModel instantiation for BLS12-381
from src.zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381

# The following is the script that, taken two points P, Q and some additional data, compute the pairing e(P,Q)
bls12_381_pairing = bls12_381.pairing(
    modulo_threshold = 1,                               # The max size a number is allowed to reach during script execution
    check_constant = True,
    clean_constant = True,
)

# The following is the script that, taken two points P1, P2, P3, Q1, Q2, Q3, and some additional data, compute the product of the three pairins e(P1,Q1) * e(P2,Q2) * e(P3,Q3)
bls12_381_triple_pairing = bls12_381.triple_pairing(
    modulo_threshold = 1,                   
    check_constant = True,
    clean_constant = True,
)
```
