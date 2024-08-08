# Find correct paths
import os
import sys

from typing import Optional

root = os.path.normpath(os.path.join(os.path.dirname(__file__),'../../../../')) # root
sys.path.append(root)

from tx_engine import Script

from zkscript.util.utility_scripts import pick, nums_to_script

# Fq2 Script implementation
from zkscript.bilinear_pairings.mnt4_753.fields import fq2_script

class LineFunctions:
	'''
	Line evaluation for MNT4_753
	'''

	def __init__(self, fq2):
		self.MODULUS = fq2.MODULUS
		self.FQ2 = fq2

		return

	def line_evaluation(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Evaluate line through T and Q at P.
		If T = Q, then the line is the one tangent at T.
		Inputs:
			- Stack: q .. lambda Q P
			- Altstack: []
		Output:
			- ev_(l_(T,Q)(P))
		Assumption on data:
			- lambda is the gradient through T and Q
			- Q = (x2,y2) is passed as an affine point in E'(F_q^2), the sextic twist
			- P = (xP,yP) is passed as an affine point in E(F_q)
		Variables:
			- If take_modulo is set to True, the outputs are returned as constants in Z_q.
		REMARK: 
			- lambda is NOT checked in this function, it is assumed to be the gradient.
			- the point ev_(l_(T,Q)(P)) does NOT include the zero in the second component, this is to optimise the script size
		'''

		# Fq2 implementation
		fq2 = self.FQ2

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS]) + Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		# Compute third component -----------------------------------------------------

		# After this, the stack is: lambda xQ yQ xP, altstack = [yP]
		second_component = Script.parse_string('OP_TOALTSTACK')

		# -----------------------------------------------------------------------------

		# Compute second component ----------------------------------------------------

		# After this, the stack is: lambda xQ yQ, altstack = [second_component, -lambda*xP*u]
		first_component = Script.parse_string('OP_NEGATE')												# Negate xP
		first_component += pick(position=6,nElements=2)													# Pick lambda
		first_component += Script.parse_string('OP_ROT')												# Roll -xP
		first_component += fq2.scalar_mul(take_modulo=False,check_constant=False,clean_constant=False)
		first_component += fq2.mul_by_non_residue(take_modulo=False,check_constant=False,clean_constant=False)
		first_component += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')

		# After this, the stack is: -yQ + lambda*xQ -lambda*xP*u, altsack = [yP]
		first_component += Script.parse_string('OP_2ROT OP_2ROT')											# Roll lambda and xQ
		first_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		first_component += Script.parse_string('OP_2SWAP')												# Roll yQ
		first_component += fq2.subtract(take_modulo=False,check_constant=False,clean_constant=False,is_constant_reused=False)
		first_component += Script.parse_string('OP_FROMALTSTACK OP_FROMALTSTACK')
		if take_modulo:
			first_component += fq2.add(take_modulo=take_modulo,check_constant=False,clean_constant=clean_constant,is_constant_reused=True)
		else:
			first_component += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)

		# ----------------------------------------------------------------------------

		out += second_component + first_component

		if take_modulo:
			# Batched modulo operations: pull from altstack, rotate, mod out, repeat
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			out += Script.parse_string('OP_FROMALTSTACK')

		return out
	
line_functions = LineFunctions(fq2=fq2_script)