import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tx_engine import Script, Context

from elliptic_curves.fields.fq import base_field_from_modulus
from elliptic_curves.fields.quadratic_extension import quadratic_extension_from_base_field_and_non_residue
from elliptic_curves.fields.cubic_extension import cubic_extension_from_base_field_and_non_residue

from zkscript.fields.fq2 import Fq2 as Fq2ScriptModel, fq2_for_towering
from zkscript.fields.fq4 import Fq4 as Fq4ScriptModel, fq4_for_towering
from zkscript.fields.fq12_3_over_2_over_2 import Fq12Cubic as Fq12Script
from zkscript.util.utility_scripts import nums_to_script

# Fq2 definition, q = 19, non_residue = 2
q = 19
Fq = base_field_from_modulus(q=q)
NON_RESIDUE = Fq(2)
Fq2 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq,non_residue=NON_RESIDUE)
# Fq2 definition, non_residue = 1 + u
NON_RESIDUE_FQ2 = Fq2(Fq(1),Fq(1))
Fq4 = quadratic_extension_from_base_field_and_non_residue(base_field=Fq2,non_residue=NON_RESIDUE_FQ2)
# Fq12
NON_RESIDUE_FQ4 = Fq4.u()
Fq12 = cubic_extension_from_base_field_and_non_residue(base_field=Fq4,non_residue=NON_RESIDUE_FQ4)
# Fq2 in script
Fq2Script = fq2_for_towering(mul_by_non_residue=Fq2ScriptModel.mul_by_one_plus_u)
fq2_script = Fq2Script(q=q,non_residue=NON_RESIDUE.to_list()[0])
# Fq4 in script
Fq4Script = fq4_for_towering(mul_by_non_residue=Fq4ScriptModel.mul_by_u)
fq4_script = Fq4Script(q=q,base_field=fq2_script)
# Fq12Cubic in script
fq12_script = Fq12Script(
    q=q,
    fq2=fq2_script,
    fq4=fq4_script
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
]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

# ------------------------------------

def test_mul():

    x = Fq12(
          x0=Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3))),
          x1=Fq4(Fq2(Fq(7),Fq(11)),Fq2(Fq(5),Fq(3))),
          x2=Fq4(Fq2(Fq(8),Fq(17)),Fq2(Fq(15),Fq(6))),
    )
    y = Fq12(
          x0=Fq4(Fq2(Fq(1),Fq(2)),Fq2(Fq(3),Fq(4))),
          x1=Fq4(Fq2(Fq(8),Fq(12)),Fq2(Fq(1),Fq(10))),
          x2=Fq4(Fq2(Fq(5),Fq(16)),Fq2(Fq(11),Fq(12)))
    )
    
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
    x = Fq12(Fq4(Fq2(Fq(1),Fq(1)),Fq2(Fq(2),Fq(3))),Fq4(Fq2(Fq(7),Fq(11)),Fq2(Fq(5),Fq(3))),Fq4(Fq2(Fq(8),Fq(17)),Fq2(Fq(15),Fq(6))))

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

parser = argparse.ArgumentParser("Fq12_3_over_2_over_2 arithmetic")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

print('\nBegin tests for Fq12_3_over_2_over_2 ------------------------\n')

test_mul()
test_square()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/fq12_3_over_2_over_2.json','w')
    json.dump(scripts, outfile)

print('\nFq12_3_over_2_over_2 arithmetic: all tests successful-------\n')