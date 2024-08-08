import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from tx_engine import Script, Context

from elliptic_curves.instantiations.bls12_381.bls12_381 import bls12_381 as bls12_381_curve, Fr

from zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381
from zkscript.util.utility_scripts import nums_to_script

q = bls12_381_curve.q
r = bls12_381_curve.r
g1 = bls12_381_curve.g1
g2 = bls12_381_curve.g2
val_miller_loop = bls12_381_curve.val_miller_loop
exp_miller_loop = bls12_381_curve.exp_miller_loop

# Utility functions for the tests
def generate_verify(z) -> Script:
    out = Script()
    for ix, el in enumerate(z.to_list()[::-1]):
        out += nums_to_script([el])
        if ix != len(z.to_list())-1:
            out += Script.parse_string('OP_EQUALVERIFY') 
        else:
            out += Script.parse_string('OP_EQUAL')

    return out

def generate_unlock(z) -> Script:
    out = nums_to_script(z.to_list())

    return out

# Json dictionary of the outputs
tests = [
    'pairing',
    'pairing P is infinity',
    'pairing Q is infinity',
    'pairing P & Q is infinity'
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

def test_pairing():
    P = g1.multiply(n=Fr.generate_random_point().x)
    while P.is_infinity():
        P = g1.multiply(n=Fr.generate_random_point().x)
    Q = g2.multiply(n=Fr.generate_random_point().x)
    while Q.is_infinity():
        Q = g2.multiply(n=Fr.generate_random_point().x)

    output = bls12_381_curve.pairing(P,Q)
    
    lambdas_Q_exp_miller_loop = [list(map(lambda s: s.to_list(),el)) for el in Q.get_lambdas(exp_miller_loop)]

    unlock = bls12_381.single_pairing_input(
        P=P.to_list(),
        Q=Q.to_list(),
        lambdas_Q_exp_miller_loop=lambdas_Q_exp_miller_loop,
        miller_output_inverse=bls12_381_curve.miller_loop_on_twisted_curve(P,Q,'quadratic').invert().to_list(),
    )
    
    # Check correct evaluation
    lock = bls12_381.single_pairing(modulo_threshold=1,check_constant=True,clean_constant=True)
    lock += generate_verify(output)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and (len(context.get_stack()) == 1) and (len(context.get_altstack()) == 0))

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    print('Pairing: \t\t\t test successful')

    return

def test_pairing_P_is_infinity():
    P = g1.multiply(0)
    Q = g2.multiply(n=Fr.generate_random_point().x)
    while Q.is_infinity():
        Q = g2.multiply(n=Fr.generate_random_point().x)

    output = bls12_381_curve.pairing(P,Q)
    
    lambdas_Q_exp_miller_loop = [list(map(lambda s: s.to_list(),el)) for el in Q.get_lambdas(exp_miller_loop)]
        
    unlock = bls12_381.single_pairing_input(
        P=[None,None],
        Q=Q.to_list(),
        lambdas_Q_exp_miller_loop=lambdas_Q_exp_miller_loop,
        miller_output_inverse=None,
    )
    
    # Check correct evaluation
    lock = bls12_381.single_pairing(modulo_threshold=1,check_constant=True,clean_constant=True)
    lock += generate_verify(output)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and (len(context.get_stack()) == 1) and (len(context.get_altstack()) == 0))

    # Save scripts
    scripts[tests[1]][type_of_script[0]] = unlock
    scripts[tests[1]][type_of_script[1]] = lock

    print('Pairing w/ P infinity: \t\t test successful')

    return

def test_pairing_Q_is_infinity():
    P = g1.multiply(n=Fr.generate_random_point().x)
    while P.is_infinity():
        P = g1.multiply(n=Fr.generate_random_point().x)
    Q = g2.multiply(n=0)
    
    output = bls12_381_curve.pairing(P,Q)
    
    unlock = bls12_381.single_pairing_input(
        P=P.to_list(),
        Q=[None,None],
        lambdas_Q_exp_miller_loop=[],
        miller_output_inverse=None,
    )
    
    # Check correct evaluation
    lock = bls12_381.single_pairing(modulo_threshold=1,check_constant=True,clean_constant=True)
    lock += generate_verify(output)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and (len(context.get_stack()) == 1) and (len(context.get_altstack()) == 0))

    # Save scripts
    scripts[tests[2]][type_of_script[0]] = unlock
    scripts[tests[2]][type_of_script[1]] = lock

    print('Pairing w/ Q infinity: \t\t test successful')

    return

def test_pairing_P_and_Q_are_infinity():
    P = g1.multiply(0)
    Q = g2.multiply(0)
    
    output = bls12_381_curve.pairing(P,Q)
    
    unlock = bls12_381.single_pairing_input(
        P=[None,None],
        Q=[None,None],
        lambdas_Q_exp_miller_loop=[],
        miller_output_inverse=None
    )
    
    # Check correct evaluation
    lock = bls12_381.single_pairing(modulo_threshold=1,check_constant=True,clean_constant=True)
    lock += generate_verify(output)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and (len(context.get_stack()) == 1) and (len(context.get_altstack()) == 0))

    # Save scripts
    scripts[tests[3]][type_of_script[0]] = unlock
    scripts[tests[3]][type_of_script[1]] = lock

    print('Pairing w P & Q infinity: \t test successful')

    return

parser = argparse.ArgumentParser("Pairing")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

print('\nBegin tests pairing for BLS12-381 -------------\n')

test_pairing()
test_pairing_P_is_infinity()
test_pairing_Q_is_infinity()
test_pairing_P_and_Q_are_infinity()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/pairing.json','w')
    json.dump(scripts, outfile)

print('\nPairing BLS12_381: all tests successful -------\n')