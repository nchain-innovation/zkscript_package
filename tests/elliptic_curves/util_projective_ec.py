from copy import deepcopy

from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.models.ec import ShortWeierstrassEllipticCurve, ShortWeierstrassEllipticCurvePoint

def add(lhs: list[PrimeField], rhs: list[PrimeField], field: PrimeField) -> list[PrimeField]:
    # lhs = [x, y, z]
    u = lhs[2] * rhs[1] - lhs[1] * rhs[2] # y2 * z1 - y1 * z2
    v = lhs[2] * rhs[0] - lhs[0] * rhs[2] # x2 * z1 - x1 * z2
    a = u * u * lhs[2] * rhs[2] - v * v * v - field(2) * v * v * lhs[0] * rhs[2]

    return [
        v * a,
        u * (v * v * lhs[0] * rhs[2] - a) - v * v * v * lhs[1] * rhs[2],
        v * v * v * lhs[2] * rhs[2]
    ]

def double(self: list[PrimeField], curve: ShortWeierstrassEllipticCurve, field: PrimeField) -> list[PrimeField]:
    s = self[1] * self[2]
    B = self[0] * self[1] * s
    w = curve.a * self[2].power(2) + self[0].power(2) * field(3)
    h = w.power(2) - B * field(8)

    return [
        h * s * field(2),
        w * (B * field(4) - h) - s.power(2) * self[1].power(2) * field(8),
        s.power(3) * field(8)
    ]

def multiply(self: list[PrimeField], scalar: int, curve: ShortWeierstrassEllipticCurve, field: PrimeField) -> list[PrimeField]:
    exp_scalar = [int(bin(scalar)[j]) for j in range(2, len(bin(scalar)))]
    T = deepcopy(self)

    for e in exp_scalar[1:]:
        T = double(T, curve, field)
        if e == 1:
            T = add(self, T, field)
        
    return T

def negate(self: list[PrimeField]) -> list[PrimeField]:
    return [
        self[0],
        -self[1],
        self[2]
    ]

def to_proj(point: ShortWeierstrassEllipticCurvePoint, field: PrimeField) -> list[PrimeField]:
    return [
        point.x,
        point.y,
        field.identity()
    ]

def to_aff(point: list[PrimeField], curve: ShortWeierstrassEllipticCurve, field: PrimeField) -> ShortWeierstrassEllipticCurvePoint:
    return curve(
        point[0] * point[2].invert(),
        point[1] * point[2].invert(),
        False,
    ) if not point[2].is_zero() else curve(
        field.identity(),
        field.identity(),
        True
    )

def proj_to_list(point):
    return [element.to_int() for element in point]