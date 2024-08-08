import sys, os, json, argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from tx_engine import Script, Context

from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.instantiations.bls12_381.bls12_381 import bls12_381

from zkscript.bilinear_pairings.bls12_381.line_functions import line_functions
from zkscript.util.utility_scripts import nums_to_script

q = bls12_381.q
r = bls12_381.r
g1 = bls12_381.g1
g2 = bls12_381.g2
Fr = base_field_from_modulus(q=r)

# Utility functions for the tests
def generate_verify(z) -> Script:
    out = Script()
    non_zero = [el for el in z.to_list() if el != 0]
    for ix, el in enumerate(non_zero[::-1]):
        if el != 0:
            out += nums_to_script([el])
        if ix != len(non_zero)-1:
            out += Script.parse_string('OP_EQUALVERIFY') 
        else:
            out += Script.parse_string('OP_EQUAL')

    return out

def generate_unlock(z) -> Script:
    out = nums_to_script(z.to_list())

    return out

# Json dictionary of the outputs
tests = [
    'doubling line evaluation',
    'addition line evaluation',
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

def test_doubling_line_evaluation():
    P = g1.multiply(n=Fr.generate_random_point().x)
    while P.is_infinity():
        P = g1.multiply(n=Fr.generate_random_point().x)
    Q = g2.multiply(n=Fr.generate_random_point().x)
    while Q.is_infinity():
        Q = g2.multiply(n=Fr.generate_random_point().x)

    lam = Q.get_lambda(Q)
    z = Q.line_evaluation(Q,P.to_twisted_curve())
    # Swap between Fq12 and Fq12Cubic
    z.x0.x0, z.x0.x1, z.x0.x2, z.x1.x0, z.x1.x1, z.x1.x2 = z.x0.x0, z.x1.x1, z.x1.x0, z.x0.x2, z.x0.x1, z.x1.x2

    unlock = nums_to_script([q])
    unlock += nums_to_script(lam.to_list())
    unlock += nums_to_script(Q.to_list())
    unlock += nums_to_script(P.to_list())

    # Check correct evaluation
    lock = line_functions.line_evaluation(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = line_functions.line_evaluation(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Check correct evaluation leaving constant for reuse
    lock_ = line_functions.line_evaluation(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    print('Doubling line evaluation: \t test successful')

    return

def test_addition_line_evaluation():
    P = g1.multiply(n=Fr.generate_random_point().x)
    while P.is_infinity():
        P = g1.multiply(n=Fr.generate_random_point().x)
    Q = g2.multiply(n=Fr.generate_random_point().x)
    while Q.is_infinity():
        Q = g2.multiply(n=Fr.generate_random_point().x)
    R = g2.multiply(n=Fr.generate_random_point().x)
    while R.is_infinity() or R == Q:
        R = g2.multiply(n=Fr.generate_random_point().x)

    lam = Q.get_lambda(R)
    z = Q.line_evaluation(R,P.to_twisted_curve())
    # Swap between Fq12 and Fq12Cubic
    z.x0.x0, z.x0.x1, z.x0.x2, z.x1.x0, z.x1.x1, z.x1.x2 = z.x0.x0, z.x1.x1, z.x1.x0, z.x0.x2, z.x0.x1, z.x1.x2

    unlock = nums_to_script([q])
    unlock += nums_to_script(lam.to_list())
    unlock += nums_to_script(R.to_list())
    unlock +=nums_to_script(P.to_list())

    # Check correct evaluation
    lock = line_functions.line_evaluation(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = line_functions.line_evaluation(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Check correct evaluation leaving constant for reuse
    lock_ = line_functions.line_evaluation(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)

    # Save scripts
    scripts[tests[1]][type_of_script[0]] = unlock
    scripts[tests[1]][type_of_script[1]] = lock

    print('Line addition evaluation: \t test successful')

    return

parser = argparse.ArgumentParser("Line evaluations")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

print('\nBegin tests line evaluations BLS12-381 ---------------------\n')

test_doubling_line_evaluation()
test_addition_line_evaluation()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/line_evaluations.json','w')
    json.dump(scripts, outfile)

print('\nLine evaluations BLS12_381: all tests successful ----------\n')