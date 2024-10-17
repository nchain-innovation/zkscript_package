from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Union

from src.zkscript.util.utility_scripts import pick, roll

type MovingFunction = Union[roll, pick]


@dataclass(init=False)
class StackBaseElement:
    position: int
    length: int
    move: MovingFunction

    def __init__(self, position: int, length: int, move: MovingFunction):
        if length <= 0:
            msg = f"The length must be a positive integer: length: {length}"
            raise ValueError(msg)
        if position >= 0 and position - length + 1 < 0:
            msg = f"The number does not fit in the stack: position: {position}, length: {length}"
            raise ValueError(msg)

        self.position = position
        self.length = length
        self.move = move

    def is_before(self, other):
        """Check whether self comes before other in the stack. Raise a ValueError if the two elements overlap.

        The method checks whether all the elements: (self[0], .., self[self.length-1]) are before the elements
        (other[0], .., other[other.length-1]) in the stack.
        """
        overlap, msg = self.overlaps_on_the_right(other)
        if overlap:
            raise ValueError(msg)
        return self.position > other.position

    def overlaps_on_the_right(self, other):
        """Check whether the end of self overlaps with the beginning of other.

        Return True if: (self[0], .., self[self.length-1]) and (other[0], .., other[other.length-1])
        are such that self[self.length-1] comes after other[0] in the stack.

        """
        if self.position - self.length < other.position:
            msg = f"Self and other overlap: \
                self.position: {self.position}, self.length: {self.length}, other.position {other.position}"
            return True, msg
        return False, ""

    def is_rolled(self):
        """Return True if self.move == roll, else False."""
        return self.move == roll

    def shift(self, n: int):
        """Return a copy of self shifted by n in the stack."""
        out = deepcopy(self)
        out.position += n
        return out

    def set_move(self, move: MovingFunction):
        """Return a copy of self with move set to move."""
        out = deepcopy(self)
        out.move = move
        return out

    def moving_script(self, start_index: int = 0, end_index: int | None = None):
        """Return the script that moves self with self.move."""
        if end_index is None:
            end_index = self.length
        if self.length < end_index:
            msg = f"Moving more elements than self, self.length: {self.length}, end_index: {end_index}"
            raise ValueError(msg)
        if start_index < 0:
            msg = f"Start index must be positive: start_index {start_index}"
            raise ValueError(msg)
        return self.move(position=self.position - start_index, n_elements=end_index - start_index)


@dataclass(init=False)
class StackNumber(StackBaseElement):
    position: int
    length: int
    negate: bool
    move: MovingFunction

    def __init__(self, position: int, length: int, negate: bool, move: MovingFunction):
        super().__init__(position, length, move)
        self.negate = negate

    def set_negate(self, negate: bool):
        """Return a copy of self with negate set to negate."""
        out = deepcopy(self)
        out.negate = negate
        return out


@dataclass(init=False)
class StackEllipticCurvePoint:
    x: StackNumber
    y: StackNumber

    def __init__(self, x: StackNumber, y: StackNumber):
        overlaps = different_lenghts = different_moving_functions = False
        msg = ""

        overlaps, msg = x.overlaps_on_the_right(y)
        if x.length != y.length:
            msg = f"The lengths of the x and y coordinates do not match: \
                x.length: {x.length}, y.length: {y.length}"
            different_lenghts = True
        if x.move != y.move:
            msg = f"Current implementations only support the same moving function for \
                the x and y coordinates: x.move: {x.move}, y.move: {y.move}"
            different_moving_functions = True
        if overlaps or different_lenghts or different_moving_functions:
            raise ValueError(msg)

        self.x = x
        self.y = y

    def is_before(self, other):
        """Check whether self comes before other in the stack. Raise a ValueError if the two elements overlap.

        The method checks whether all the elements: (self.y[0], .., self.y[self.length-1]) are before the elements
        (other[0], .., other[other.length-1]) in the stack. If other is StackEllipticCurvePoint, then the function
        subtitutes other with other.x.
        """
        if type(other) is StackEllipticCurvePoint:
            other = other.x
        return self.y.is_before(other)

    def is_rolled(self):
        """Return True if self.x.move == roll, else False."""
        return self.x.move == roll

    def shift(self, n: int):
        """Return a copy of self shifted by n in the stack."""
        return StackEllipticCurvePoint(self.x.shift(n), self.y.shift(n))

    def set_move(self, move: MovingFunction):
        """Return a copy of self with move set to move."""
        return StackEllipticCurvePoint(self.x.set_move(move), self.y.set_move(move))

    def moving_script(self):
        """Return the script that moves self with self.move."""
        return self.x.move(position=self.x.position, n_elements=self.x.length + self.y.length)


# Argument type for functions generating scripts
type StackElements = Dict[str, Union[StackBaseElement, StackNumber, StackEllipticCurvePoint]]
