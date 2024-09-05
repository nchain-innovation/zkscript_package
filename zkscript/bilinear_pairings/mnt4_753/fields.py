# Export finite field arithmetic for MNT4_753

from typing import Optional
from types import MethodType
from tx_engine import Script

# Find correct paths
import os
import sys

root = os.path.normpath(os.path.join(os.path.dirname(__file__),'../../../')) # root
sys.path.append(root)

from zkscript.bilinear_pairings.mnt4_753.parameters import q, NON_RESIDUE_FQ, GAMMAS

from zkscript.fields.fq2 import Fq2 as Fq2ScriptModel, fq2_for_towering
from zkscript.fields.fq4 import Fq4 as Fq4ScriptModel

from zkscript.util.utility_scripts import nums_to_script

# Fq2 class
Fq2Script = fq2_for_towering(Fq2ScriptModel.mul_by_u)
# Fq2 implementation
fq2_script = Fq2Script(q=q,non_residue=NON_RESIDUE_FQ)

# Override squaring
def square(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
    """
    Squaring in Fq4
    """
    
    if check_constant:
        out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS]) + Script.parse_string('OP_EQUALVERIFY')
    else:
        out = Script()
            
    # Fourth component ------
    
    # After this, the stack is: x0 x1 x2 x3, altstack = [2*(x1*x2 + x0*x3)]
    out += Script.parse_string('OP_2OVER OP_2OVER')
    out += Script.parse_string('OP_TOALTSTACK')
    out += Script.parse_string('OP_MUL')
    out += Script.parse_string('OP_SWAP OP_FROMALTSTACK OP_MUL')
    out += Script.parse_string('OP_ADD OP_2 OP_MUL')
    out += Script.parse_string('OP_TOALTSTACK')
    
    # Third compenent -------
    
    # After this, the stack is: x0 x1 x2 x3, altstack = [fourth_component, 2*(x0*x2 + x1*x3*NON_RESIDUE)]
    out += Script.parse_string('OP_2OVER OP_2OVER')
    out += Script.parse_string('OP_ROT')
    out += Script.parse_string('OP_MUL')
    out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
    out += Script.parse_string('OP_MUL')
    out += Script.parse_string('OP_ROT OP_ROT OP_MUL')
    out += Script.parse_string('OP_ADD OP_2 OP_MUL')
    out += Script.parse_string('OP_TOALTSTACK')
    
    # Second component ------
    
    # After this, the stack is: x0 x1 x2 x3, altstack = [fourth_component, third_component, 2*x0*x1 + x2^2 + x3^2 * NON_RESIDUE]
    out += Script.parse_string('OP_2OVER OP_2OVER')
    out += Script.parse_string('OP_DUP OP_MUL')
    out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
    out += Script.parse_string('OP_MUL')
    out += Script.parse_string('OP_SWAP')
    out += Script.parse_string('OP_DUP OP_MUL')
    out += Script.parse_string('OP_ADD')
    out += Script.parse_string('OP_ROT OP_ROT')
    out += Script.parse_string('OP_2 OP_MUL OP_MUL')
    out += Script.parse_string('OP_ADD')
    out += Script.parse_string('OP_TOALTSTACK')
    
    # First component -------
    
    # After this, the stack is: x0^2 + (x1^2 + 2*x2*x3)*NON_RESIDUE, altstack = [fourth_component, third_component, second_component]
    out += Script.parse_string('OP_2 OP_MUL OP_MUL')
    out += Script.parse_string('OP_SWAP')
    out += Script.parse_string('OP_DUP OP_MUL OP_ADD')
    out += nums_to_script([self.BASE_FIELD.NON_RESIDUE])
    out += Script.parse_string('OP_MUL')
    out += Script.parse_string('OP_SWAP')
    out += Script.parse_string('OP_DUP OP_MUL OP_ADD')
    
    if take_modulo:
        batched_modulo = Script()
        
        assert(clean_constant != None and is_constant_reused != None)
        if clean_constant:
            fetch_q = Script.parse_string('OP_DEPTH OP_1SUB OP_ROLL')
        else:
            fetch_q = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK')

        batched_modulo += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
        batched_modulo += Script.parse_string('OP_FROMALTSTACK OP_ROT')
        batched_modulo += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
        batched_modulo += Script.parse_string('OP_FROMALTSTACK OP_ROT')
        batched_modulo += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
        batched_modulo += Script.parse_string('OP_FROMALTSTACK OP_ROT')
        
        if is_constant_reused:
            batched_modulo += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
        else:
            batched_modulo += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')

        out += fetch_q + batched_modulo
    else:
        out += Script.parse_string('OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK')
    
    return out

# Fq4 implementation
fq4_script = Fq4ScriptModel(
    q=q,
    base_field=fq2_script,
    gammas_frobenius=GAMMAS
)
fq4_script.square = MethodType(square,fq4_script)