"""Bitcoin scripts that perform arithmetic operations in a cubic extension of F_q."""

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.fields.prime_field_extension import PrimeFieldExtension
from src.zkscript.types.stack_elements import StackFiniteFieldElement
from src.zkscript.util.utility_functions import check_order
from src.zkscript.util.utility_scripts import (
    bitmask_to_boolean_list,
    bool_to_moving_function,
    mod,
    move,
    nums_to_script,
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


class Fq3(PrimeFieldExtension):
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
        self.PRIME_FIELD = Fq(q)

    def fq_scalar_mul(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(3, False, 3),  # noqa: B008
        scalar: StackFiniteFieldElement = StackFiniteFieldElement(0, False, 1),  # noqa: B008
        rolling_options: int = 3,
    ) -> Script:
        """Addition in F_q^3.

        Stack input:
            - stack:    [q, .., x := (x0, x1, x2), .., scalar, ..]
            - altstack: []

        Stack output:
            - stack:    [q, ..., scalar * x := (scalar * x0, scalar * x1, scalar * x2)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            x (StackFiniteFieldElement): The position in the stack of `x` and whether `x`.
                Defaults to `StackFiniteFieldElement(3,False,3)`.
            scalar (StackFiniteFieldElement): The position in the stack of `scalar` and whether `scalar` should be
                negated when used. Defaults to `StackFiniteFieldElement(0,False,1)`.
            rolling_options (int): Bitmask detailing which of the elements `scalar` and `x` should be removed
                from the stack after execution. Defaults to `3` (remove everything).

        Returns:
            Script to multiply an element in F_q^3 by a scalar in F_q.

        Note:
            The function raises an assertion error if:
                - `scalar.extension_degree` is not `1`.
                - `x.extension_degree` is not `3`.
                - `x.negate` is `True`.
        """
        assert scalar.extension_degree == 1
        assert x.extension_degree == self.EXTENSION_DEGREE
        assert not x.negate
        check_order([x, scalar])

        is_scalar_rolled, is_x_rolled = bitmask_to_boolean_list(rolling_options, 2)
        is_default_position = (x == StackFiniteFieldElement(self.EXTENSION_DEGREE, False, self.EXTENSION_DEGREE)) and (
            scalar.position == 0
        )

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack in:     [q, .., x, .., scalar, ..]
        # stack out:    [q, .., x, .., scalar, .., scalar * x0]
        # altstack out: [scalar * x2, scalar * x1]
        out += move(scalar, bool_to_moving_function(is_scalar_rolled))  # Move scalar
        out += Script.parse_string("OP_NEGATE" if scalar.negate else "")
        if is_default_position:
            for i in range(self.EXTENSION_DEGREE):
                out += Script.parse_string("OP_TUCK" if i != self.EXTENSION_DEGREE - 1 else "")
                out += Script.parse_string("OP_MUL")  # Compute scalar * xi
                out += Script.parse_string("OP_TOALTSTACK" if i != self.EXTENSION_DEGREE - 1 else "")
        else:
            for i in range(self.EXTENSION_DEGREE):
                out += move(
                    x.shift(1 - i * is_x_rolled - is_scalar_rolled).extract_component(2 - i),
                    bool_to_moving_function(is_x_rolled),
                )  # Move xi
                out += Script.parse_string("OP_OVER" if i != self.EXTENSION_DEGREE - 1 else "")
                out += Script.parse_string("OP_MUL")  # Compute scalar * xi
                out += Script.parse_string("OP_TOALTSTACK" if i != self.EXTENSION_DEGREE - 1 else "")

        # stack in:     [q, .., x, .., scalar, .., scalar * x0]
        # altstack in:  [scalar * x2, scalar * x1]
        # stack out:    [q, .., x, .., scalar, .., scalar * x]
        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            for i in range(self.EXTENSION_DEGREE):
                out += mod(
                    stack_preparation="OP_FROMALTSTACK OP_ROT" if i != 0 else "",
                    is_positive=positive_modulo,
                    is_constant_reused=True if i != self.EXTENSION_DEGREE - 1 else is_constant_reused,
                )
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * (self.EXTENSION_DEGREE - 1)))

        return out

    def square(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        x: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 3),  # noqa: B008
        rolling_option: bool = True,
    ) -> Script:
        """Squaring in F_q^3.

        Stack input:
            - stack:    [q, ..., x := (x0, x1, x2), ..]
            - altstack: []

        Stack output:
            - stack:    [q, ..., x^2 := (
                            x0^2 + 2 * x1 * x2 * NON_RESIDUE,
                            x2^2 * NON_RESIDUE + 2 * x0 * x1,
                            x1^2 + 2 * x0 * x1
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
            rolling_option (bool): If `True`, `x` is removed from the stack after execution. Defaults to `True`.

        Returns:
            Script to compute square an element in F_q^3.

        Note:
            The function raises an assertion error if `x.extension_degree` is not equal to `3`.
        """
        assert x.extension_degree == self.EXTENSION_DEGREE

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack in:     [q, .., x, ..]
        # stack out:    [q, .., x, .., x1, x2, x0]
        # altstack out: [x1^2 + 2*x0*x2]
        if x.position == self.EXTENSION_DEGREE - 1:
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
        out += Script.parse_string("OP_TOALTSTACK")

        # stack in:    [q, .., x, .., x1, x2, x0]
        # altstack in: [x1^2 + 2*x0*x2]
        # stack out:    [q, .., x, .., x1, x2, x0]
        # altstack out: [x1^2 + 2*x0*x2, x2^2 * NON_RESIDUE + 2 * x0 * x1]
        out += Script.parse_string("OP_OVER OP_DUP")
        out += nums_to_script([self.NON_RESIDUE])
        out += Script.parse_string("OP_MUL OP_MUL")  # Compute x2^2 * NON_RESIDUE
        out += Script.parse_string("OP_OVER")
        out += pick(position=4, n_elements=1)  # Pick x1
        out += Script.parse_string("OP_2 OP_MUL OP_MUL OP_ADD")  # Compute x2^2 * NON_RESIDUE + 2 * x0 * x1
        out += Script.parse_string("OP_TOALTSTACK")

        # stack in:     [q, .., x, .., x1, x2, x0]
        # altstack in:  [x1^2 + 2*x0*x2, x2^2 * NON_RESIDUE + 2 * x0 * x1]
        # stack out:    [q, .., x, .., x0^2 + 2 * x1 * x2 * NON_RESIDUE]
        # altstack out: [x1^2 + 2*x0*x2, x2^2 * NON_RESIDUE + 2 * x0 * x1]
        out += Script.parse_string("OP_DUP OP_MUL OP_TOALTSTACK")
        out += Script.parse_string("OP_2") + nums_to_script([self.NON_RESIDUE])
        out += Script.parse_string(
            "OP_MUL OP_MUL OP_MUL OP_FROMALTSTACK OP_ADD"
        )  # Compute x0^2 + 2 * x1 * x2 * NON_RESIDUE

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            for i in range(self.EXTENSION_DEGREE):
                out += mod(
                    stack_preparation="OP_FROMALTSTACK OP_ROT" if i != 0 else "",
                    is_positive=positive_modulo,
                    is_constant_reused=True if i != self.EXTENSION_DEGREE - 1 else is_constant_reused,
                )
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * (self.EXTENSION_DEGREE - 1)))

        return out
