# Find correct paths
import os
import sys

from typing import Optional

root = os.path.normpath(os.path.join(os.path.dirname(__file__),'../../../')) # root
sys.path.append(root)

from tx_engine import Script

from zkscript.util.utility_scripts import pick, roll, nums_to_script

def fq6_for_towering(mul_by_non_residue):
	"""
	Function to export Fq2 class below together with a mul_by_non_residue method which is used to construct towering extensions
	"""

	class Fq6ForTowering(Fq6):
		pass

	Fq6ForTowering.mul_by_non_residue = mul_by_non_residue

	return Fq6ForTowering

class Fq6:
	'''
	F_q^6 built as cubic extension of F_q^2. The non residue is specified by defining the method self.BASE_FIELD.mul_by_non_residue.
	'''

	def __init__(self, q:int, base_field):
		# Characteristic of the field
		self.MODULUS = q
		# Script implementation of the base field Fq2
		self.BASE_FIELD = base_field

		return

	def add(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Addition in F_q^6.
		Input parameters:
			- Stack: q .. X Y
			- Altstack: []
		Output:
			- X + Y
		Assumption on data:
			- X and Y are passed as triplets of elements of Fq2
		Variables:
			- If take_modulo is set to True, then the coordinates of X + Y are in Z_q; otherwise, the coordinates are not taken modulo q.
		Example:
			- x00 x01 x10 x11 x20 x21 y00 y01 y10 y11 y20 y21 [add] --> (x00 + y00) (x01 + y01) (x10 + y10) (x11 + y11) (x20 + y20) (x21 + y21)
		'''

		# Fq2 implementation
		fq2 = self.BASE_FIELD

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS])+ Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		# After this, the stack is x0 x1 y0 y1 altstack = [x2 + y2]
		out += roll(position=7,nElements=2)											# Roll x2
		out += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)
		out += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')

		# After this, the stack is: x0 y0 (x1 + y1), altstack = [x2 + y2]
		out += Script.parse_string('OP_2ROT')
		out += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)

		if take_modulo:
			# After this the stack is: (x0 + y0), altstack = [x2 + y2, x1 + y1]
			out += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')
			out += fq2.add(take_modulo=True,check_constant=False,clean_constant=clean_constant,is_constant_reused=True)
			# Batched modulo operations: pull from altstack, rotate, mod out, repeat
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			# After this the stack is: (x0 + y0) (x1 + y1), altstack = [x2 + y2]
			out += Script.parse_string('OP_2ROT OP_2ROT')
			out += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)
			out += Script.parse_string('OP_2SWAP')

			out += Script.parse_string('OP_FROMALTSTACK OP_FROMALTSTACK')

		return out

	def subtract(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Subtraction in F_q^6.
		Input parameters:
			- Stack: q .. X Y
			- Altstack: []]
		Output:
			- X - Y
		Assumption on data:
			- X and Y are passed as triplets of elements in F_q^2
		Variables:
			- If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates are not taken modulo q.
		'''

		# Fq2 implementation
		fq2 = self.BASE_FIELD

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS])+ Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		# After this, the stack is: x0 x1 y0 y1, altstack = [x2 - y2]
		out += roll(position=7,nElements=2)				# Roll x2
		out += Script.parse_string('OP_2SWAP')
		out += fq2.subtract(take_modulo=False,check_constant=False,clean_constant=False)
		out += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')
		# After this, the stack is: x0 y0 (x1 - y1), altstack = [x2 - y2]
		out += Script.parse_string('OP_2ROT OP_2SWAP')
		out += fq2.subtract(take_modulo=False,check_constant=False,clean_constant=False)

		if take_modulo:
			# After this the stack is: (x0 + y0), altstack = [x2 + y2, x1 + y1]
			out += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')
			out += fq2.subtract(take_modulo=True,check_constant=False,clean_constant=clean_constant,is_constant_reused=True)
			# Batched modulo operations: pull from altstack, rotate, mod out, repeat
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			# After this the stack is: (x0 + y0) (x1 + y1), altstack = [x2 + y2]
			out += Script.parse_string('OP_2ROT OP_2ROT')
			out += fq2.subtract(take_modulo=False,check_constant=False,clean_constant=False)
			out += Script.parse_string('OP_2SWAP')

			out += Script.parse_string('OP_FROMALTSTACK OP_FROMALTSTACK')

		return out

	def fq_scalar_mul(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Multiplication in F_q^6 by a scalar in F_q.
		Input parameters:
			- Stack: q .. X <lambda>
			- Altstack: []
		Output:
			- lambda * X
		Assumption on data:
			- X is passed as a couple of elements of Fq2
			- lambda is passed as an integer: minimally encoded, little endian
		Variables:
			- If take_modulo is set to True, then the coordinates X are in Z_q; otherwise, the coordinates are not taken modulo q.
		'''

		# Fq2 implementation
		fq2 = self.BASE_FIELD

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS])+ Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		# After this, the stack is: x0 x1 lambda, altstack = [x2*lambda]
		out += Script.parse_string('OP_TUCK OP_MUL OP_TOALTSTACK')
		out += Script.parse_string('OP_TUCK OP_MUL OP_TOALTSTACK')

		# After this, the stack is: x0, altstack = [x2*lambda, x1*lambda]
		out += Script.parse_string('OP_TUCK OP_MUL OP_TOALTSTACK')
		out += Script.parse_string('OP_TUCK OP_MUL OP_TOALTSTACK')

		if take_modulo:
			# After this, the stack is: x00*lambda q x01*lambda, altstack = [x2*lambda, x1*lambda]
			out += fq2.scalar_mul(take_modulo=True,check_constant=False,clean_constant=clean_constant,is_constant_reused=True)
			# Batched modulo operations: pull from altstack, rotate, mod out, repeat
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			# After this, the stack is: x00*lambda q x01*lambda, altstack = [x2*lambda, x1*lambda]
			out += fq2.scalar_mul(take_modulo=False,check_constant=False,clean_constant=False)
			out += Script.parse_string('OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK')
		
		return out

	def scalar_mul(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Multiplication by scalar in F_q^6
		Input parameters:
			- Stack: q .. X <lambda>
			- Altstack: []
		Output:
			- lambda * X
		Assumption on data:
			- X is passed as a couple of elements of Fq2
			- lambda is in F_q^2
		Variables:
			- If take_modulo is set to True, then the coordinates X are in Z_q; otherwise, the coordinates are not taken modulo q.
		'''

		# Fq2 implementation
		fq2 = self.BASE_FIELD

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS])+ Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		# After this, the stack is: x0 x1 lambda, altstack = [x2 * lambda]
		out += Script.parse_string('OP_2SWAP OP_2OVER')
		out += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		out += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')
		# After this, the stack is: x0 lambda (x1*lamdba), altstack = [x2 * lambda]
		out += Script.parse_string('OP_2SWAP OP_2OVER')
		out += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)

		if take_modulo:
			# After this, the stack is: x0*lambda, altstack = [x2*lambda, x1*lambda]
			out += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')
			out += fq2.mul(take_modulo=True,check_constant=False,clean_constant=clean_constant,is_constant_reused=True)
			# Batched modulo operations: pull from altstack, rotate, mod out, repeat
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			# After this, the stack is: (x0 * lambda) (x1 * lambda) (x2 * lamdba)
			out += Script.parse_string('OP_2ROT OP_2ROT')
			out += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
			out += Script.parse_string('OP_2SWAP OP_FROMALTSTACK OP_FROMALTSTACK')

		return out

	def negate(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Negation in F_q^6.
		Input parameters:
			- Stack: q .. X
			- Altstack: []
		Output:
			- -X
		Assumption on data:
			- X is passed as a triplet of elements in F_q^2
		Variables:
			- If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates are not taken modulo q.
		REMARK: OP_0 OP_NEGATE returns OP_0
		'''

		# Fq2 implementation
		fq2 = self.BASE_FIELD

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS])+ Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		if take_modulo:
			# After this, stack is: x0 x1, altstack = [-x2]
			out += fq2.negate(take_modulo=False,check_constant=False,clean_constant=False)
			out += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')
			# After this, stack is: x0, altstack = [-x2, -x1]
			out += fq2.negate(take_modulo=False,check_constant=False,clean_constant=False)
			out += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')
			# After this, stack is: -x_0, altstack = [-x2,-x1]
			out += fq2.negate(take_modulo=True,check_constant=False,clean_constant=clean_constant,is_constant_reused=True)
			# Batched modulo operations: pull from altstack, rotate, mod out, repeat
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			# After this, stack is: x_1 x_2 -x_0
			out += Script.parse_string('OP_2ROT')
			out += fq2.negate(take_modulo=False,check_constant=False,clean_constant=False)

			# After this, stack is: x_2 -x_0 -x_1
			out += Script.parse_string('OP_2ROT')
			out += fq2.negate(take_modulo=False,check_constant=False,clean_constant=False)

			# After this, stack is: -x_0 -x_1 -x_2
			out += Script.parse_string('OP_2ROT')
			out += fq2.negate(take_modulo=False,check_constant=False,clean_constant=False)

		return out

	def mul(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Multiplication in F_q^6.
		Input parameters:
			- Stack: q .. X Y
			- Altstack: []
		Output:
			- X * Y
		Assumption on data:
			- X and Y are passed as couples of elements of Fq2
			- The coordinates of X and Y are in Z_q
		Variables:
			- If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates are not taken modulo q.
		'''

		# Fq2 implementation
		fq2 = self.BASE_FIELD

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS])+ Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		# Computation of third component ---------------------------------------------------------

		# After this, the stack is: x0 x1 x2 y0 y1 y2 (x1*y1)
		compute_third_component = Script.parse_string('OP_2OVER')		# Pick y1
		compute_third_component += pick(position=11,nElements=2)		# Pick x1
		compute_third_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: x0 x1 x2 y0 y1 y2 (x1*y1) (x0*y2)
		compute_third_component += Script.parse_string('OP_2OVER')	# Pick y2
		compute_third_component += pick(position=15,nElements=2)		# Pick x0
		compute_third_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: x0 x1 x2 y0 y1 y2, altstack = [thirdComponent]
		compute_third_component += pick(position=11,nElements=2)		# Pick x2
		compute_third_component += pick(position=11,nElements=2)		# Pick y0
		compute_third_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		compute_third_component += fq2.add_three(take_modulo=False,check_constant=False,clean_constant=False)
		compute_third_component += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')

		# End of computation of third component ---------------------------------------------------

		# Computation of second component ---------------------------------------------------------

		# After this, the stack is: x0 x1 x2 y0 y1 y2 (y1*x0)
		compute_second_component = Script.parse_string('OP_2OVER')	# Pick y1
		compute_second_component += pick(position=13,nElements=2) 	# Pick x0
		compute_second_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: x0 x1 x2 y0 y1 y2 (y1*x0) (x2*y2*xi)
		compute_second_component += Script.parse_string('OP_2OVER')	# Pick y2
		compute_second_component += pick(position=11,nElements=2)		# Pick x2
		compute_second_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		compute_second_component  += fq2.mul_by_non_residue(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: x0 x1 x2 y0 y1 y2, altstack = [thirdComponent,secondComponent]
		compute_second_component += pick(position=13,nElements=2)		# Pick x1
		compute_second_component += pick(position=11,nElements=2)		# Pick y0
		compute_second_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		compute_second_component += fq2.add_three(take_modulo=False,check_constant=False,clean_constant=False)
		compute_second_component += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')

		# End of computation of second component ---------------------------------------------------

		# Computation of first component -----------------------------------------------------------

		# After this, the stack is: x0 x2 y0 y1 (y2*x1), altstack = [thirdComponent,secondComponent]
		compute_first_component = roll(position=9,nElements=2)		# Roll x1
		compute_first_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: x0 y0 [(y2*x1) + (x2*y1)] * xi, altstack = [thirdComponent,secondComponent]
		compute_first_component += Script.parse_string('OP_2SWAP')	# Roll y1
		compute_first_component += roll(position=7,nElements=2)		# Roll x2
		compute_first_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		compute_first_component += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)
		compute_first_component += fq2.mul_by_non_residue(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: firstComponent, altstack = [thirdComponent,secondComponent]
		compute_first_component += Script.parse_string('OP_2ROT OP_2ROT')
		compute_first_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		if take_modulo:
			compute_first_component += fq2.add(take_modulo=True,check_constant=False,clean_constant=clean_constant,is_constant_reused=True)
		else:
			compute_first_component += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)

		# End of computation of first component ----------------------------------------------------

		if take_modulo:
			out += compute_third_component + compute_second_component + compute_first_component
			
			# Batched modulo operations: pull from altstack, rotate, mod out, repeat
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			out += compute_third_component + compute_second_component + compute_first_component + Script.parse_string('OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK')

		return out

	def square(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Squaring in F_q^6.
		Input parameters:
			- Stack: q .. X
			- Altstack: []
		Output:
			- X**2
		Assumption on data:
			- X is passed as as a triplet of elements of Fq2
		Variables:
			- If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates are not taken modulo q.
		'''

		# Fq2 implementation
		fq2 = self.BASE_FIELD

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS])+ Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		# Computation third component ------------------------------------------------------------

		# After this, the stack is: x0 x1 x2 x1^2
		compute_third_component = Script.parse_string('OP_2OVER')		# Pick x1
		compute_third_component += fq2.square(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: x0 x1 x2 2x2 x1^2 2x2
		compute_third_component += Script.parse_string('OP_2OVER')	# Pick x2
		compute_third_component += Script.parse_string('OP_2') + fq2.scalar_mul(take_modulo=False,check_constant=False,clean_constant=False)
		compute_third_component += Script.parse_string('OP_2SWAP OP_2OVER')
		# After this, the stack is: x0 x1 x2 2x2, altstack = [thirdComponent]
		compute_third_component += pick(position=11,nElements=2)		# Pick x0
		compute_third_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		compute_third_component += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)
		compute_third_component += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')

		# End of computation of third component --------------------------------------------------

		# Computation of second component --------------------------------------------------------

		# After this, the stack is: x0 x1 2x2 x2^2
		compute_second_component = Script.parse_string('OP_2SWAP')		# Roll x2
		compute_second_component += fq2.square(take_modulo=False,check_constant=False,clean_constant=False)
		compute_second_component += fq2.mul_by_non_residue(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: x0 2x2 x1 x2^2 2x1*x0
		compute_second_component += Script.parse_string('OP_2ROT OP_2SWAP OP_2OVER')
		compute_second_component += pick(position=9,nElements=2)			# Pick x0
		compute_second_component += fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		compute_second_component += Script.parse_string('OP_2') + fq2.scalar_mul(take_modulo=False,check_constant=False,clean_constant=False)
		# After this, the stack is: x0 2x2 x1, altstack = [thirdComponent, secondComponent]
		compute_second_component += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)
		compute_second_component += Script.parse_string('OP_TOALTSTACK OP_TOALTSTACK')

		# End of computation of second component -------------------------------------------------

		# Computation of first component ---------------------------------------------------------

		# After this, the stack is: firstComponent, altstack = [thirdComponent, secondComponent]
		compute_first_component = fq2.mul(take_modulo=False,check_constant=False,clean_constant=False)
		compute_first_component += fq2.mul_by_non_residue(take_modulo=False,check_constant=False,clean_constant=False)
		compute_first_component += Script.parse_string('OP_2SWAP')		# Roll x0
		compute_first_component += fq2.square(take_modulo=False,check_constant=False,clean_constant=False)
		if take_modulo:
			compute_first_component += fq2.add(take_modulo=True,check_constant=False,clean_constant=clean_constant,is_constant_reused=True)
		else:
			compute_first_component += fq2.add(take_modulo=False,check_constant=False,clean_constant=False)

		# End of computation of first component --------------------------------------------------

		if take_modulo:
			out += compute_third_component + compute_second_component + compute_first_component
			
			# Batched modulo operations: pull from altstack, rotate, mod out, repeat
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_FROMALTSTACK OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			out += compute_third_component + compute_second_component + compute_first_component + Script.parse_string('OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK')

		return out
	
	def mul_by_v(self, take_modulo: bool, check_constant: Optional[bool] = None, clean_constant: Optional[bool] = None, is_constant_reused: Optional[bool] = None) -> Script:
		'''
		Multiplication by v in F_q^6.
		Input parameters:
			- Stack: q .. X
			- Altstack: []
		Output:
			- X * s
		Assumption on data:
			- X is passed as a triplet of elements of Fq2
		Variables:
			- If take_modulo is set to True, then the coordinates of the result are in Z_q; otherwise, the coordinates are not taken modulo q.
		'''

		# Fq2 implementation
		fq2 = self.BASE_FIELD

		if check_constant:
			out = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK') + nums_to_script([self.MODULUS])+ Script.parse_string('OP_EQUALVERIFY')
		else:
			out = Script()

		if take_modulo:
			# After this, the stack is: x0 x1 x2*NON_RESIDUE
			out += fq2.mul_by_non_residue(take_modulo=True,check_constant=False,clean_constant=False,is_constant_reused=False)
			# After this, the stack is: x1 (x2*NON_RESIDUE) x01 x00 q
			out += Script.parse_string('OP_2ROT OP_SWAP')
			out += Script.parse_string('OP_DEPTH OP_1SUB OP_PICK')
			# Mod out twice - after this the stack is: x1 (x2*NON_RESIDUE) x0
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_SWAP OP_ROT')
			out += Script.parse_string('OP_OVER OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')

			if clean_constant:
				fetch_q = Script.parse_string('OP_DEPTH OP_1SUB OP_ROLL')
			else:
				fetch_q = Script.parse_string('OP_DEPTH OP_1SUB OP_PICK')

			# Mod out twice - after this the stack is: (x2*NON_RESIDUE) x0 x1
			out += Script.parse_string('OP_2ROT OP_SWAP')
			out += fetch_q
			out += Script.parse_string('OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			out += Script.parse_string('OP_SWAP OP_ROT')
			if is_constant_reused:
				out += Script.parse_string('OP_OVER OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD')
			else:
				out += Script.parse_string('OP_OVER OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD')
		else:
			out += fq2.mul_by_non_residue(take_modulo=False,check_constant=False,clean_constant=False)
			out += Script.parse_string('OP_2ROT OP_2ROT')

		return out
