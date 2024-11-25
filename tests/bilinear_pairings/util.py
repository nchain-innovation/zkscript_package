import json
from pathlib import Path
from typing import Optional

from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script


def generate_verify(z, elements_to_select: Optional[list[int]] = None) -> Script:
    out = Script()
    z = z.to_list()

    selected_elements = z if elements_to_select is None else [z[i] for i in elements_to_select]

    n_selected_elements = len(selected_elements)

    for ix, el in enumerate(selected_elements[::-1]):
        out += nums_to_script([el])
        if ix != n_selected_elements - 1:
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out += Script.parse_string("OP_EQUAL")

    return out


def modify_verify_modulo_check(old_verification_script, clean_constant):
    """Modify the verification script to take the positive modulo of the results before checking the equalities.

    Args:
        old_verification_script: the original verification script
        clean_constant: a boolean value determining if the modulo should be removed from the stack or not
    """

    op_equalverify_with_modulo = "OP_SWAP OP_DEPTH OP_1SUB OP_PICK OP_TUCK OP_ADD OP_SWAP OP_MOD OP_EQUALVERIFY"
    op_equal_with_modulo = op_equalverify_with_modulo.replace("OP_EQUALVERIFY", "OP_EQUAL")
    new_verification_script = Script.parse_string(
        str(old_verification_script)
        .replace("OP_EQUALVERIFY", op_equalverify_with_modulo)
        .replace("OP_EQUAL", op_equal_with_modulo)
    )

    if clean_constant:
        new_verification_script += Script.parse_string("OP_SWAP OP_DROP")
    return new_verification_script


def generate_unlock(z, elements_to_select: Optional[list[int]] = None) -> Script:
    if elements_to_select is None:
        return nums_to_script(z.to_list())
    selected_elements = [z.to_list()[i] for i in elements_to_select]
    return nums_to_script(selected_elements)


def check_constant(q) -> Script:
    return Script.parse_string("OP_SWAP") + nums_to_script([q]) + Script.parse_string("OP_EQUALVERIFY")


def save_scripts(lock, unlock, save_to_json_folder, filename, test_name):
    if save_to_json_folder:
        output_dir = Path("data") / save_to_json_folder / "bilinear_pairings"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_file = output_dir / f"{filename}.json"

        data = {}

        if json_file.exists():
            with json_file.open("r") as f:
                data = json.load(f)

        data[test_name] = {"lock": lock, "unlock": unlock}

        with json_file.open("w") as f:
            json.dump(data, f, indent=4)
