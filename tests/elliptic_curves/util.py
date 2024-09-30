import json
from pathlib import Path

from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script


def select_elements(elements: list[int], elements_to_select: list[int] | None = None):
    return elements if elements_to_select is None else [elements[i] for i in elements_to_select]


def generate_verify_point(point_p, degree) -> Script:
    out = Script()
    if not point_p.is_infinity():
        out += generate_verify_from_list(point_p.to_list())
    else:
        out += Script.parse_string(
            "0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY " * (degree - 1) + "0x00 OP_EQUALVERIFY 0x00 " "OP_EQUAL"
        )
    return out


def generate_verify_from_list(elements: list[int]) -> Script:
    out = Script()
    for ix, el in enumerate(elements[::-1]):
        out += nums_to_script([el])
        if ix != len(elements) - 1:
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out += Script.parse_string("OP_EQUAL")
    return out


def generate_unlock(point_p: list[int], degree) -> Script:
    out = Script()
    if not point_p.is_infinity():
        out += nums_to_script(point_p.to_list())
    else:
        out += Script.parse_string("0x00 0x00 " * degree)
    return out


def generate_extended_list(elements: list[list[int]], positions_elements: list[int], filler: int = 1):
    """Take a list of element a fills it with the filler element."""
    extended_list = []
    positions_elements = [*positions_elements, -1]

    for i in range(len(elements)):
        element_to_add = elements[i]
        extended_list = [*extended_list, *element_to_add]
        extended_list = [
            *extended_list,
            *[filler] * (positions_elements[i] - positions_elements[i + 1] - len(element_to_add)),
        ]

    return extended_list


def save_scripts(lock, unlock, save_to_json_folder, filename, test_name):
    if save_to_json_folder:
        output_dir = Path("data") / save_to_json_folder / "elliptic_curves"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_file = output_dir / f"{filename}.json"

        data = {}

        if json_file.exists():
            with json_file.open("r") as f:
                data = json.load(f)

        data[test_name] = {"lock": lock, "unlock": unlock}

        with json_file.open("w") as f:
            json.dump(data, f, indent=4)
