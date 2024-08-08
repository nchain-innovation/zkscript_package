import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from tx_engine import Script, Context

from elliptic_curves.instantiations.mnt4_753.mnt4_753 import Fq4, mnt4_753
from elliptic_curves.instantiations.mnt4_753.final_exponentiation import easy_exponentiation, hard_exponentiation

from zkscript.bilinear_pairings.mnt4_753.final_exponentiation import final_exponentiation
from zkscript.util.utility_scripts import nums_to_script

q = mnt4_753.q

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
    'easy exponentiation with inverse check',
    'hard exponentiation',
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

def test_easy_exponentiation_with_inverse_check():
    x = Fq4.generate_random_point()
    x_inverse = x.invert()

    z = easy_exponentiation(x)
    
    unlock = nums_to_script([q])
    unlock += generate_unlock(x_inverse)
    unlock += generate_unlock(x)

   # Check correct evaluation
    lock = final_exponentiation.easy_exponentiation_with_inverse_check(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = final_exponentiation.easy_exponentiation_with_inverse_check(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Check correct evaluation leaving constant for reuse
    lock_ = final_exponentiation.easy_exponentiation_with_inverse_check(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)

    print('Easy exponentiation with inverse check: \t test successful')

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    return

def test_hard_exponentiation():
    x = Fq4.generate_random_point()
    x = easy_exponentiation(x)

    z = hard_exponentiation(x)
    
    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

     # Check correct evaluation
    lock = final_exponentiation.hard_exponentiation(take_modulo=True,modulo_threshold=1,check_constant=True,clean_constant=True)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = final_exponentiation.hard_exponentiation(take_modulo=True,modulo_threshold=1,check_constant=True,clean_constant=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Save scripts
    scripts[tests[1]][type_of_script[0]] = unlock
    scripts[tests[1]][type_of_script[1]] = lock

    print('Hard exponentiation: \t\t\t\t test successful')

    return

parser = argparse.ArgumentParser("Final exponentiation")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()


print('\nBegin tests final exponentation MNT4-753 -------------\n')

test_easy_exponentiation_with_inverse_check()
test_hard_exponentiation()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/final_exponentiation.json','w')
    json.dump(scripts, outfile)

print('\nFinal exponentiation MNT4_753: all tests successful --\n')