import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tx_engine import Script, Context

from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.fields.quadratic_extension import quadratic_extension_from_base_field_and_non_residue

from zkscript.fields.fq2 import Fq2 as Fq2ScriptModel, fq2_for_towering
from zkscript.fields.fq4 import Fq4 as Fq4Script
from zkscript.util.utility_scripts import nums_to_script

# Fq2 definition, q = 19, non_residue = 2
q = 19
Fq = base_field_from_modulus(q=q)
NON_RESIDUE = Fq(2)
Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq,non_residue=NON_RESIDUE)
# Fq4 definition, non_residue = 1 + u
NON_RESIDUE_FQ2 = Fq2(Fq(1),Fq(1))
Fq4 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq2,non_residue=NON_RESIDUE_FQ2)
# Fq2 in script
Fq2Script = fq2_for_towering(mul_by_non_residue=Fq2ScriptModel.mul_by_one_plus_u)
fq2_script = Fq2Script(q=q,non_residue=NON_RESIDUE.to_list()[0])
# Fq4 in script
# Gammas for Frobenius
gammas_frobenius = [NON_RESIDUE_FQ2.power((q**j-1)//2).to_list() for j in range(1,4)]
fq4_script = Fq4Script(q=q,base_field=fq2_script,gammas_frobenius=gammas_frobenius)

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

#define the json dictionary of outputs
tests = [
    'addition',
    'scalar multiplication Fq',
    'scalar multiplication Fq2',
    'multiplication',
    'square',
    'addition 3 terms',
    'frobenius',
    'frobenius square',
    'frobenius cube',
    'multiplication by u',
    'conjugation',
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

# ------------------------------------

def test_addition():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))
    y = Fq4(Fq2(Fq(1),Fq(2)),Fq2(Fq(3),Fq(4)))

    z = Fq4(Fq2(Fq(2),Fq(3)),Fq2(Fq(5),Fq(7)))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = fq4_script.add(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.add(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.add(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check failure for wrong constant
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    print('Addition:\t\t\t test successful')

    return

def test_scalar_mul_fq():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))

    lam = Fq(10)
    
    z = Fq4(Fq2(Fq(10),Fq(10)),Fq2(Fq(1),Fq(11)))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += Script.parse_string(str(lam))

    # Check correct evaluation
    lock = fq4_script.fq_scalar_mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.fq_scalar_mul(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.fq_scalar_mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[1]][type_of_script[0]] = unlock
    scripts[tests[1]][type_of_script[1]] = lock

    print('Scalar multiplication by Fq:\t test successful')

    return

def test_scalar_mul_fq2():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))

    lam = Fq2(Fq(2),Fq(3))
    
    z = lam * x

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(lam)

    # Check correct evaluation
    lock = fq4_script.scalar_mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.scalar_mul(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.scalar_mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker
    
    # Save scripts
    scripts[tests[2]][type_of_script[0]] = unlock
    scripts[tests[2]][type_of_script[1]] = lock

    print('Scalar multiplication by Fq2:\t test successful')

    return

def test_mul():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))
    y = Fq4(Fq2(Fq(1),Fq(2)),Fq2(Fq(3),Fq(4)))
    
    z = x * y

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = fq4_script.mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.mul(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[3]][type_of_script[0]] = unlock
    scripts[tests[3]][type_of_script[1]] = lock

    print('Multiplication:\t\t\t test successful')

    return

def test_square():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))

    z = x * x

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    
    # Check correct evaluation
    lock = fq4_script.square(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.square(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.square(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[4]][type_of_script[0]] = unlock
    scripts[tests[4]][type_of_script[1]] = lock

    print('Squaring:\t\t\t test successful')

    return

def test_add_three():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))
    y = Fq4(Fq2(Fq(1),Fq(2)),Fq2(Fq(3),Fq(4)))
    z = Fq4(Fq2(Fq(4),Fq(7)),Fq2(Fq(1),Fq(2)))
    
    w = Fq4(Fq2(Fq(6),Fq(10)),Fq2(Fq(6),Fq(9)))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)
    unlock += generate_unlock(z)

    # Check correct evaluation
    lock = fq4_script.add_three(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(w)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.add_three(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(w)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.add_three(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(w)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[5]][type_of_script[0]] = unlock
    scripts[tests[5]][type_of_script[1]] = lock

    print('Triple addition:\t\t test successful')

    return

def test_frobenius():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))
    
    z = x.frobenius(1)

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq4_script.frobenius_odd(n=1,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.frobenius_odd(n=1,take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.frobenius_odd(n=1,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[6]][type_of_script[0]] = unlock
    scripts[tests[6]][type_of_script[1]] = lock

    print('Frobenius:\t\t\t test successful')
    
    return

def test_frobenius_square():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))
    
    z = x.frobenius(2)

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq4_script.frobenius_even(n=2,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.frobenius_even(n=2,take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.frobenius_even(n=2,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    print('Frobenius square:\t\t test successful')

    # Save scripts
    scripts[tests[7]][type_of_script[0]] = unlock
    scripts[tests[7]][type_of_script[1]] = lock

    return

def test_frobenius_cube():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))
    
    z = x.frobenius(3)

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq4_script.frobenius_odd(n=3,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.frobenius_odd(n=3,take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.frobenius_odd(n=3,take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[8]][type_of_script[0]] = unlock
    scripts[tests[8]][type_of_script[1]] = lock

    print('Frobenius cube:\t\t\t test successful')
    
    return

def test_mul_by_u():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))
    
    z = x * Fq4.u()

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq4_script.mul_by_u(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.mul_by_u(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.mul_by_u(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    print('Multiplication by u:\t\t test successful')

    # Save scripts
    scripts[tests[9]][type_of_script[0]] = unlock
    scripts[tests[9]][type_of_script[1]] = lock

    return

def test_conjugate():
    x = Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3)))
    
    z = x.conjugate()

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq4_script.conjugate(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq4_script.conjugate(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq4_script.conjugate(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Save scripts
    scripts[tests[10]][type_of_script[0]] = unlock
    scripts[tests[10]][type_of_script[1]] = lock

    print('Conjugation:\t\t\t test successful')

    return

parser = argparse.ArgumentParser("Fq4 arithmetic")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

print('\nBegin tests for Fq4 ----------------------------\n')

test_addition()
test_scalar_mul_fq()
test_scalar_mul_fq2()
test_mul()
test_square()
test_add_three()
test_frobenius()
test_frobenius_square()
test_frobenius_cube()
test_mul_by_u()
test_conjugate()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/fq4.json','w')
    json.dump(scripts, outfile)

print('\nFq4 arithmetic: all tests successful-----------\n')