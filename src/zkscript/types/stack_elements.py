"""Classes defining types of elements manipulated on the stack."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Self, Union


@dataclass(init=False)
class StackBaseElement:
    """Base element on the stack.

    Attributes:
        position (int): the position of StackBaseElement on the stack.
    """

    position: int

    def __init__(self, position: int):
        """Initialise StackBaseElement, representing an element on the stack.

        Args:
            position (int): the position of StackBaseElement on the stack.
        """
        self.position = position

    def is_before(self, other) -> bool:
        """Check whether self comes before other in the stack.

        The method checks whether all the elements: (self[0], .., self[self.length-1]) are before the elements
        (other[0], .., other[other.length-1]) in the stack.
        """
        return (
            self.position > other.x.position
            if isinstance(other, StackEllipticCurvePoint)
            else self.position > other.position
        )

    def overlaps_on_the_right(self, other) -> tuple[bool, str]:
        """Check whether the end of self overlaps with the beginning of other."""
        if self.position <= other.position:
            msg = "Self and other overlap: "
            msg += f"self.position: {self.position}, other.position: {other.position}"
            return True, msg
        return False, ""

    def shift(self, n: int) -> Self:
        """Return a copy of self shifted by n in the stack."""
        out = deepcopy(self)
        out.position += n
        return out


@dataclass(init=False)
class StackNumber(StackBaseElement):
    """Number on the stack.

    Attributes:
        position (int): the position of StackNumber on the stack.
        negate (bool): whether the number should be negated when used in a script.
    """

    position: int
    negate: bool

    def __init__(self, position: int, negate: bool):
        """Initialise StackNumber, representing a number (integer) on the stack.

        Args:
            position (int): the position of StackNumber on the stack.
            negate (bool): whether the number should be negated when used in a script.
        """
        super().__init__(position)
        self.negate = negate

    def set_negate(self, negate: bool) -> Self:
        """Return a copy of self with negate set to negate."""
        return StackNumber(self.position, negate)


@dataclass(init=False)
class StackFiniteFieldElement(StackNumber):
    """Finite field element on the stack.

    Attributes:
        position (int): the position of StackNumber on the stack.
        negate (bool): whether the number should be negated when used in a script.
        extension_degree (int): the extension degree of the finite field over Fq.
    """

    position: int
    negate: bool
    extension_degree: int

    def __init__(self, position: int, negate: bool, extension_degree: int):
        """Initialise StackFiniteFieldElement, representing an element of a finite field on the stack.

        Args:
            position (int): the position of StackNumber on the stack.
            negate (bool): whether the number should be negated when used in a script.
            extension_degree (int): the extension degree of the finite field over Fq.
        """
        if extension_degree <= 0:
            msg = "The extension_degree must be a positive integer: "
            msg += f"extension_degree: {extension_degree}"
            raise ValueError(msg)
        if position >= 0 and position - extension_degree + 1 < 0:
            msg = "The field element does not fit in the stack: "
            msg += f"position: {position}, extension_degree: {extension_degree}"
            raise ValueError(msg)

        super().__init__(position, negate)
        self.extension_degree = extension_degree

    def overlaps_on_the_right(self, other) -> tuple[bool, str]:
        """Check whether the end of self overlaps with the beginning of other.

        Return True if: (self[0], .., self[self.extension_degree-1]) and (other[0], .., other[other.extension_degree-1])
        are such that self[self.extension_degree-1] comes after other[0] in the stack.
        """
        if self.position - self.extension_degree < other.position:
            msg = "Self and other overlap: "
            msg += f"self.position: {self.position}, self.extension_degree: {self.extension_degree}, other.position: {
                other.position
                }"
            return True, msg
        return False, ""

    def set_negate(self, negate: bool) -> Self:
        """Return a copy of self with negate set to negate."""
        return StackFiniteFieldElement(self.position, negate, self.extension_degree)

    def extract_component(self, component: int) -> Self:
        """Extract `self_component` from `self`."""
        assert component >= 0, "Component should be positive."
        assert component < self.extension_degree, "Component should be smaller than self.extension_degree."
        return StackFiniteFieldElement(self.position - component, self.negate, 1)


@dataclass(init=False)
class StackEllipticCurvePoint:
    """Elliptic curve point on the stack comprising two finite field elements.

    Attributes:
        x (StackFiniteFieldElement): the x coordinate of the point.
        y (StackFiniteFieldElement): the y coordinate of the point.
        position (int): the position of the point in the stack (equal to x.position).
        negate (bool): whether the point should be negated when used in a script (equal to y.negate).
    """

    x: StackFiniteFieldElement
    y: StackFiniteFieldElement
    position: int
    negate: bool

    def __init__(self, x: StackFiniteFieldElement, y: StackFiniteFieldElement):
        """Initialise StackEllipticCurvePoint, representing an elliptic curve point on the stack.

        Args:
            x (StackFiniteFieldElement): the x coordinate of the point.
            y (StackFiniteFieldElement): the y coordinate of the point.
        """
        different_lengths = False

        overlaps, msg = x.overlaps_on_the_right(y)  # Note: if overlaps = False, then x.is_before(y) = True
        msg = "\n" * overlaps + msg  # Nice alignment
        if x.extension_degree != y.extension_degree:
            msg += "\nThe extension degrees of the x and y coordinates do not match: "
            msg += f"x.extension_degree: {x.extension_degree}, y.extension_degree: {y.extension_degree}"
            different_lengths = True
        if overlaps or different_lengths:
            msg = f"Defining StackEllipticCurvePoint with \n x: {x}, \n y: {y}\nErrors:{msg}"
            raise ValueError(msg)

        self.x = x
        self.y = y
        self.position = self.x.position
        self.negate = y.negate

    def overlaps_on_the_right(self, other) -> tuple[bool, str]:
        """Check whether the end of self overlaps with the beginning of other.

        The method checks whether all the elements: (self[0], .., self[self.length-1]) are before the elements
        (other[0], .., other[other.length-1]) in the stack. If other is StackEllipticCurvePoint, then the function
        substitutes other with other.x.
        """
        return self.y.overlaps_on_the_right(other)

    def is_before(self, other) -> bool:
        """Check whether self comes before other in the stack.

        The method checks whether all the elements: (self.y[0], .., self.y[self.length-1]) are before the elements
        (other[0], .., other[other.length-1]) in the stack. If other is StackEllipticCurvePoint, then the function
        substitutes other with other.x.
        """
        return self.y.is_before(other)

    def shift(self, n: int) -> Self:
        """Return a copy of self shifted by n in the stack."""
        return StackEllipticCurvePoint(self.x.shift(n), self.y.shift(n))

    def set_negate(self, negate: bool) -> Self:
        """Return a copy of self with negate set to negate."""
        out = deepcopy(self)
        out.y.negate = negate
        out.negate = negate
        return out


type StackElements = Union[StackBaseElement, StackNumber, StackFiniteFieldElement, StackEllipticCurvePoint]
