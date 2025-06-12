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

    # def __repr__(self):
    #     return (
    #         f"{self.__class__.__name__}("
    #         f"positive_modulo={self.positive_modulo}, "
    #         f"check_constant={self.check_constant}, "
    #         f"take_modulo={self.take_modulo}, "
    #         f"clean_constant={self.clean_constant}, "
    #         f"is_constant_reused={self.is_constant_reused})"
    #     )

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
