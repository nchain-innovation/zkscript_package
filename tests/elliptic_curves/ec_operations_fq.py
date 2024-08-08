import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tx_engine import Script, Context

from elliptic_curves.models.ec import elliptic_curve_from_curve
from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.models.curve import Curve

from zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from zkscript.util.utility_scripts import nums_to_script

secp256k1_MODULUS = 115792089237316195423570985008687907853269984665640564039457584007908834671663
secp256k1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Fq_k1 = base_field_from_modulus(q=secp256k1_MODULUS)
Fr_k1 = base_field_from_modulus(q=secp256k1_ORDER)
secp256k1, _ = elliptic_curve_from_curve(curve=Curve(a=Fq_k1(0),b=Fq_k1(7)))
secp256k1_generator = secp256k1(
    x = Fq_k1(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798),
    y = Fq_k1(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
)

secp256r1_MODULUS = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff 
secp256r1_ORDER = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
Fq_r1 = base_field_from_modulus(q=secp256r1_MODULUS)
Fr_r1 = base_field_from_modulus(q=secp256r1_ORDER)
secp256r1, _ = elliptic_curve_from_curve(
    curve=Curve(
        a=Fq_r1(0xffffffff00000001000000000000000000000000fffffffffffffffffffffffc),
        b=Fq_r1(0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b)
        )
    )
secp256r1_generator = secp256r1(
    x = Fq_r1(0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296),
    y = Fq_r1(0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)
)

secp256k1_script = EllipticCurveFq(q=secp256k1_MODULUS,curve_a=0)
secp256r1_script = EllipticCurveFq(q=secp256r1_MODULUS,curve_a=0xffffffff00000001000000000000000000000000fffffffffffffffffffffffc)

# Utility functions for the tests
def generate_verify(P) -> Script:
    out = Script()
    if not P.is_infinity():
        for ix, el in enumerate(P.to_list()[::-1]):
            out += nums_to_script([el])
            if ix != len(P.to_list())-1:
                out += Script.parse_string('OP_EQUALVERIFY')
            else:
                out += Script.parse_string('OP_EQUAL')
    else:
        out += Script.parse_string('0x00 OP_EQUALVERIFY 0x00 OP_EQUAL')
    return out

def generate_unlock(P) -> Script:
    out = Script()
    if not P.is_infinity():
        out += nums_to_script(P.to_list())
    else:
        out += Script.parse_string('0x00 0x00')
    return out

# Json dictionary of the outputs
tests = [
    'point addition',
    'point doubling a = 0',
    'point doubling a != 0',
    'point addition with unknown points, a = 0',
    'point addition with unknown points, a != 0'
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

# ------------------------------------

def test_point_addition():
    P = secp256k1_generator.multiply(Fr_k1.generate_random_point().to_list()[0])
    Q = secp256k1_generator.multiply(Fr_k1.generate_random_point().to_list()[0])
    R = P+Q
    
    lam = P.get_lambda(Q)

    unlock = nums_to_script([secp256k1_MODULUS])
    unlock += nums_to_script(lam.to_list())
    unlock += generate_unlock(P)
    unlock += generate_unlock(Q)

    lock = secp256k1_script.point_addition(take_modulo=True,check_constant=True,clean_constant=True)
    lock += generate_verify(R)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock)
    # Wrong constant
    assert(not(context_wrong.evaluate(quiet=True)))

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    print('Point addition: \t\t\t\t test successfull')

    return

def test_point_doubling_a_equal_zero():
    P = secp256k1_generator.multiply(Fr_k1.generate_random_point().to_list()[0])
    R = P + P
    
    lam = P.get_lambda(P)

    unlock = nums_to_script([secp256k1_MODULUS])
    unlock += nums_to_script(lam.to_list())
    unlock += generate_unlock(P)

    lock = secp256k1_script.point_doubling(take_modulo=True,check_constant=True,clean_constant=True)
    lock += generate_verify(R)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock)
    # Wrong constant
    assert(not(context_wrong.evaluate(quiet=True)))

    # Save scripts
    scripts[tests[1]][type_of_script[0]] = unlock
    scripts[tests[1]][type_of_script[1]] = lock

    print('Point doubling a = 0:\t\t\t\t test successfull')

    return

