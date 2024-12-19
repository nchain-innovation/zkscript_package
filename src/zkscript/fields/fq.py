"""Bitcoin scripts that perform arithmetic operations in F_q."""

from tx_engine import Script

from src.zkscript.types.stack_elements import StackFiniteFieldElement
from src.zkscript.util.utility_functions import check_order
from src.zkscript.util.utility_scripts import (
    bitmask_to_boolean_list,
    bool_to_moving_function,
    mod,
    move,
    roll,
    verify_bottom_constant,
)


class Fq:
    """Construct Bitcoin scripts that perform arithmetic operations in F_q.

    Attributes:
        MODULUS: The characteristic of the field F_q.
    """

    def __init__(self, q: int):
        """Initialise F_q.

        Args:
            q: The characteristic of the base field F_q.
        """
        self.MODULUS = q

    def algebraic_sum(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(1, False, 1),  # noqa: B008
        y: StackFiniteFieldElement = StackFiniteFieldElement(0, False, 1),  # noqa: B008
        rolling_options: int = 3,
    ) -> Script:
        """Compute the algebraic sum of x and y.

        The script computes `± x ± y` for `x` and `y` in `F_q`.

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x` and whether `x` should be negated when used.
            y (StackFiniteFieldElement): The position in the stack of `y` and whether `y` should be negated when used.
            component:
            rolling_options (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            The script that computes `± x ± y`.
        """
        check_order([x, y])
        is_x_rolled, is_y_rolled = bitmask_to_boolean_list(rolling_options, 2)

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        out += move(y, bool_to_moving_function(is_y_rolled))  # Move y
        out += move(x.shift(1 - is_y_rolled), bool_to_moving_function(is_x_rolled))  # Move x
        out += Script.parse_string("OP_ADD" if not (x.negate or y.negate) or (x.negate and y.negate) else "OP_SUB")
        if (x.negate and y.negate) or (not x.negate and y.negate):
            out += Script.parse_string("OP_NEGATE")
        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else roll(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        return out
