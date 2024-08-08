import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tx_engine import Script, Context

from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.fields.quadratic_extension import quadratic_extension_from_base_field_and_non_residue
from elliptic_curves.fields.cubic_extension import cubic_extension_from_base_field_and_non_residue

from zkscript.fields.fq2 import Fq2 as Fq2ScriptModel, fq2_for_towering
from zkscript.fields.fq6_3_over_2 import Fq6 as Fq6ScriptModel, fq6_for_towering
from zkscript.fields.fq12_2_over_3_over_2 import Fq12 as Fq12Script
from zkscript.util.utility_scripts import nums_to_script

# Fq2 definition, q = 19, non_residue = 3
q = 19
Fq = base_field_from_modulus(q=q)
NON_RESIDUE = Fq(3)
Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq,non_residue=NON_RESIDUE)
# Fq6 definition, non_residue = 1 + u
NON_RESIDUE_FQ2 = Fq2(Fq(1),Fq(1))
Fq6 = cubic_extension_from_base_field_and_non_residue(base_field=Fq2,non_residue=NON_RESIDUE_FQ2)
# Fq12 definition, non_residue = v
NON_RESIDUE_FQ6 = Fq6.v()
Fq12 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq6,non_residue=NON_RESIDUE_FQ6)
# Fq2 in script
Fq2Script = fq2_for_towering(mul_by_non_residue=Fq2ScriptModel.mul_by_one_plus_u)
fq2_script = Fq2Script(q=q,non_residue=NON_RESIDUE.to_list()[0])
# Fq6 in script
Fq6Script = fq6_for_towering(mul_by_non_residue=Fq6ScriptModel.mul_by_v)
fq6_script = Fq6Script(q=q,base_field=fq2_script)
# Gammas for Frobenius
gammas_frobenius = [[NON_RESIDUE_FQ2.power(i*(q**j-1)//6).to_list() for i in range(1,6)] for j in range(1,12)]
# Fq12 in script
fq12_script = Fq12Script(
    q=q,
    fq2=fq2_script,
    fq6=fq6_script,
    gammas_frobenius=gammas_frobenius
    )

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
    'multiplication',
    'square',
    'conjugation',
    'frobenius',
    'frobenius square',
    'frobenius cube'
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

# ------------------------------------

def test_mul():
    x = Fq12(Fq6(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)),Fq2(Fq(7),Fq(11))),Fq6(Fq2(Fq(5),Fq(3)),Fq2(Fq(8),Fq(17)),Fq2(Fq(15),Fq(6))))
    y = Fq12(Fq6(Fq2(Fq(1),Fq(2)),Fq2(Fq(3),Fq(4)),Fq2(Fq(8),Fq(12))),Fq6(Fq2(Fq(1),Fq(10)),Fq2(Fq(5),Fq(16)),Fq2(Fq(11),Fq(12))))
    
    z = x * y

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = fq12_script.mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq12_script.mul(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq12_script.mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    print('Multiplication:\t\t\t test successful')

    return

def test_square():
    x =  Fq12(Fq6(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)),Fq2(Fq(7),Fq(11))),Fq6(Fq2(Fq(5),Fq(3)),Fq2(Fq(8),Fq(17)),Fq2(Fq(15),Fq(6))))

    z = x * x

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    
    # Check correct evaluation
    lock = fq12_script.square(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq12_script.square(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq12_script.square(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[1]][type_of_script[0]] = unlock
    scripts[tests[1]][type_of_script[1]] = lock

    print('Squaring:\t\t\t test successful')

    return

def test_conjugate():
    x =  Fq12(Fq6(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)),Fq2(Fq(7),Fq(11))),Fq6(Fq2(Fq(5),Fq(3)),Fq2(Fq(8),Fq(17)),Fq2(Fq(15),Fq(6))))

    z = x.conjugate()

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    
    # Check correct evaluation
    lock = fq12_script.conjugate(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq12_script.conjugate(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq12_script.conjugate(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[2]][type_of_script[0]] = unlock
    scripts[tests[2]][type_of_script[1]] = lock

    print('Conjugation:\t\t\t test successful')

    return

def test_frobenius():
    x = Fq12(Fq6(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)),Fq2(Fq(7),Fq(11))),Fq6(Fq2(Fq(5),Fq(3)),Fq2(Fq(8),Fq(17)),Fq2(Fq(15),Fq(6))))
    
    z = x.frobenius(1)

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq12_script.frobenius_odd(n=1,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq12_script.frobenius_odd(n=1,take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq12_script.frobenius_odd(n=1,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[3]][type_of_script[0]] = unlock
    scripts[tests[3]][type_of_script[1]] = lock

    print('Frobenius:\t\t\t test successful')

    return

def test_frobenius_square():
    x = Fq12(Fq6(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)),Fq2(Fq(7),Fq(11))),Fq6(Fq2(Fq(5),Fq(3)),Fq2(Fq(8),Fq(17)),Fq2(Fq(15),Fq(6))))
    
    z = x.frobenius(2)

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq12_script.frobenius_even(n=2,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq12_script.frobenius_even(n=2,take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq12_script.frobenius_even(n=2,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[4]][type_of_script[0]] = unlock
    scripts[tests[4]][type_of_script[1]] = lock

    print('Frobenius square:\t\t test successful')

    return

def test_frobenius_cube():
    x = Fq12(Fq6(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)),Fq2(Fq(7),Fq(11))),Fq6(Fq2(Fq(5),Fq(3)),Fq2(Fq(8),Fq(17)),Fq2(Fq(15),Fq(6))))
    
    z = x.frobenius(3)

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq12_script.frobenius_odd(n=3,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq12_script.frobenius_odd(n=3,take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq12_script.frobenius_odd(n=3,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[5]][type_of_script[0]] = unlock
    scripts[tests[5]][type_of_script[1]] = lock

    print('Frobenius cube:\t\t\t test successful')

    return

parser = argparse.ArgumentParser("Fq12_2_over_3_over_2 arithmetic")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

print('\nBegin tests for Fq12_2_over_3_over_2 ------------------------\n')

test_mul()
test_square()
test_conjugate()
test_frobenius()
test_frobenius_square()
test_frobenius_cube()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/fq12_2_over_3_over_2.json','w')
    json.dump(scripts, outfile)

print('\nFq12_2_over_3_over_2 arithmetic: all tests successful-------\n')