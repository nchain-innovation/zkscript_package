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
