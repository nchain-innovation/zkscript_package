from typing import Optional
from copy import copy
from dataclasses import dataclass

@dataclass 
class ScriptParameters:
    positive_modulo: Optional[bool] = True
    check_constant: Optional[bool] = None
    take_modulo: Optional[bool] = False
    clean_constant: Optional[bool] = None
    is_constant_reused: Optional[bool] = None

    def change_attributes(self, attr_name:str, *args):
        args = (attr_name,) + args
        for arg in args:
            if hasattr(self, arg):
                current_value = getattr(self,arg)
                if isinstance(current_value, bool):
                    setattr(self, arg, not current_value)
                else:
                    raise TypeError(f'The attribute {arg} is not a boolean.')
            else:
                raise AttributeError(f'The attribute {arg} does not exist.')


    def with_overrides(self, **overrides):
        new_params = copy(self)
        for key, value in overrides.items():
            if hasattr(new_params, key):
                setattr(new_params, key, value)
            else:
                raise AttributeError(f"ScriptParameters has no attribute '{key}'")
        return new_params

default_parameters_1 = ScriptParameters()
default_parameters_2 = ScriptParameters(positive_modulo=True, check_constant=False, take_modulo=True, clean_constant=None, is_constant_reused=None) 
default_parameters_3 = ScriptParameters(positive_modulo=True, check_constant=True, take_modulo=True, clean_constant=None, is_constant_reused=None) 