def test_point_doubling_a_not_zero():
    P = secp256r1_generator.multiply(Fr_r1.generate_random_point().to_list()[0])
    R = P + P
    
    lam = P.get_lambda(P)

    unlock = nums_to_script([secp256r1_MODULUS])
    unlock += nums_to_script(lam.to_list())
    unlock += generate_unlock(P)

    lock = secp256r1_script.point_doubling(take_modulo=True,check_constant=True,clean_constant=True)
    lock += generate_verify(R)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock)
    # Wrong constant
    assert(not(context_wrong.evaluate(quiet=True)))

    # Save scripts
    scripts[tests[2]][type_of_script[0]] = unlock
    scripts[tests[2]][type_of_script[1]] = lock

    print('Point doubling a != 0:\t\t\t\t test successfull')

    return

def test_addition_unknown_points_a_equal_zero():
    for i in range(5):
        unlock = nums_to_script([secp256k1_MODULUS])
    
        if i < 1:
            P = secp256k1_generator.multiply(Fr_k1.generate_random_point().to_list()[0])
            Q = secp256k1_generator.multiply(Fr_k1.generate_random_point().to_list()[0])
            R = P + Q
    
            lam = P.get_lambda(Q)
    
            unlock += nums_to_script(lam.to_list())
        elif i < 2:
            P = secp256k1_generator.multiply(Fr_k1.generate_random_point().to_list()[0])
            Q = -P
            R = secp256k1.point_at_infinity()
        elif i < 3:
            P = secp256k1_generator.multiply(Fr_k1.generate_random_point().to_list()[0])
            Q = secp256k1.point_at_infinity()
            R = P
        else:
            P = secp256k1.point_at_infinity()
            Q = secp256k1_generator.multiply(Fr_k1.generate_random_point().to_list()[0])
            R = Q
        
        unlock += generate_unlock(P)
        unlock += generate_unlock(Q)
    
        lock = secp256k1_script.point_addition_with_unknown_points(take_modulo=True,check_constant=True,clean_constant=True)
        lock += generate_verify(R)
    
        context = Context(script = unlock + lock)
        assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)
    
        unlock_wrong = Script.parse_string('OP_10') + unlock
        context_wrong = Context(script = unlock_wrong + lock)
        # Wrong constant
        assert(not(context_wrong.evaluate(quiet=True)))

        if i < 1:
            # Save scripts
            scripts[tests[3]][type_of_script[0]] = unlock
            scripts[tests[3]][type_of_script[1]] = lock
    
    print('Point addition w/ unknown points, a = 0: \t test successfull')
    
    return

def test_addition_unknown_points_a_not_zero():
    for i in range(5):
        unlock = nums_to_script([secp256r1_MODULUS])
    
        if i < 1:
            P = secp256r1_generator.multiply(Fr_r1.generate_random_point().to_list()[0])
            Q = secp256r1_generator.multiply(Fr_r1.generate_random_point().to_list()[0])
            R = P + Q
    
            lam = P.get_lambda(Q)
    
            unlock += nums_to_script(lam.to_list())
        elif i < 2:
            P = secp256r1_generator.multiply(Fr_r1.generate_random_point().to_list()[0])
            Q = -P
            R = secp256r1.point_at_infinity()
        elif i < 3:
            P = secp256r1_generator.multiply(Fr_r1.generate_random_point().to_list()[0])
            Q = secp256r1.point_at_infinity()
            R = P
        else:
            P = secp256r1.point_at_infinity()
            Q = secp256r1_generator.multiply(Fr_r1.generate_random_point().to_list()[0])
            R = Q
        
        unlock += generate_unlock(P)
        unlock += generate_unlock(Q)
    
        lock = secp256r1_script.point_addition_with_unknown_points(take_modulo=True,check_constant=True,clean_constant=True)
        lock += generate_verify(R)

        context = Context(script = unlock + lock)
        assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)
    
        unlock_wrong = Script.parse_string('OP_10') + unlock
        context_wrong = Context(script = unlock_wrong + lock)
        # Wrong constant
        assert(not(context_wrong.evaluate(quiet=True)))

        if i < 1:
            # Save scripts
            scripts[tests[4]][type_of_script[0]] = unlock
            scripts[tests[4]][type_of_script[1]] = lock
    
    print('Point addition w/ unknown points, a != 0: \t test successfull')
    
    return

parser = argparse.ArgumentParser("EC arithmetic over Fq")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

print('\nBegin tests EC arithmetic over Fq -------------------\n')

test_point_addition()
test_point_doubling_a_equal_zero()
test_point_doubling_a_not_zero()
test_addition_unknown_points_a_equal_zero()
test_addition_unknown_points_a_not_zero()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/ec_arithmetic_fq.json','w')
    json.dump(scripts, outfile)

print('\nEC arithmetic over Fq: all tests successfull --------\n')