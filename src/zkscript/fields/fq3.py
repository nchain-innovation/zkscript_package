"""Bitcoin scripts that perform arithmetic operations in a cubic extension of F_q."""

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.fields.prime_field_extension import PrimeFieldExtension
from src.zkscript.script_types.stack_elements import StackFiniteFieldElement
from src.zkscript.util.utility_scripts import (
    bitmask_to_boolean_list,
    bool_to_moving_function,
    move,
    nums_to_script,
    pick,
    verify_bottom_constant,
)


class Fq3(PrimeFieldExtension):
    """Construct Bitcoin scripts that perform arithmetic operations in F_q^3 = F_q[u] / (u^3 - non_residue).

    F_q^3 = F_q[u] / (u^3 - non_residue) is a cubic extension of a base field F_q.

    Elements in F_q^3 are of the form `x0 + x1 * u + x2 * u^2`, where `x0`, `x1`, and `x2` are elements of F_q,
    and `u^3` is equal to some `non_residue` in F_q.

    Attributes:
        modulus: The characteristic of the base field F_q.
        non_residue: The non-residue element used to define the cubic extension.
        extension_degree: The extension degree over the prime field, equal to 3.
        prime_field: The Bitcoin Script implementation of the prime field F_q.
    """

    def __init__(self, q: int, non_residue: int):
        """Initialise F_q^3, the cubic extension of F_q.

        Args:
            q: The characteristic of the base field F_q.
            non_residue: The non-residue element used to define the cubic extension.
        """
        self.modulus = q
        self.non_residue = non_residue
        self.extension_degree = 3
        self.prime_field = Fq(q)

    def square(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 3),  # noqa: B008
        scalar: int = 1,
        rolling_option: bool = True,
    ) -> Script:
        """Squaring in F_q^3 followed by scalar multiplication.

        The script computes the operation x^2 --> scalar * x^2, where scalar is in Fq.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2), ..]
            - altstack: []

        Stack output:
            - stack:    [q, ..., scalar * x^2 := (
                            scalar * (x0^2 + 2 * x1 * x2 * non_residue),
                            scalar * (x2^2 * non_residue + 2 * x0 * x1),
                            scalar * (x1^2 + 2 * x0 * x1)
                            )]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x`.
                Defaults to `StackFiniteFieldElement(2,False,3)`.
            scalar (int): The scalar to multiply the result by. Defaults to 1.
            rolling_option (bool): If `True`, `x` is removed from the stack after execution. Defaults to `True`.

        Returns:
            Script to compute square an element in F_q^3 and rescale the result.

        Note:
            The function raises an assertion error if `x.extension_degree` is not equal to `3`.
        """
        assert x.extension_degree == self.extension_degree

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:     [q, .., x, ..]
        # stack out:    [q, .., x, .., x1, x2, x0]
        # altstack out: [scalar * (x1^2 + 2*x0*x2)]
        if x.position == self.extension_degree - 1:
            out += move(x.extract_component(1), pick)  # Pick x1
            out += Script.parse_string("OP_DUP OP_MUL")  # Compute x1^2
            out += move(x.shift(1).extract_component(2), pick)  # Pick x2
            out += move(x.shift(2).extract_component(0), bool_to_moving_function(rolling_option))  # Move x0
        else:
            out += move(x.extract_component(1), bool_to_moving_function(rolling_option))  # Move x1
            out += Script.parse_string("OP_DUP OP_DUP OP_MUL")  # Compute x1^2
            out += move(x.shift(2).extract_component(2), bool_to_moving_function(rolling_option))  # Pick x2
            out += move(
                x.shift(3 - 2 * rolling_option).extract_component(0), bool_to_moving_function(rolling_option)
            )  # Move x0
        out += Script.parse_string("OP_TUCK OP_2 OP_MUL OP_MUL OP_ROT OP_ADD")  # Compute x1^2 + 2*x0*x2
        if scalar != 1:
            out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK")

        # stack in:     [q, .., x, .., x1, x2, x0]
        # altstack in:  [x1^2 + 2*x0*x2]
        # stack out:    [q, .., x, .., x1, x2, x0]
        # altstack out: [scalar * (x1^2 + 2*x0*x2), scalar * (x2^2 * non_residue + 2 * x0 * x1)]
        out += Script.parse_string("OP_OVER OP_DUP")
        out += nums_to_script([self.non_residue])
        out += Script.parse_string("OP_MUL OP_MUL")  # Compute x2^2 * non_residue
        out += Script.parse_string("OP_OVER")
        out += pick(position=4, n_elements=1)  # Pick x1
        out += Script.parse_string("OP_2 OP_MUL OP_MUL OP_ADD")  # Compute x2^2 * non_residue + 2 * x0 * x1
        if scalar != 1:
            out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK")

        # stack in:     [q, .., x, .., x1, x2, x0]
        # altstack in:  [scalar * (x1^2 + 2*x0*x2), scalar * (x2^2 * non_residue + 2 * x0 * x1)]
        # stack out:    [q, .., x, .., scalar * (x0^2 + 2 * x1 * x2 * non_residue)]
        # altstack out: [scalar * (x1^2 + 2*x0*x2), scalar* (x2^2 * non_residue + 2 * x0 * x1)]
        out += Script.parse_string("OP_DUP OP_MUL OP_TOALTSTACK")
        out += Script.parse_string("OP_2") + nums_to_script([self.non_residue])
        out += Script.parse_string(
            "OP_MUL OP_MUL OP_MUL OP_FROMALTSTACK OP_ADD"
        )  # Compute x0^2 + 2 * x1 * x2 * non_residue
        if scalar != 1:
            out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")

        out += (
            self.take_modulo(
                positive_modulo=positive_modulo, clean_constant=clean_constant, is_constant_reused=is_constant_reused
            )
            if take_modulo
            else Script.parse_string(" ".join(["OP_FROMALTSTACK"] * (self.extension_degree - 1)))
        )

        return out

    def mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(5, False, 3),  # noqa: B008
        y: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 3),  # noqa: B008
        scalar: int = 1,
        rolling_options: int = 3,
    ) -> Script:
        """Multiplication in F_q^3 followed by scalar multiplication.

        The script computes the operation (x, y) --> scalar * x * y, where scalar is in Fq.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2), .., y := (y0, y1, y2), ..]
            - altstack: []

        Stack output:
            - stack:    [q, ..., scalar * x * y := (
                            scalar * (x0 * y0 + (x1 * y2 + x2 * y1) * non_residue),
                            scalar * (x2 * y2 * non_residue + x0 * x1 + y1 * y0),
                            scalar * (x1 * y1 + x0 * y2 + x2 * y0)
                            )]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x`.
                Defaults to `StackFiniteFieldElement(5,False,3)`.
            y (StackFiniteFieldElement): The position in the stack of `y`.
                Defaults to `StackFiniteFieldElement(2,False,3)`.
            scalar (int): The scalar to multiply the result by. Defaults to 1.
            rolling_options (int): Bitmaks detailing which of `x` and `y` should be removed after the execution of the
                script. Defaults to `3` (remove everything).

        Returns:
            Script to multiply two elements in F_q^3 and rescale the result.

        Note:
            The function raises an assertion error if `x.extension_degree` and `y.extension_degree`
            are not equal to `3`.
        """
        assert x.extension_degree == self.extension_degree
        assert y.extension_degree == self.extension_degree

        is_x_rolled, is_y_rolled = bitmask_to_boolean_list(rolling_options, 2)

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:     [q, .., x, .., y, ..]
        # stack out:    [q, .., x, .., y, .., ]
        # altstack out: [scalar * (x1 * y1 + x0 * y2 + x2 * y0)]
        out += move(y.extract_component(2), pick)
        out += move(x.shift(1).extract_component(0), pick)
        out += Script.parse_string("OP_MUL")

        out += move(y.shift(1).extract_component(1), pick)
        out += move(x.shift(2).extract_component(1), pick)
        out += Script.parse_string("OP_MUL OP_ADD")

        out += move(y.shift(1).extract_component(0), pick)
        out += move(x.shift(2).extract_component(2), pick)
        out += Script.parse_string("OP_MUL OP_ADD")
        if scalar != 1:
            out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK")

        # stack in:     [q, .., x, .., y, ..]
        # stack out:    [q, .., x, .., y, .., ]
        # altstack out: [scalar* (x1 * y1 + x0 * y2 + x2 * y0), scalar * (x0 * y1 + x1 * y0 + x2 * y2 * non_residue)]
        out += move(y.extract_component(2), pick)
        out += move(x.shift(1).extract_component(2), pick)
        out += Script.parse_string("OP_MUL")
        out += nums_to_script([self.non_residue])
        out += Script.parse_string("OP_MUL")

        out += move(y.shift(1).extract_component(1), pick)
        out += move(x.shift(2).extract_component(0), pick)
        out += Script.parse_string("OP_MUL OP_ADD")

        out += move(y.shift(1).extract_component(0), pick)
        out += move(x.shift(2).extract_component(1), pick)
        out += Script.parse_string("OP_MUL OP_ADD")
        if scalar != 1:
            out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")
        out += Script.parse_string("OP_TOALTSTACK")

        # stack in:     [q, .., x, .., y, ..]
        # stack out:    [q, .., x, .., y, .., ]
        # altstack out: [scalar * (x1 * y1 + x0 * y2 + x2 * y0), scalar * (x0 * y1 + x1 * y0 + x2 * y2 * non_residue),
        #                   scalar * (x0 * y0 + non_residue * (x1 * y2 + x2 * y1))]
        out += move(y.extract_component(2), bool_to_moving_function(is_y_rolled))
        out += move(x.shift(1 - is_y_rolled).extract_component(1), bool_to_moving_function(is_x_rolled))
        out += Script.parse_string("OP_MUL")

        out += move(y.shift(1 - is_y_rolled).extract_component(1), bool_to_moving_function(is_y_rolled))
        out += move(x.shift(2 - 2 * is_y_rolled).extract_component(2), bool_to_moving_function(is_x_rolled))
        out += Script.parse_string("OP_MUL OP_ADD")
        out += nums_to_script([self.non_residue])
        out += Script.parse_string("OP_MUL")

        out += move(y.shift(1 - 2 * is_y_rolled).extract_component(0), bool_to_moving_function(is_y_rolled))
        out += move(
            x.shift(2 - 3 * is_y_rolled - 2 * is_x_rolled).extract_component(0), bool_to_moving_function(is_x_rolled)
        )
        out += Script.parse_string("OP_MUL OP_ADD")
        if scalar != 1:
            out += nums_to_script([scalar]) + Script.parse_string("OP_MUL")

        out += (
            self.take_modulo(
                positive_modulo=positive_modulo, clean_constant=clean_constant, is_constant_reused=is_constant_reused
            )
            if take_modulo
            else Script.parse_string(" ".join(["OP_FROMALTSTACK"] * (self.extension_degree - 1)))
        )

        return out
