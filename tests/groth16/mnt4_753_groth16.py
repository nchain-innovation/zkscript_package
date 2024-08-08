import sys, os, json, argparse, secrets

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tx_engine import Context

from elliptic_curves.instantiations.mnt4_753.mnt4_753 import mnt4_753 as mnt4_753_curve

from zkscript.groth16.mnt4_753.mnt4_753 import mnt4_753

q = mnt4_753_curve.q
r = mnt4_753_curve.r
g1 = mnt4_753_curve.g1
g2 = mnt4_753_curve.g2
val_miller_loop = mnt4_753_curve.val_miller_loop

# Json dictionary of the outputs
tests = [
    'groth16',
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

def test_groth16():
    n_pub = 5
    # Dummy ZKP
    A_ = secrets.randbelow(r-1)+1
    B_ = secrets.randbelow(r-1)+1
    C_ = secrets.randbelow(r-1)+1
    
    A = g1.multiply(A_)
    B = g2.multiply(B_)
    C = g1.multiply(C_)

    # Test also the case in which one public input is zero
    a = [1,0]
    for i in range(2,n_pub):
        a.append(secrets.randbelow(r))
    # Test the case in which sum_gamma_abc is the point at infinity
    a.append(0)
    assert(len(a) == n_pub+1)

    # Dummy CRS
    alpha_ = secrets.randbelow(r-1)+1
    beta_ = secrets.randbelow(r-1)+1
    gamma_ = secrets.randbelow(r-1)+1
    delta_ = secrets.randbelow(r-1)+1
    
    alpha = g1.multiply(alpha_)
    beta = g2.multiply(beta_)
    gamma = g2.multiply(gamma_)
    delta = g2.multiply(delta_)
    
    gamma_abc = []
    sum_gamma_abc = g1.multiply(0)
    for i in range(n_pub+1):
        gamma_abc.append(g1.multiply(secrets.randbelow(r-1)+1))
        sum_gamma_abc += gamma_abc[i].multiply(a[i])

    alpha_beta = mnt4_753_curve.triple_pairing(A,sum_gamma_abc,C,B,-gamma,-delta)
    
    input_groth16 = mnt4_753_curve.prepare_groth16_proof(
        pub=a[1:],
        proof = {'a' : A, 'b': B, 'c': C},
        vk = {'alpha' : alpha, 'beta': beta, 'gamma': gamma, 'delta': delta, 'gamma_abc' : gamma_abc},
        miller_loop_type='twisted_curve',
        denominator_elimination='quadratic',
    )

    unlock = mnt4_753.groth16_verifier_unlock(**input_groth16)
    
    lock = mnt4_753.groth16_verifier(
        modulo_threshold=1,
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=(-gamma).to_list(),
        minus_delta=(-delta).to_list(),
        gamma_abc=list(map(lambda s: s.to_list(),gamma_abc)),
        check_constant=True,
        clean_constant=True
    )

    context = Context(script = unlock + lock)
    assert(context.evaluate() and (len(context.get_stack()) == 1) and (len(context.get_altstack()) == 0))

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    return

parser = argparse.ArgumentParser("Groth16 MNT4-753")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

test_groth16()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/mnt4_753_groth16.json','w')
    json.dump(scripts, outfile)

print('\nGroth16 MNT4_753: all tests successful -----\n')