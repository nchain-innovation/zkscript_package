# Finite field arithmetic

The zk Script Library contains the implementation of finite field arithmetic for the following finite fields:
- `Fq2`: the quadratic extension of a field with prime order `q`
- `Fq4`: the quadratic extension of the finite field `Fq2`
- `Fq6_3_over_2`: the finite field `Fq6`, built as a cubic extension of `Fq2`
- `Fq12_2_over_3_over_2`: the finite field `Fq12`, built as a quadratic extension of `Fq6`
- `Fq12_3_over_2_over_2`: the finite fields `Fq12`, built a a cubic extension of `Fq4`

Not all operations have been implemented for all fields, as the implementation has been on a need-to-use basis. However, `Fq2` and `Fq4` have implementation of most operations in these fields.

The code below shows how to use the scripts for these fields.

### Fq2

```python
# This is the class containing the script for Fq2 arithmetic
from zkscript.fields.fq2 import Fq2
# For testing
from tx_engine import Script, Context


# (-1)^((19-1)/2) = -1 => -1 is not a quadratic residue
fq2_script = Fq2(q=19,non_residue=-1)

# We can construct the script to add two elements of Fq2
# The required stack is: q .. X Y, where X, Y are in Fq2
# The output is X + Y
lock = fq2_script.add(
    take_modulo = True,                                             # Returns the output with coordinates in Fq
    check_constant = True,                                          # Checks that the constant supplied for modulo operation is the correct one, i.e., 19
    clean_constant = True,                                          # Cleans the constant
    is_constant_reused = False                                      # We do not need the constant after the end of the script execution
)
lock += Script.parse_string('1 OP_EQUALVERIFY 1 OP_EQUAL')          # We seek two elements in Fq2 that sum to (1,1)

unlock = Script.parse_string('19')                                  # modulus
unlock += Script.parse_string('1 0 0 1')                            # X = (1,0), Y = (0,1)
assert(Context(script=unlock+lock).evaluate())

# Let's test an incorrect input
unlock = Script.parse_string('19')                                  # modulus
unlock += Script.parse_string('1 1 1 0')                            # X = (1,1), Y = (1,0)
assert(not Context(script=unlock_wrong+lock).evaluate())
```

### Fq4

```python
# This is the class containing the script for Fq4 arithmetic
from zkscript.fields.fq4 import Fq4
# To build extension of Fq2
from zkscript.fields.fq2 import Fq2, fq2_for_towering
# For testing
from tx_engine import Script, Context

# If we wish to export Fq2 for towering, we use the function fq2_for_towering
# To the function, we need to pass the mul_by_non_residue variable
# 2 is a non quadratic residue in Fq => we build Fq2 with 2 as non_residue; then, 1 + u = (1,1) is Fq2 is a non quadratic residue
Fq2ForTowering = fq2_for_towering(mul_by_non_residue = Fq2.mul_by_one_plus_u)
fq2_script = Fq2ForTowering(q=19,non_residue=2)
fq4_script = Fq4(
    q=19,
    base_field=fq2_script,
    gammas_frobenius=None                   # If we want to leverage the implementation of the Frobenius morphism in Fq4, we need to pass the gammas here
)


# We can construct the script to multiply two elements of Fq4
# The required stack is: q .. X Y, where X, Y are in Fq4
# The output is X * Y
lock = fq4_script.mul(
    take_modulo = True,                                             # Returns the output with coordinates in Fq
    check_constant = True,                                          # Checks that the constant supplied for modulo operation is the correct one, i.e., 19
    clean_constant = True,                                          # Cleans the constant
    is_constant_reused = False                                      # We do not need the constant after the end of the script execution
)
lock += Script.parse_string('0 OP_EQUALVERIFY 1 OP_EQUALVERIFY 0 OP_EQUALVERIFY 0 OP_EQUAL')    # We seek two elements in Fq4 that multiply to (0,0,1,0)

unlock = Script.parse_string('19')
unlock += Script.parse_string('1 0 0 0 0 0 1 0')
assert(Context(script=unlock+lock).evaluate())

# Let's test an incorrect input
unlock_wrong = Script.parse_string('19')
unlock_wrong += Script.parse_string('0 0 1 0 0 0 1 0')
assert(not Context(script=unlock_wrong+lock).evaluate())
```