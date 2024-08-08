import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from tx_engine import Script, Context

from elliptic_curves.instantiations.bls12_381.bls12_381 import bls12_381 as bls12_381_bilinear, Fr

from zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381
from zkscript.bilinear_pairings.bls12_381.fields import fq12cubic_script
from zkscript.util.utility_scripts import nums_to_script

q = bls12_381_bilinear.q
r = bls12_381_bilinear.r
g1 = bls12_381_bilinear.g1
g2 = bls12_381_bilinear.g2
val_miller_loop = bls12_381_bilinear.val_miller_loop
exp_miller_loop  = bls12_381_bilinear.exp_miller_loop

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
    'miller loop',
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

def test_miller_loop():
    P = g1.multiply(n=Fr.generate_random_point().x)
    while P.is_infinity():
        P = g1.multiply(n=Fr.generate_random_point().x)
    Q = g2.multiply(n=Fr.generate_random_point().x)
    while Q.is_infinity():
        Q = g2.multiply(n=Fr.generate_random_point().x)

    output = bls12_381_bilinear.miller_loop_on_twisted_curve(P,Q,denominator_elimination='quadratic')
    
    lambdas_Q_exp_miller_loop = [list(map(lambda s: s.to_list(),el)) for el in Q.get_lambdas(exp_miller_loop)]

    unlock = bls12_381.miller_loop_input_data(
        P=P.to_list(),
        Q=Q.to_list(),
        lambdas_Q_exp_miller_loop=lambdas_Q_exp_miller_loop)
    
    # Check correct evaluation
    lock = bls12_381.miller_loop(modulo_threshold=1,check_constant=True,clean_constant=True)
    lock += fq12cubic_script.to_quadratic()
    lock += generate_verify(output) + Script.parse_string('OP_VERIFY')
    lock += generate_verify(Q.multiply(val_miller_loop))

    context = Context(script = unlock + lock)
    assert(context.evaluate() and (len(context.get_stack()) == 1) and (len(context.get_altstack()) == 0))

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    return

parser = argparse.ArgumentParser("Miller loop")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

test_miller_loop()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/miller_loop.json','w')
    json.dump(scripts, outfile)

print('\nMiller loop BLS12_381: all tests successful ------------\n')