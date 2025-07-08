"""Bitcoin scripts that perform arithmetic operations in F_q."""

from tx_engine import Script

from src.zkscript.script_types.stack_elements import StackFiniteFieldElement
from src.zkscript.util.utility_functions import check_order
from src.zkscript.util.utility_scripts import (
    bitmask_to_boolean_list,
    bool_to_moving_function,
    mod,
    move,
    pick,
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
        rolling_option: int = 3,
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
            rolling_option (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            The script that computes `± x ± y`.
        """
        check_order([x, y])
        is_x_rolled, is_y_rolled = bitmask_to_boolean_list(rolling_option, 2)

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        out += move(y, bool_to_moving_function(is_y_rolled))  # Move y
        out += move(x.shift(1 - is_y_rolled), bool_to_moving_function(is_x_rolled))  # Move x
        out += Script.parse_string("OP_ADD" if (x.negate == y.negate) else "OP_SUB")
        out += Script.parse_string("OP_NEGATE" if y.negate else "")
        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        return out

    def inverse(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(0, False, 1),  # noqa: B008
        rolling_option: int = 1,
        mod_frequency: int = 1,
    ) -> Script:
        """Compute x^-1.

        The script computes `x^(self.MODULUS - 2) = x^-1` (in Fq) if `x != 0` else `0`.

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x` and if `x` is negated.
            rolling_option (int): Bitmask deciding if `x` is removed from the stack. Defaults to `1` (remove).
            mod_frequency (int): Integer defining after how many operation it is required to take the modulo.

        Returns:
            The script that computes `x^-1` if `x != 0` else `0`.
        """
        is_x_rolled = bitmask_to_boolean_list(rolling_option, 1)
        bin_mod = [int(digit) for digit in bin(self.MODULUS - 2)[2:]]

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()
        out += move(x, bool_to_moving_function(is_x_rolled))
        out += Script.parse_string("OP_NEGATE") if x.negate else Script()

        # inverse computations in Fq2 and Fq3 are trivial
        if self.MODULUS not in {2, 3}:
            out += Script.parse_string("OP_DUP")

            mul_tracker = 0
            for digit in bin_mod[1:-1]:
                if digit == 0:
                    out += Script.parse_string("OP_DUP OP_MUL")
                    mul_tracker += 1
                else:
                    out += Script.parse_string("OP_DUP OP_MUL OP_OVER OP_MUL")
                    mul_tracker += 2
                if mul_tracker >= mod_frequency:
                    out += pick(position=-1, n_elements=1)
                    out += mod(stack_preparation="", is_positive=False, is_constant_reused=False)
                    mul_tracker = 0

            out += Script.parse_string("OP_DUP OP_MUL OP_MUL")

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo, is_constant_reused=is_constant_reused)
        return out
