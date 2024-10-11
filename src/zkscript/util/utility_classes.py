from dataclasses import dataclass
from typing import Dict, Union

from src.zkscript.util.utility_scripts import pick, roll

type MovingFunction = Union[roll, pick]


@dataclass(init=False)
class StackNumber:
    position: int
    length: int
    negate: bool
    move: MovingFunction

    def __init__(self, position: int, length: int, negate: bool, move: MovingFunction):
        if position < 0:
            msg = f"The position must be a positive integer: position: {position}"
            raise ValueError(msg)
        if length <= 0:
            msg = f"The length must be a positive integer: length: {length}"
            raise ValueError(msg)
        if position - length + 1 < 0:
            msg = f"The number does not fit in the stack: position: {position}, length: {length}"
            raise ValueError(msg)

        self.position = position
        self.length = length
        self.negate = negate
        self.move = move

    def __lt__(self, other):
        """Check whether self comes before other in the stack. Raise a ValueError if the two elements overlap."""
        if type(other) is StackEllipticCurvePoint:
            other = other.x
        if self.position - self.length < other.position:
            msg = f"Self and other overlap: \
                self.position: {self.position}, self.length: {self.length}, other.position {other.position}"
            raise ValueError(msg)
        return self.position > other.position


@dataclass(init=False)
class StackString:
    position: int
    length: int
    move: MovingFunction

    def __init__(self, position: int, length: int, move: MovingFunction):
        if position < 0:
            msg = f"The position must be a positive integer: position: {position}"
            raise ValueError(msg)
        if length <= 0:
            msg = f"The length must be a positive integer: length: {length}"
            raise ValueError(msg)
        if position - length + 1 < 0:
            msg = f"The string does not fit in the stack: position: {position}, length: {length}"
            raise ValueError(msg)

        self.position = position
        self.length = length
        self.move = move

    def __lt__(self, other):
        """Check whether self comes before other in the stack. Raise a ValueError if the two elements overlap."""
        if type(other) is StackEllipticCurvePoint:
            other = other.x
        if self.position - self.length < other.position:
            msg = f"Self and other overlap: \
                self.position: {self.position}, self.length: {self.length}, other.position {other.position}"
            raise ValueError(msg)
        return self.position > other.position


@dataclass(init=False)
class StackEllipticCurvePoint:
    x: StackNumber
    y: StackNumber

    def __init__(self, x: StackNumber, y: StackNumber):
        if x.position - x.length < y.position:
            msg = f"The x-coordinate and the y-coordinate overlap: \
                x.position: {x.position}, x.length: {x.length}, y.position {y.position}"
            raise ValueError(msg)
        if x.length != y.length:
            msg = f"The lengths of the x and y coordinates do not match: \
                x.length: {x.length}, y.length: {y.length}"
            raise ValueError(msg)
        if x.move != y.move:
            msg = f"Current implementations only support the same moving function for \
                the x and y coordinates: x.move: {x.move}, y.move: {y.move}"
            raise ValueError(msg)

        self.x = x
        self.y = y

    def __lt__(self, other):
        """Check whether self comes before other in the stack. Raise a ValueError if the two elements overlap."""
        if type(other) is StackEllipticCurvePoint:
            other = other.x
        return self.y < other


type StackElements = Dict[str, Union[StackNumber, StackString, StackEllipticCurvePoint]]
