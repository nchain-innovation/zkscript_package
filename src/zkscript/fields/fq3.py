"""Bitcoin scripts that perform arithmetic operations in a cubic extension of F_q."""

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.types.stack_elements import StackFiniteFieldElement
from src.zkscript.util.utility_scripts import (
    bitmask_to_boolean_list,
    mod,
    pick,
    roll,
    verify_bottom_constant,
)


def fq3_for_towering(mul_by_non_residue):
    """Export Fq2 class with a mul_by_non_residue method to construct towering extensions."""

    class Fq3ForTowering(Fq3):
        pass

    Fq3ForTowering.mul_by_non_residue = mul_by_non_residue

    return Fq3ForTowering


class Fq3:
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^3 = F_q[x] / (x^3 - non_residue).

    F_q^3 = F_q[u] / (u^3 - non_residue) is a cubic extension of a base field F_q.

    Elements in F_q^3 are of the form `x0 + x1 * u + x2 * u^2`, where `x0`, `x1`, and `x2` are elements of F_q,
    and `u^3` is equal to some `non_residue` in F_q.

    Attributes:
        MODULUS: The characteristic of the base field F_q.
        NON_RESIDUE: The non-residue element used to define the quadratic extension.
    """

    def __init__(self, q: int, non_residue: int):
        """Initialise F_q^3, the quadratic extension of F_q.

        Args:
            q: The characteristic of the base field F_q.
            non_residue: The non-residue element used to define the quadratic extension.
        """
        self.MODULUS = q
        self.NON_RESIDUE = non_residue
        self.EXTENSION_DEGREE = 3
        self.base_field = Fq(q)

    def algebraic_sum(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(5, False, 3),  # noqa: B008
        y: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 3),  # noqa: B008
        rolling_options: int = 3,
    ) -> Script:
        """Algebraic addition in F_q^3.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2), y := (y0, y1, y2)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., ± x ± y := (± x0 ± y0, ± x1 ± y1, ± x2 ± y2)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x` and whether `x` should be negated when used.
                Defaults to `StackFiniteFieldElement(5,False,3)`.
            y (StackFiniteFieldElement): The position in the stack of `y` and whether `y` should be negated when used.
                Defaults to `StackFiniteFieldElement(2,False,3)`.
            rolling_options (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            Script to compute algebraic sum of two elements in F_q^3.

        Note:
            The function raises an assertion error if `x.extension_degree` or `y.extension_degree` are not equal to `3`.
        """
        assert x.extension_degree == self.EXTENSION_DEGREE, "x must have extension degree equal to 3."
        assert y.extension_degree == self.EXTENSION_DEGREE, "y must have extension degree equal to 3."

        is_x_rolled, is_y_rolled = bitmask_to_boolean_list(rolling_options, 2)

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Compute ± x2 ± y2
        # stack in:     [q, .., x, .., y, ..]
        # stack out:    [q, .., x, .., y, ..]
        # altstack out: [± x2 ± y2]
        out += self.base_field.algebraic_sum(
            take_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            x=x.extract_component(2),
            y=y.extract_component(2),
            rolling_options=rolling_options,
        )
        out += Script.parse_string("OP_TOALTSTACK")

        # Compute ± x1 ± y1
        # stack in:     [q, .., x, .., y, ..]
        # altstack in:  [± x2 ± y2]
        # stack out:    [q, .., x, .., y, ..]
        # altstack out: [± x2 ± y2, ±x1 ± y1]
        out += self.base_field.algebraic_sum(
            take_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            x=x.shift(-is_x_rolled - is_y_rolled).extract_component(1),
            y=y.shift(-is_y_rolled).extract_component(1),
            rolling_options=rolling_options,
        )
        out += Script.parse_string("OP_TOALTSTACK")

        # Compute ± x0 ± y0
        # stack in:     [q, .., x, .., y, ..]
        # altstack in:  [± x2 ± y2, ±x1 ± y1]
        # stack out:    [q, .., x, .., y, .., ± x0 ± y0]
        # altstack out: [± x2 ± y2, ±x1 ± y1]
        out += self.base_field.algebraic_sum(
            take_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            x=x.shift(-2 * is_x_rolled - 2 * is_y_rolled).extract_component(0),
            y=y.shift(-2 * is_y_rolled).extract_component(0),
            rolling_options=rolling_options,
        )

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo)
            out += mod(stack_preparation="OP_FROMALTSTACK OP_ROT", is_positive=positive_modulo)
            out += mod(
                stack_preparation="OP_FROMALTSTACK OP_ROT",
                is_positive=positive_modulo,
                is_constant_reused=is_constant_reused,
            )

        return out

    def add(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(5, False, 3),  # noqa: B008
        y: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 3),  # noqa: B008
        rolling_options: int = 3,
    ) -> Script:
        """Addition in F_q^3.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2), y := (y0, y1, y2)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x + y := (x0 + y0, x1 + y1, x2 + y2)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x` and whether `x` should be negated when used.
                Defaults to `StackFiniteFieldElement(5,False,3)`.
            y (StackFiniteFieldElement): The position in the stack of `y` and whether `y` should be negated when used.
                Defaults to `StackFiniteFieldElement(2,False,3)`.
            rolling_options (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            Script to add two elements in F_q^3.

        Note:
            The function raises an assertion error if:
                - `x.extension_degree` or `y.extension_degree` are not equal to `3`.
                - `x.negate` is `True` or `y.negate` is `True`
        """
        assert not x.negate, "x.negate should be False."
        assert not y.negate, "x.negate should be False."

        return self.algebraic_sum(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
            x=x,
            y=y,
            rolling_options=rolling_options,
        )

    def subtract(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(5, False, 3),  # noqa: B008
        y: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 3),  # noqa: B008
        rolling_options: int = 3,
    ) -> Script:
        """Addition in F_q^3.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2), y := (y0, y1, y2)]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x + y := (x0 + y0, x1 + y1, x2 + y2)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x` and whether `x` should be negated when used.
                Defaults to `StackFiniteFieldElement(5,False,3)`.
            y (StackFiniteFieldElement): The position in the stack of `y` and whether `y` should be negated when used.
                Defaults to `StackFiniteFieldElement(2,False,3)`.
            rolling_options (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            Script to add two elements in F_q^3.

        Note:
            The function raises an assertion error if:
                - `x.extension_degree` or `y.extension_degree` are not equal to `3`.
                - `x.negate` is `True` or `y.negate` is `True`
        """
        assert not x.negate, "x.negate should be False."
        assert not y.negate, "x.negate should be False."

        return self.algebraic_sum(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
            x=x,
            y=y.set_negate(True),
            rolling_options=rolling_options,
        )
