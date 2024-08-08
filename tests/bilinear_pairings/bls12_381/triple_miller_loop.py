import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from tx_engine import Script, Context

from elliptic_curves.instantiations.bls12_381.bls12_381 import bls12_381 as bls12_381_curve, Fr

from zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381
from zkscript.bilinear_pairings.bls12_381.fields import fq12cubic_script
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
    'triple miller loop',
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

def test_triple_miller_loop():
    P1 = g1.multiply(n=Fr.generate_random_point().x)
    Q1 = g2.multiply(n=Fr.generate_random_point().x)
    P2 = g1.multiply(n=Fr.generate_random_point().x)
    Q2 = g2.multiply(n=Fr.generate_random_point().x)
    P3 = g1.multiply(n=Fr.generate_random_point().x)
    Q3 = g2.multiply(n=Fr.generate_random_point().x)
    
    output = bls12_381_curve.triple_miller_loop_on_twisted_curve(P1,P2,P3,Q1,Q2,Q3,denominator_elimination='quadratic')
    
    unlock = bls12_381.triple_miller_loop_input(
        P1=P1.to_list(),
        P2=P2.to_list(),
        P3=P3.to_list(),
        Q1=Q1.to_list(),
        Q2=Q2.to_list(),
        Q3=Q3.to_list(),
        lambdas_Q1_exp_miller_loop=[list(map(lambda s: s.to_list(),el)) for el in Q1.get_lambdas(exp_miller_loop)],
        lambdas_Q2_exp_miller_loop=[list(map(lambda s: s.to_list(),el)) for el in Q2.get_lambdas(exp_miller_loop)],
        lambdas_Q3_exp_miller_loop=[list(map(lambda s: s.to_list(),el)) for el in Q3.get_lambdas(exp_miller_loop)]
    )
    
    lock = bls12_381.triple_miller_loop(modulo_threshold=1,check_constant=True,clean_constant=True)
    lock += fq12cubic_script.to_quadratic()
    lock += generate_verify(output)
    
    context = Context(script = unlock + lock)
    assert(context.evaluate() and (len(context.get_stack()) == 1) and (len(context.get_altstack()) == 0))

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock
    
    return

parser = argparse.ArgumentParser("Triple Miller loop")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

test_triple_miller_loop()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/triple_miller_loop.json','w')
    json.dump(scripts, outfile)

print('\nTriple Miller loop BLS12_381: all tests successful -----\n')