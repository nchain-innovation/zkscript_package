"""types package.

This package provides custom types.

Modules:
    - stack_elements: Represents individual elements on the stack such as Integers, Finite Field Elements,
        Elliptic Curve points, with properties like `position`, `length`, `extension degree`.
    - locking_keys: Classes that encapsulate data required to generate locking scripts.
    - unlocking_keys: Classes that encapsulate data required to generate unlocking scripts.

Usage example:
    Representing an Elliptic Curve point on the stack `P = (x,y)`, where `x`, `y` are in F_q, that should not be
    negated when used in a script, and that is positioned as follows on the stack [..., x, y, a, b]:

    >>> from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
    >>>
    >>> point_p = StackEllipticCurvePoint(
    ...     StackFiniteFieldElement(position=3,negate=False,extension_degree=1),
    ...     StackFiniteFieldElement(position=2,negate=False,extension_degree=1)
    ... )
"""
