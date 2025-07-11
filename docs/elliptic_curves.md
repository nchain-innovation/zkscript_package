# Elliptic curve arithmetic

The zk Script Library contains the implementation of arithmetic for elliptic curves. More precisely, it contains scripts for:
- EC arithmetic over a prime field `Fq`:
    - `point_algebraic_addition`: a script to perform algebraic point addition (i.e., `P + Q`, `P - Q`, `- P + Q`, `- P - Q`) of two points that we know are not equal, nor the inverse of one another
    - `point_algebraic_doubling`: a script to perfom algebraic doubling of a point (i.e., `2P` or `-2P`)
    - `point_addition_with_unknown_points`: a script to sum two points which we do not know whether they are equal, different, or the inverse of one another
- Unrolled EC arithmetic over a prime field `Fq`: `unrolled_multiplication` returns a script to compute the scalar point multiplication `a * P` for any point `P` and any `a` which is smaller that the `max_multiplier` parameter supplied to the `unrolled_multiplication` function when the script was constructed
- EC arithmetic over a quadratic extension field `Fq2`:
    - `point_algebraic_addition`
    - `point_algebraic_doubling`
    - `point_negation`

 In all the implementations, the point at infinity is modelled as a sequence of `0x00`, as many as the number of elements required to specify a point on the curve. E.g, `0x00 0x00` is the point at infinity in a curve over `Fq`, `0x00 0x00 0x00 0x00` is the point at infinity in a curve over `Fq2`.

## Function arguments for `EllipticCurveFq`, `EllipticCurveFq2`

The scripts `point_algebraic_addition` and `point_algebraic_doubling` in the classes `EllipticCurveFq` and `EllipticCurveFq2` have the following arguments:
- `take_modulo (bool | None)`: whether or not to return the coordinates of the output modulo `q`
- `check_constant (bool | None)`: whether or not to check the constant supplied for modulo operations is the correct one
- `clean_constant (bool | None)`: wheter or not to clean the constant supplied for modulo operations
- `verify_gradient (bool)`: whether to check the validity of the gradient provided
- `gradient (StackFiniteFieldElement)`: the position of `gradient` in the stack
- `P (StackEllipticCurvePoint)`: the position of `P` in the stack (and whether it should be negated)
- (only for `point_algebraic_addition`) `Q (StackEllipticCurvePoint)`: the position of `Q` in the stack (and whether it should be negated)
- `rolling_option (int)`: a bitmask telling the function whether `gradient`, `P`, and `Q` should be rolled.

For the definition of the `StackFiniteFieldElement`, `StackEllipticCurvePoint`, see [StackElements](../docs/stack_elements.md).

 # Examples: EC arithmetic over Fq

 ```python
# For testing
from tx_engine import Script, Context
# Let's set up secp256k1
from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.util.utility_scripts import nums_to_script

secp256k1_MODULUS = 115792089237316195423570985008687907853269984665640564039457584007908834671663
# Script class for operations on secp256k1
secp256k1_script = EllipticCurveFq(q=secp256k1_MODULUS,curve_a=0,curve_b=7)

secp256k1_generator = [0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798, 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8]
secp256k1_double_generator = [0xc6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5,0x1ae168fea63dc339a3c58419466ceaeef7f632653266d0e1236431a950cfe52a]
secp256k1_generator_plus_double_generator = [0xf9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9, 0x388f7b0f632de8140fe337e62a37f3566500a99934c2231b6cb9fd7584b8e672]

# Let's sum two points on secp256k1: generator + 2*generator
lock = secp256k1_script.point_algebraic_addition(take_modulo=True,check_constant=True,clean_constant=True)
lock += nums_to_script([secp256k1_generator_plus_double_generator[1]]) + Script.parse_string('OP_EQUALVERIFY')
lock += nums_to_script([secp256k1_generator_plus_double_generator[0]]) + Script.parse_string('OP_EQUAL')

# Gradient through generator and 2*generator: (y1 - y0) * (x1 - x0)^-1
lam = ((secp256k1_double_generator[1] - secp256k1_generator[1]) * pow(secp256k1_double_generator[0] - secp256k1_generator[0],-1,secp256k1_MODULUS)) % secp256k1_MODULUS

# Unlocking script
unlock = nums_to_script([secp256k1_MODULUS])
unlock += nums_to_script([lam])
unlock += nums_to_script(secp256k1_double_generator)
unlock += nums_to_script(secp256k1_generator)

context = Context(script = unlock + lock)
assert(context.evaluate())

# Let's double a point: 2*generator
lock = secp256k1_script.point_algebraic_doubling(take_modulo=True,check_constant=True,clean_constant=True)
lock += nums_to_script([secp256k1_double_generator[1]]) + Script.parse_string('OP_EQUALVERIFY')
lock += nums_to_script([secp256k1_double_generator[0]]) + Script.parse_string('OP_EQUAL')

# Gradient through generator and 2*generator: 3*x0^2 / (2*y0)
lam = (3 * pow(secp256k1_generator[0],2,secp256k1_MODULUS) * pow(secp256k1_generator[1] * 2, -1, secp256k1_MODULUS)) % secp256k1_MODULUS

# Unlocking script
unlock = nums_to_script([secp256k1_MODULUS])
unlock += nums_to_script([lam])
unlock += nums_to_script(secp256k1_generator)

context = Context(script = unlock + lock)
assert(context.evaluate())
```

**Note:** `ec_operations_fq2` works in the same way as per `ec_operations_fq`, with the difference that when we instantiate an object of the class `EllipticCurveFq2` we need to supply the instantiation of the Bitcoin Script arithmetic in `Fq2`.

# Unrolled EC arithmetic

`EllipticCurveFqUnrolled` is a class that allows us to compute scalar point multiplication over any curve over a prime field. The function producing such script is `unrolled_multiplication`, which takes the following variables:
- `max_multiplier`: the max number `n` such that the script is able to compute `n * P`
- `modulo_threshold`: the max size a number is allowed to reach during script execution
- `check_constant`: a boolean value deciding whether the script should check that the constant supplied for modulo operations is correct
- `clean_constant`: a boolean value deciding whether the script should clean the constant used for modulo operations

The data needed to execute the output script of `unrolled_multiplication` is described in the function documentation. It works as follows: `q ... marker_a_is_zero [lamdbas,a] P`, where:
- `q` is the modulus used to perform modulo operations
- `marker_a_is_zero` is a marker which is set to `ÒP_1` if `a=0`, to `OP_0` otherwise
- `P` is the point we are multiplying by
- `[lambdas,a]` is the sequence of gradients (also called lamdbdas) needed to compute `a * P`, together with some flags used by the script to detect which operations to perform. The construction of the unlocking script can be seen in the function `unrolled_multiplication_input`; some examples are also given in the `unrolled_multiplication` function documentation.

Note that the script computes `a * P` via double-and-add, i.e., it goes down from `a_(n-2)` to `a_0`, where `a = a_0 ... a_(n-1)` in binary and doubles and add at each step according to `a_i`. 