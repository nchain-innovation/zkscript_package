from collections.abc import Callable
from dataclasses import dataclass

from tx_engine import Script


@dataclass
class CurvePoint:
    position: int  # Position of the point
    negate: bool  # Whether the point should be negated or not when used
    move: Callable[[int, int], Script]  # Moving function: pick or roll from utility_scripts.py


@dataclass
class FieldElement:
    position: int  # Position of the element
    move: Callable[[int, int], Script]  # Moving function: pick or roll from utility_scripts.py
