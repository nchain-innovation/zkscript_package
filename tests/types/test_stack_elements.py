import re

import pytest

from src.zkscript.types.stack_elements import (
    StackBaseElement,
    StackEllipticCurvePoint,
    StackFiniteFieldElement,
)


@pytest.mark.parametrize(
    ("stack_element_type", "parameters", "msg"),
    [
        (
            StackFiniteFieldElement,
            {"position": 1, "negate": False, "extension_degree": -1},
            r"The extension_degree must be a positive integer: extension_degree: -\d+",
        ),
        (
            StackFiniteFieldElement,
            {
                "position": 1,
                "negate": False,
                "extension_degree": 3,
            },
            r"The field element does not fit in the stack: position: \d+, extension_degree: \d+",
        ),
        (
            StackEllipticCurvePoint,
            {"x": StackFiniteFieldElement(1, False, 1), "y": StackFiniteFieldElement(2, False, 1)},
            r"Defining StackEllipticCurvePoint with \n x: .*, \n y: .*\nErrors:\nSelf "
            r"and other overlap: self\.position: \d+, self\.extension_degree: \d+, other\.position: \d+",
        ),
        (
            StackEllipticCurvePoint,
            {"x": StackFiniteFieldElement(2, False, 1), "y": StackFiniteFieldElement(1, False, 2)},
            r"Defining StackEllipticCurvePoint with \n x: .*, \n y: .*\nErrors:\nThe extension "
            r"degrees of the x and y coordinates do not match: x\.extension_degree: \d+, y\.extension_degree: \d+",
        ),
    ],
)
def test_initialisation_errors(stack_element_type, parameters, msg):
    with pytest.raises(ValueError, match=msg):
        stack_element_type(**parameters)


@pytest.mark.parametrize(
    ("stack_element_type", "parameters", "msg"),
    [
        (
            [StackFiniteFieldElement, StackFiniteFieldElement],
            [
                {"position": 1, "negate": False, "extension_degree": 1},
                {"position": 1, "negate": False, "extension_degree": 1},
            ],
            r"Self and other overlap: self\.position: \d+, self\.extension_degree: \d+, other\.position: \d+",
        ),
        (
            [StackBaseElement, StackBaseElement],
            [
                {"position": 1},
                {"position": 1},
            ],
            r"Self and other overlap: self\.position: \d+, other\.position: \d+",
        ),
        (
            [StackEllipticCurvePoint, StackEllipticCurvePoint],
            [
                {"x": StackFiniteFieldElement(6, False, 2), "y": StackFiniteFieldElement(4, False, 2)},
                {"x": StackFiniteFieldElement(4, False, 2), "y": StackFiniteFieldElement(2, False, 2)},
            ],
            r"Self and other overlap: self\.position: \d+, self\.extension_degree: \d+, other\.position: \d+",
        ),
    ],
)
def test_overlaps_on_the_right(stack_element_type, parameters, msg):
    overlaps, msg_returned = stack_element_type[0](**parameters[0]).overlaps_on_the_right(
        stack_element_type[1](**parameters[1])
    )
    assert overlaps
    assert re.match(msg, msg_returned)
