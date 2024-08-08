import sys, os, json, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from tx_engine import Script, Context

from elliptic_curves.instantiations.mnt4_753.mnt4_753 import Fq, Fq4, mnt4_753

from zkscript.bilinear_pairings.mnt4_753.miller_output_operations import miller_output_ops
from zkscript.util.utility_scripts import nums_to_script

q = mnt4_753.q

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
    out = Script()
    elements = [_ for _ in z.to_list() if _ != 0]
    out += nums_to_script(elements)
    return out

# Json dictionary of the outputs
tests = [
    'line eval times eval',
    'line eval times eval times eval',
    'miller output times eval',

]

scripts = {test : {} for test in tests} 

type_of_script = [
    'unlocking',
    'locking script cleaning constants'
]

def test_line_eval_times_eval():
    x = Fq4.generate_random_point()
    x.x1.x0 = Fq.zero()
    y = Fq4.generate_random_point()
    y.x1.x0 = Fq.zero()
    
    z = x * y

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = miller_output_ops.line_eval_times_eval(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = miller_output_ops.line_eval_times_eval(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Check correct evaluation leaving constant for reuse
    lock_ = miller_output_ops.line_eval_times_eval(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)

    # Save scripts
    scripts[tests[0]][type_of_script[0]] = unlock
    scripts[tests[0]][type_of_script[1]] = lock

    print('Line eval times eval: \t\t\t\t\t\t\t test successful')

    return

def test_line_eval_times_eval_times_eval():
    x = Fq4.generate_random_point()
    x.x1.x0 = Fq.zero()
    y = Fq4.generate_random_point()
    
    z = x * y

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = miller_output_ops.line_eval_times_eval_times_eval(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = miller_output_ops.line_eval_times_eval_times_eval(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Check correct evaluation leaving constant for reuse
    lock_ = miller_output_ops.line_eval_times_eval_times_eval(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)

    # Save scripts
    scripts[tests[1]][type_of_script[0]] = unlock
    scripts[tests[1]][type_of_script[1]] = lock

    print('Line eval times eval times eval: \t\t\t\t\t test successful')
    
    return

def test_miller_output_times_eval():
    x = Fq4.generate_random_point()
    y = Fq4.generate_random_point()
    y.x1.x0 = Fq.zero()
    
    z = x * y

    unlock = nums_to_script([q])
    unlock += generate_unlock(x)
    unlock += generate_unlock(y)

    # Check correct evaluation
    lock = miller_output_ops.miller_loop_output_times_eval(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=False)
    lock += generate_verify(z)

    context = Context(script = unlock + lock)
    assert(context.evaluate() and len(context.get_stack()) == 1 and len(context.get_altstack()) == 0)

    # Check correct evaluation w/o cleaning constant
    lock_ = miller_output_ops.miller_loop_output_times_eval(take_modulo=True,check_constant=True,clean_constant=False,is_constant_reused=False)
    lock_ += generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 2 and len(context_.get_altstack()) == 0)

    # Check correct evaluation leaving constant for reuse
    lock_ = miller_output_ops.miller_loop_output_times_eval(take_modulo=True,check_constant=True,clean_constant=True,is_constant_reused=True)
    lock_ += Script.parse_string('OP_SWAP') + nums_to_script([q]) + Script.parse_string('OP_EQUALVERIFY') + generate_verify(z)

    context_ = Context(script = unlock + lock_)
    assert(context_.evaluate() and len(context_.get_stack()) == 1 and len(context_.get_altstack()) == 0)

    # Save scripts
    scripts[tests[2]][type_of_script[0]] = unlock
    scripts[tests[2]][type_of_script[1]] = lock

    print('Miller output times line eval: \t\t\t\t\t\t test successful')

    return

parser = argparse.ArgumentParser("Miller output operations")
parser.add_argument('save_to_json', help = '0/1: save the unlocking and locking scripts to json file', type=int)
args = parser.parse_args()

print('\nBegin tests Miller output operations MNT4-753 -------------------\n')

test_line_eval_times_eval()
test_line_eval_times_eval_times_eval()
test_miller_output_times_eval()

if args.save_to_json == 1:
    # Save scripts to file
    scripts = {x : {y: str(scripts[x][y]) for y in scripts[x]} for x in scripts}
    if not os.path.exists('./scripts_json'):
        os.makedirs('./scripts_json')
    outfile = open('./scripts_json/miller_output_operations.json','w')
    json.dump(scripts, outfile)

print('\nMiller output operations MNT4_753: all tests successful ---------\n')