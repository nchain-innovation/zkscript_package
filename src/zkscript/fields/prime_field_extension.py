"""Bitcoin scripts that perform arithmetic operations in F_q^n."""

from tx_engine import Script

from src.zkscript.types.stack_elements import StackFiniteFieldElement
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


class PrimeFieldExtension:
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^n.

    The class inheriting from this class is assumed to have the following attributes:
        MODULUS: The characteristic of the prime field F_q.
        EXTENSION_DEGREE: The extension degree of the field extension,i.e., n.
        PRIME_FIELD: The script implementation of the prime field F_q.
    """

    def __algebraic_sum_leaving_result_on_altstack(
        self,
        x: StackFiniteFieldElement,
        y: StackFiniteFieldElement,
        rolling_options: int = 3,
    ) -> Script:
        """Algebraic addition in F_q^n, where n = x.extension_degree = y.extension_degree leaving result on altstack.

        Stack input:
            - stack:    [q, ..., x := (x0, .., xn), .., y := (y0, .., yn), ..]
            - altstack: []

        Stack output:
            - stack:    [q, ..., ± x0 ± y0]
            - altstack: [± xn ± yn, .., ± x1 ± y1]

        Args:
            x (StackFiniteFieldElement): The position in the stack of `x` and whether `x` should be negated when used.
            y (StackFiniteFieldElement): The position in the stack of `y` and whether `y` should be negated when used.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            rolling_options (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            Script to compute algebraic sum of two elements in F_q^n, leaving the result (except the first coordinate)
            on the altstack.

        Notes:
            The function returns an asssertion error if `x.extension_degree != y.extension_degree`
        """
        assert x.extension_degree == y.extension_degree, "x and y must have the same extension degree."
        is_x_rolled, is_y_rolled = bitmask_to_boolean_list(rolling_options, 2)
        is_extension_degree_two = x.extension_degree == 2
        is_y_on_top = y.position == y.extension_degree - 1
        # Default config: x, y rolled and on top of the stack
        is_default_config = (x.position == 2 * x.extension_degree - 1) and is_y_on_top and is_x_rolled and is_y_rolled
        # Config for x.extension_degree == 2, x.position = 5, y on top, x, y rolled
        is_extension_degree_two_special_config = (
            is_extension_degree_two
            and is_y_on_top
            and x.position == 3 * x.extension_degree - 1
            and is_x_rolled
            and is_y_rolled
        )

        out = Script()

        # stack in:     [q, .., x, .., y, ..]
        # stack out:    [q, .., x, .., y, .., ± x0 ± y0]
        # altstack out: [± xn ± yn, .., ± x1 ± y1]
        if is_default_config:
            match x.extension_degree:
                case 2 | 3:
                    for i in range(x.extension_degree):
                        out += self.PRIME_FIELD.algebraic_sum(
                            take_modulo=False,
                            check_constant=False,
                            clean_constant=False,
                            is_constant_reused=False,
                            x=x.shift(-i * (is_x_rolled + is_y_rolled)).extract_component(x.extension_degree - 1 - i),
                            y=y.shift(-i * is_y_rolled).extract_component(x.extension_degree - 1 - i),
                            rolling_options=3,
                        )
                        out += Script.parse_string("OP_TOALTSTACK" if i != x.extension_degree - 1 else "")
                case 4:
                    out += move(x, bool_to_moving_function(is_x_rolled), start_index=2, end_index=4)
                    for j in range(x.extension_degree):
                        negate = [y.negate, x.negate] if j <= 1 else [x.negate, y.negate]
                        out += self.PRIME_FIELD.algebraic_sum(
                            take_modulo=False,
                            check_constant=False,
                            clean_constant=False,
                            is_constant_reused=False,
                            x=StackFiniteFieldElement(2 - (j % 2), negate[0], 1),
                            y=StackFiniteFieldElement(0, negate[1], 1),
                            rolling_options=3,
                        )
                        out += Script.parse_string("OP_TOALTSTACK" if j != x.extension_degree - 1 else "")
                case 6:
                    out += move(x, bool_to_moving_function(is_x_rolled), start_index=4, end_index=6)
                    out += self.__algebraic_sum_leaving_result_on_altstack(
                        x=StackFiniteFieldElement(3, y.negate, 2),
                        y=StackFiniteFieldElement(1, x.negate, 2),
                        rolling_options=3,
                    )
                    out += Script.parse_string("OP_TOALTSTACK")
                    out += self.__algebraic_sum_leaving_result_on_altstack(
                        x=StackFiniteFieldElement(x.shift(-4).position, x.negate, 4),
                        y=StackFiniteFieldElement(y.shift(-2).position, y.negate, 4),
                        rolling_options=3,
                    )
                case _:
                    remainder = min(6, x.extension_degree - 1)  # Either 6 or 4
                    out += self.__algebraic_sum_leaving_result_on_altstack(
                        x=StackFiniteFieldElement(x.position - remainder, x.negate, x.extension_degree - remainder),
                        y=StackFiniteFieldElement(y.position - remainder, y.negate, x.extension_degree - remainder),
                        rolling_options=3,
                    )
                    out += Script.parse_string("OP_TOALTSTACK")
                    out += self.__algebraic_sum_leaving_result_on_altstack(
                        x=StackFiniteFieldElement(
                            x.shift(-x.extension_degree + remainder).position, x.negate, remainder
                        ),
                        y=StackFiniteFieldElement(
                            y.shift(-y.extension_degree + remainder).position, y.negate, remainder
                        ),
                        rolling_options=3,
                    )
        elif is_extension_degree_two_special_config:
            out += move(x, roll)
            out += self.__algebraic_sum_leaving_result_on_altstack(
                x=StackFiniteFieldElement(2 * y.extension_degree - 1, y.negate, y.extension_degree),
                y=StackFiniteFieldElement(x.extension_degree - 1, x.negate, x.extension_degree),
                rolling_options=3,
            )
        else:
            for i in range(x.extension_degree):
                out += self.PRIME_FIELD.algebraic_sum(
                    take_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    x=x.shift(-i * (is_x_rolled + is_y_rolled)).extract_component(x.extension_degree - 1 - i),
                    y=y.shift(-i * is_y_rolled).extract_component(x.extension_degree - 1 - i),
                    rolling_options=rolling_options,
                )
                out += Script.parse_string("OP_TOALTSTACK" if i != x.extension_degree - 1 else "")

        return out

    def algebraic_sum(
        self,
        x: StackFiniteFieldElement,
        y: StackFiniteFieldElement,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        rolling_options: int = 3,
    ) -> Script:
        """Algebraic addition in F_q^n.

        Stack input:
            - stack:    [q, ..., x := (x0, .., xn), .., y := (y0, .., yn), ..]
            - altstack: []

        Stack output:
            - stack:    [q, ..., ± x ± y := (± x0 ± y0, .., ± xn ± yn)]
            - altstack: []

        Args:
            x (StackFiniteFieldElement): The position in the stack of `x` and whether `x` should be negated when used.
            y (StackFiniteFieldElement): The position in the stack of `y` and whether `y` should be negated when used.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            rolling_options (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            Script to compute algebraic sum of two elements in F_q^n.

        Note:
            The function raises an assertion error if `x.extension_degree` or `y.extension_degree` are not equal to `n`.
        """
        assert (
            x.extension_degree == self.EXTENSION_DEGREE
        ), f"x must have extension degree equal to {self.EXTENSION_DEGREE}"
        assert (
            y.extension_degree == self.EXTENSION_DEGREE
        ), f"y must have extension degree equal to {self.EXTENSION_DEGREE}"
        check_order([x, y])

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack in:     [q, .., x, .., y, ..]
        # stack out:    [q, .., x, .., y, .., ± x0 ± y0]
        # altstack out: [± xn ± yn, .., ± x1 ± y1]
        out += self.__algebraic_sum_leaving_result_on_altstack(x=x, y=y, rolling_options=rolling_options)

        out += (
            self.take_modulo(
                positive_modulo=positive_modulo, clean_constant=clean_constant, is_constant_reused=is_constant_reused
            )
            if take_modulo
            else Script.parse_string(" ".join(["OP_FROMALTSTACK"] * (self.EXTENSION_DEGREE - 1)))
        )

        return out

    def add(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement | None = None,
        y: StackFiniteFieldElement | None = None,
        rolling_options: int = 3,
    ) -> Script:
        """Addition in F_q^n.

        Stack input:
            - stack:    [q, ..., x := (x0, .., xn), .., y := (y0, .., yn), ..]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x + y := (x0 + y0, .., xn + yn)]
            - altstack: []

        Args:
            x (StackFiniteFieldElement): The position in the stack of `x`.
            y (StackFiniteFieldElement): The position in the stack of `y`.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            rolling_options (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            Script to add two elements in F_q^n.

        Note:
            The function raises an assertion error if:
                - `x.extension_degree` or `y.extension_degree` are not equal to `n`.
                - `x.negate` is `True` or `y.negate` is `True`
        """
        x = x if x is not None else StackFiniteFieldElement(2 * self.EXTENSION_DEGREE - 1, False, self.EXTENSION_DEGREE)
        y = y if y is not None else StackFiniteFieldElement(self.EXTENSION_DEGREE - 1, False, self.EXTENSION_DEGREE)
        assert not x.negate, "x.negate should be False."
        assert not y.negate, "x.negate should be False."

        return self.algebraic_sum(
            x=x,
            y=y,
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
            rolling_options=rolling_options,
        )

    def subtract(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement | None = None,
        y: StackFiniteFieldElement | None = None,
        rolling_options: int = 3,
    ) -> Script:
        """Subtraction in F_q^n.

        Stack input:
            - stack:    [q, ..., x := (x0, .., xn), .., y := (y0, .., yn), ..]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x + y := (x0 - y0, .., xn - yn)]
            - altstack: []

        Args:
            x (StackFiniteFieldElement): The position in the stack of `x`.
            y (StackFiniteFieldElement): The position in the stack of `y`.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            rolling_options (int): Bitmask detailing which of the elements `x` and `y` should be removed from the stack
                after execution. Defaults to `3` (remove everything).

        Returns:
            Script to subtract two elements in F_q^n.

        Note:
            The function raises an assertion error if:
                - `x.extension_degree` or `y.extension_degree` are not equal to `n`.
                - `x.negate` is `True` or `y.negate` is `True`
        """
        x = x if x is not None else StackFiniteFieldElement(2 * self.EXTENSION_DEGREE - 1, False, self.EXTENSION_DEGREE)
        y = y if y is not None else StackFiniteFieldElement(self.EXTENSION_DEGREE - 1, False, self.EXTENSION_DEGREE)
        assert not x.negate, "x.negate should be False."
        assert not y.negate, "x.negate should be False."

        return self.algebraic_sum(
            x=x,
            y=y.set_negate(True),
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=check_constant,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
            rolling_options=rolling_options,
        )

    def base_field_scalar_mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement | None = None,
        scalar: StackFiniteFieldElement | None = None,
        rolling_options: int = 3,
    ) -> Script:
        """Multiplication in F_q^n by a scalar in F_q.

        Stack input:
            - stack:    [q, ..., x := (x0, .., xn), .., scalar, ..], `x` is an element in F_q^n, `scalar` is
                an element of F_q
            - altstack: []

        Stack output:
            - stack:    [q, ..., x * scalar]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x`.
            scalar (StackFiniteFieldElement): The position in the stack of `scalar`.
            rolling_options (int): Bitmask detailing which of the elements `x` and `scalar` should be removed from the
                stack after execution. Defaults to `3` (remove everything).

        Returns:
            Script to multiply an element `x` in F_q^n by a scalar `scalar` in F_q.
        """
        x = x if x is not None else StackFiniteFieldElement(self.EXTENSION_DEGREE, False, self.EXTENSION_DEGREE)
        scalar = scalar if scalar is not None else StackFiniteFieldElement(0, False, 1)
        assert scalar.extension_degree == 1, "The extension degree of `scalar` must be 1."
        check_order([x, scalar])

        is_scalar_rolled, is_x_rolled = bitmask_to_boolean_list(rolling_options, 2)
        is_default_config = (x.position == self.EXTENSION_DEGREE) and (scalar.position == 0)

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack out:    [.., x, .., scalar, x0 * scalar]
        # altstack out: [xn * scalar, .., x1 * scalar]
        if is_default_config:
            out += Script.parse_string("OP_NEGATE") if scalar.negate else Script()
            for _ in range(self.EXTENSION_DEGREE - 1):
                out += Script.parse_string("OP_TUCK OP_MUL OP_TOALTSTACK")
            out += Script.parse_string("OP_MUL")
        else:
            out += move(scalar, bool_to_moving_function(is_scalar_rolled))  # Move scalar
            out += Script.parse_string("OP_NEGATE") if scalar.negate else Script()
            for i in range(self.EXTENSION_DEGREE - 1, -1, -1):
                out += move(
                    x.shift(1 - is_scalar_rolled - (self.EXTENSION_DEGREE - 1 - i) * is_x_rolled).extract_component(i),
                    bool_to_moving_function(is_x_rolled),
                )  # Move x[i]
                out += Script.parse_string("OP_OVER OP_MUL OP_TOALTSTACK" if i != 0 else "OP_MUL OP_TOALTSTACK")

        out += (
            self.take_modulo(
                positive_modulo=positive_modulo, clean_constant=clean_constant, is_constant_reused=is_constant_reused
            )
            if take_modulo
            else Script.parse_string(" ".join(["OP_FROMALTSTACK"] * (self.EXTENSION_DEGREE - 1)))
        )

        return out

    def take_modulo(
        self,
        positive_modulo: bool = True,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Perform modulo operation in F_q^n.

        Stack input:
            - stack:    [q, ..., x0]
            - altstack: [xn, .., x1]

        Stack output:
            - stack:    [q, ..., x0 % q, x1 % q, .., xn % q]
            - altstack: []
        """
        out = Script()
        out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
        out += mod(stack_preparation="", is_positive=positive_modulo)
        for _ in range(self.EXTENSION_DEGREE - 2):
            out += mod(stack_preparation="OP_FROMALTSTACK OP_ROT", is_positive=positive_modulo)
        out += mod(
            stack_preparation="OP_FROMALTSTACK OP_ROT",
            is_positive=positive_modulo,
            is_constant_reused=is_constant_reused,
        )

        return out
