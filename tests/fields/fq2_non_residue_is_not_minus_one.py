import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tx_engine import Script, Context

from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.fields.quadratic_extension import quadratic_extension_from_base_field_and_non_residue


from zkscript.fields.fq2 import Fq2 as Fq2Script
from zkscript.util.utility_scripts import nums_to_script

# Fq2 definition, q = 19, non_residue = 3
q = 19
Fq = base_field_from_modulus(q=q)
NON_RESIDUE = Fq(3)
Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq,non_residue=NON_RESIDUE)
# Fq2 in script
fq2_script = Fq2Script(q=q,non_residue=NON_RESIDUE.to_list()[0])

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
    'addition',
    'subtraction',
    'scalar multiplication',
    'negation',
    'multiplication',
    'square',
    'addition 3 terms',
    'conjugation',
    'multiplication by u',
    'multiplication by 1 + u',
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

# ------------------------------------

def test_addition():
    x = Fq2(Fq(5),Fq(10))
    y = Fq2(Fq(2),Fq(10))

    z = Fq2(Fq(7),Fq(1))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = fq2_script.add(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.add(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.add(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)

    # Check failure for wrong constant
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    print('Addition:\t\t\t test successful')

    return

def test_subtraction():
    x = Fq2(Fq(5),Fq(10))
    y = Fq2(Fq(2),Fq(10))

    z = Fq2(Fq(3),Fq(0))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = fq2_script.subtract(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.subtract(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.subtract(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[1]][type_of_script[0]] = unlock
    scripts[tests[1]][type_of_script[1]] = lock

    print('Subtraction:\t\t\t test successful')

    return

def test_negation():
    x = Fq2(Fq(5),Fq(10))

    z = Fq2(Fq(-5),Fq(-10))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq2_script.negate(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.negate(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.negate(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker
    
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[2]][type_of_script[0]] = unlock
    scripts[tests[2]][type_of_script[1]] = lock
    
    print('Negation:\t\t\t test successful')

    return

def test_scalar_mul():
    x = Fq2(Fq(5),Fq(10))
    y = Fq(2)

    z = Fq2(Fq(10),Fq(1))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = fq2_script.scalar_mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.scalar_mul(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.scalar_mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker
    
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[3]][type_of_script[0]] = unlock
    scripts[tests[3]][type_of_script[1]] = lock

    print('Scalar multiplication:\t\t test successful')

    return

def test_mul():
    x = Fq2(Fq(5),Fq(10))
    y = Fq2(Fq(2),Fq(10))

    z = x*y

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = fq2_script.mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.mul(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.mul(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker
    
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[4]][type_of_script[0]] = unlock
    scripts[tests[4]][type_of_script[1]] = lock

    print('Multiplication:\t\t\t test successful')

    return

def test_square():
    x = Fq2(Fq(5),Fq(10))

    z = x.power(2)

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq2_script.square(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.square(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.square(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker
    
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[5]][type_of_script[0]] = unlock
    scripts[tests[5]][type_of_script[1]] = lock

    print('Squaring:\t\t\t test successful')

    return

def test_add_three():
    x = Fq2(Fq(5),Fq(10))
    y = Fq2(Fq(2),Fq(10))
    z = Fq2(Fq(7),Fq(4))

    w = Fq2(Fq(14),Fq(5))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)
    unlock += generate_unlock(z)

    # Check correct evaluation
    lock = fq2_script.add_three(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(w)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.add_three(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(w)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.add_three(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(w)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)
    
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[6]][type_of_script[0]] = unlock
    scripts[tests[6]][type_of_script[1]] = lock

    print('Triple addition:\t\t test successful')

    return

def test_conjugate():
    x = Fq2(Fq(5),Fq(10))
    z =Fq2(Fq(5),Fq(9))

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq2_script.conjugate(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.conjugate(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.conjugate(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker
    
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[7]][type_of_script[0]] = unlock
    scripts[tests[7]][type_of_script[1]] = lock

    print('Conjugation:\t\t\t test successful')

    return

def test_mul_by_u():
    x = Fq2(Fq(5),Fq(10))
    z = x * Fq2.u()

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq2_script.mul_by_u(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.mul_by_u(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.mul_by_u(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker
    
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[8]][type_of_script[0]] = unlock
    scripts[tests[8]][type_of_script[1]] = lock

    print('Multiplication by u:\t\t test successful')

    return

def test_mul_by_one_plus_u():
    x = Fq2(Fq(5),Fq(10))
    z = x * (Fq2.identity() + Fq2.u())

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)

    # Check correct evaluation
    lock = fq2_script.mul_by_one_plus_u(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation w/o cleaning constant
    lock_ = fq2_script.mul_by_one_plus_u(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker

    # Check correct evaluation leaving constant for reuse
    lock_ = fq2_script.mul_by_one_plus_u(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)   # Evaluation using the Script Checker
    
    unlock_wrong = Script.parse_string('OP_10') + unlock
    context_wrong = Context(script = unlock_wrong + lock_)
    assert(not(context_wrong.evaluate(quiet=True)))   # Wrong constant

    # Save scripts
    scripts[tests[9]][type_of_script[0]] = unlock
    scripts[tests[9]][type_of_script[1]] = lock

    print('Multiplication by 1 + u:\t test successful')

    return

parser = argparse.ArgumentParser("Fq2 arithmetic w/ non_residue = -1")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

print('\nBegin tests for Fq2 w/ non_residue != -1 ----------------------------\n')

test_addition()
test_subtraction()
test_scalar_mul()
test_negation()
test_mul()
test_square()
test_add_three()
test_conjugate()
test_mul_by_u()
test_mul_by_one_plus_u()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/fq2_non_residue_is_not_minus_one.json','w')
    json.dump(scripts, outfile)

print('\nFq2 arithmetic w/ non_residue != -1: all tests successful  ---------\n')