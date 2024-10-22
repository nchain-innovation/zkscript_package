#  Stack Elements

To standardise the arguments supplied to the functions generating the scripts, we have defined three classes (see [utility_classes.py](../src/zkscript/util/utility_classes.py)):
- `StackBaseElement`: a class representing an element on the stack. It has the following attributes:
    - `position`: the position of the element in the stack
- `StackNumber`: a class representing an integer on the stack. It has the following attributes:
    - `position`: the position of the number in the stack
    - `negate`: whether the number should be negated when used in a script
- `StackFiniteFieldElement`: a class representing a element belonging to a finite field. It has the following attributes:
    - `position`: the position of the element in the stack
    - `extension_degree`: the extension degree of the finite field $\mathbb{F}_{q^k}$ over the base field $\mathbb{F}_q$ ($k =$ `extension_degree`)
- `StackEllipticCurvePoint`: a class representing an elliptic curve point on the stack. It has two attributes:
    - `x`: a `StackFiniteFieldElement` representing the x-coordinate of the point
    - `y`: a `StackFiniteFieldElement` representing the y-coordinate of the point
    - `position`: the position of the point in the stack (equal to `x.position`)
    - `negate`: whether the point should be negated when used in a script (equal to `y.negate`)

All the classes feature the following methods:
- `is_before(self,other)`: returns `True` if `self` is before `other` in the stack (i.e., `self.position > other.position`)
- `overlaps_on_the_right(self,other)`: returns `True` (together with a message) if the last element `self` is after the first element of `other`
- `shift(self,n:int)`: returns a copy of `self` with position shifted by `n`

Furthermore, `StackNumber`, `StackFiniteFieldElement` and `StackEllipticCurvePoint` feature the method:
- `set_negate(self,negate:bool)`: returns a copy of `self` with `self.negate` set to `negate`

### `Move` script

In [utility_script](../src/zkscript/util/utility_scripts.py) we find the `move` function, whose signature is:

```python
def move(
    stack_element: StackElements, moving_function: Union[roll, pick], start_index: int = 0, end_index: int | None = None
) -> Script
```

As explained in the documentation, this function returns the script that moves `stack_element[start_index], .., stack_element[end_index]` with `moving_function`, which is either `pick` or `roll` as defined in [utility_script](../src/zkscript/util/utility_scripts.py).

## Examples: StackBaseElement

```
StackBaseElement(position=0)
```

Represents an element that sits on top of the stack.

## Examples: StackNumber

```
StackNumber(position=0,negate=False)
```

Represents a number that sits on top of the stack, which should not be negated when used.

```
StackNumber(position=3,negate=True)
```

Represents a number `x` that should be negated when used and that is positioned as follows:

```
stack = [.., x, a, b, c]
```

## Examples: StackFiniteFieldElement

```
StackFiniteFieldElement(position=3,negate=True,extension_degree=2)
```

Represents an element $x = (x_0, x_1)$, $x \in \mathbb{F}_{q^2}$, that should be negated when used in a script, and that is positioned as follows:
```
[.., x0, x1, a, b]
```

## Examples: StackEllipticCurvePoint

```
StackEllipticCurvePoint(
    StackFiniteFieldElement(position=3,negate=False,extension_degree=1)
    StackFiniteFieldElement(position=2,negate=False,extension_degree=1)
)
```

Represents an elliptic curve point $P = (x,y)$, where $x, y \in \mathbb{F}_q$, that should not be negated when used in a script, and that is positioned as follows:
```
[.., x, y, a, b]
```