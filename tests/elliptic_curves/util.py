import json
from pathlib import Path

from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script


def generate_verify(P, degree) -> Script:
    out = Script()
    if not P.is_infinity():
        for ix, el in enumerate(P.to_list()[::-1]):
            out += nums_to_script([el])
            if ix != len(P.to_list()) - 1:
                out += Script.parse_string("OP_EQUALVERIFY")
            else:
                out += Script.parse_string("OP_EQUAL")
    else:
        out += Script.parse_string(
            "0x00 OP_EQUALVERIFY 0x00 OP_EQUALVERIFY " * (degree - 1) + "0x00 OP_EQUALVERIFY 0x00 " "OP_EQUAL"
        )
    return out


def generate_unlock(P, degree) -> Script:
    out = Script()
    if not P.is_infinity():
        out += nums_to_script(P.to_list())
    else:
        out += Script.parse_string("0x00 0x00 " * degree)
    return out


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
