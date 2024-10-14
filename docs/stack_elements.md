#  Stack Elements

To standardise the arguments supplied to the functions generating the scripts, we have defined three classes (see [utility_classes.py](../src/zkscript/util/utility_classes.py)):
- `StackNumber`: a class representing an number on the stack. It has the following attributes:
    - `position`: the position of the number in the stack
    - `length`: how many elements the number is made of
    - `negate`: whether the number should be negated when used in a script
    - `move`: which moving function should be used: rolling or picking
- `StackString`: a class representing a string on the stack. It has the following attributes:
    - `position`: the position of the string in the stack
    - `length`: how many elements the string is made of
    - `move`: which moving function should be used: rolling or picking
- `StackEllipticCurvePoint`: a class representing an elliptic curve point on the stack. It has two attributes:
    - `x`: a `StackNumber` representing the x-coordinate of the point
    - `y`: a `StackNumber` representing the y-coordinate of the point

An ordering is defined for instances of the above classes, so that `a < b` means that `a` comes before `b` in the stack (`a` is buried deeper than `b`).

## Examples: StackNumber

```
StackNumber(position=0,length=1,negate=False,move=pick)
```

Represent a number made of a single element, e.g., `19`, that sits on top of the stack, which should not be negate when used, and that should be duplicated (picked).

```
StackNumber(position=3,length=2,negate=False,move=roll)
```

Represents a number $x = (x_0, x_1)$ that takes two elements to be represented, e.g, an element of $\mathbb{F}_{q^2} = \mathbb{F}_q[u] / (u^2 + 1)$ for $q = 19$, that is positioned as follows:
```
... x0 x1 a b
```
that should not be negated when used, and that should be rolled.

## Examples: StackEllipticCurvePoint

```
StackEllipticCurvePoint(
    StackNumber(position=3,length=1,negate=False,move=pick),
    StackNumber(position=2,length=1,negate=False,move=pick)
)
```

Represent an elliptic curve point $P = (x,y)$, where $x$ and $y$ are two numbers, such that $P$ should not be negated when used, $P$ should be rolled, and it is positioned as follows:
```
... x y a b
```

## Examples: StackString

```
StackString(position=4,length=1,move=pick)
```

Represent a string made of a single element, e.g., `b"Hello"`, that should be duplicated (picked) when used, and that is positioned as follows:
```
... <b"Hello> a b c d
```