import json
from pathlib import Path

from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script


def generate_verify(z) -> Script:
    out = Script()
    for ix, el in enumerate(z[::-1]):
        out += nums_to_script([el])
        if ix != len(z) - 1:
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out += Script.parse_string("OP_EQUAL")

    return out


def save_scripts(lock, unlock, save_to_json_folder, filename, test_name):
    if save_to_json_folder:
        output_dir = Path("data") / save_to_json_folder / "fields"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_file = output_dir / f"{filename}.json"

        data = {}

        if json_file.exists():
            with json_file.open("r") as f:
                data = json.load(f)

        data[test_name] = {"lock": lock, "unlock": unlock}

        with json_file.open("w") as f:
            json.dump(data, f, indent=4)
