import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Union

import tomllib

sys.path.append(str(Path(__file__).resolve().parent.parent))

from elliptic_curves.fields.fq import Fq
from elliptic_curves.instantiations.bls12_381.bls12_381 import Fr as Fr_bls12_381
from elliptic_curves.instantiations.bls12_381.bls12_381 import bls12_381 as bls12_381_curve
from elliptic_curves.instantiations.mnt4_753.mnt4_753 import Fr as Fr_mnt4_753
from elliptic_curves.instantiations.mnt4_753.mnt4_753 import mnt4_753 as mnt4_753_curve
from elliptic_curves.models.curve import BilinearPairingCurve
from tx_engine import SIGHASH, Context, Script, Tx, TxIn, TxOut, Wallet, address_to_public_key_hash, p2pkh_script
from tx_engine.interface.interface_factory import InterfaceFactory
from tx_engine.interface.verify_script import ScriptFlags, verifyscript_params

from src.zkscript.groth16.bls12_381.bls12_381 import bls12_381 as bls12_381_groth
from src.zkscript.groth16.mnt4_753.mnt4_753 import mnt4_753 as mnt4_753_groth
from src.zkscript.groth16.model.groth16 import Groth16
from src.zkscript.types.locking_keys.groth16 import Groth16LockingKey
from src.zkscript.types.unlocking_keys.groth16 import Groth16UnlockingKey

verification_flags = 1
for f in ScriptFlags._member_names_[1:-2]:
    verification_flags |= ScriptFlags._member_map_[f]


def test_network():
    config = {
        "bsv_client": {
            "interface_type": "rpc",
            "user": "bitcoin",
            "password": "bitcoin",
            "network_type": "testnet",
            "address": "127.0.0.1:18332",
            "broadcast_tx": False,
        }
    }

    return InterfaceFactory().set_config(config["bsv_client"])


def test_script_in_regtest(tx: Tx, index: int, lock: Script, flags, connection) -> bool:
    test = verifyscript_params(
        tx_hash=tx.serialize().hex(),
        index=index,
        lock_script=lock.raw_serialize().hex(),
        lock_script_amt=1,
        script_flags=flags,
    )

    return connection.verifyscript(scripts=[test], stop_on_first_invalid=False, timeout=100000)[0]["result"] == "ok"


class MillerLoopType(Enum):
    TWISTED_CURVE = ("twisted_curve",)
    BASE_CURVE = ("base_curve",)


class DenominatorElimination(Enum):
    NONE = ("none",)
    QUADRATIC = ("quadratic",)
    CUBIC = ("cubic",)


def curve_setup(curve_arg: str) -> Union[BilinearPairingCurve, Fq, Groth16, MillerLoopType, DenominatorElimination]:
    """Map command line curve argument to Python curve."""
    match curve_arg:
        case "bls12_381":
            curve = bls12_381_curve
            groth16_script = bls12_381_groth
            field = Fr_bls12_381
            miller_loop_type = MillerLoopType.TWISTED_CURVE
            denominator_elimination = DenominatorElimination.QUADRATIC
        case "mnt4_753":
            curve = mnt4_753_curve
            groth16_script = mnt4_753_groth
            field = Fr_mnt4_753
            miller_loop_type = MillerLoopType.TWISTED_CURVE
            denominator_elimination = DenominatorElimination.QUADRATIC
        case _:
            raise ValueError

    return curve, groth16_script, field, miller_loop_type, denominator_elimination


def load_public_inputs(public_inputs_serialized: bytes):
    n_public_inputs = int.from_bytes(public_inputs_serialized[:7], byteorder="little")
    field_length = (len(public_inputs_serialized) - 8) // n_public_inputs

    index = 8
    public_inputs = []
    for _ in range(n_public_inputs):
        public_inputs.extend(field.deserialise(public_inputs_serialized[index : index + field_length]).to_list())
        index += field_length
    return [1, *public_inputs]


def proof_to_unlock(
    public_statements,
    proof,
    vk,
    curve: BilinearPairingCurve,
    groth16_script: Groth16,
    miller_loop_type: MillerLoopType,
    denominator_elimination: DenominatorElimination,
) -> Script:
    groth16_proof = curve.prepare_groth16_proof(
        pub=public_statements[1:],
        proof=proof,
        vk=vk,
        miller_loop_type=miller_loop_type.value[0],
        denominator_elimination=denominator_elimination.value[0],
    )

    unlocking_key = Groth16UnlockingKey(
        pub=groth16_proof["pub"],
        A=groth16_proof["A"],
        B=groth16_proof["B"],
        C=groth16_proof["C"],
        gradients_pairings=[
            groth16_proof["lambdas_B_exp_miller_loop"],
            groth16_proof["lambdas_minus_gamma_exp_miller_loop"],
            groth16_proof["lambdas_minus_delta_exp_miller_loop"],
        ],
        inverse_miller_output=groth16_proof["inverse_miller_loop"],
        gradients_partial_sums=groth16_proof["lamdbas_partial_sums"],
        gradients_multiplication=groth16_proof["lambdas_multiplications"],
    )

    return unlocking_key.to_unlocking_script(groth16_script, None, True)


def vk_to_lock(public_statements, vk, curve: BilinearPairingCurve, groth16_script: Groth16) -> Script:
    groth16_proof = curve.prepare_groth16_proof(
        pub=public_statements[1:],
        proof=proof,
        vk=vk,
        miller_loop_type=miller_loop_type.value[0],
        denominator_elimination=denominator_elimination.value[0],
    )

    locking_key = Groth16LockingKey(
        alpha_beta=curve.pairing(vk["alpha"], vk["beta"]).to_list(),
        minus_gamma=(-vk["gamma"]).to_list(),
        minus_delta=(-vk["delta"]).to_list(),
        gamma_abc=[s.to_list() for s in vk["gamma_abc"]],
        gradients_pairings=[
            groth16_proof["lambdas_B_exp_miller_loop"],
            groth16_proof["lambdas_minus_gamma_exp_miller_loop"],
            groth16_proof["lambdas_minus_delta_exp_miller_loop"],
        ],
    )

    return groth16_script.groth16_verifier(
        locking_key=locking_key,
        modulo_threshold=200 * 8,
        check_constant=True,
        clean_constant=True,
    )


def save_data_to_file(data: list[str], key: list[str], filename: str):
    data_dir = Path(__file__).resolve().parent / "outputs"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_to_write = []
    for k, d in zip(key, data):
        data_to_write.append({k: d})
    with Path.open(data_dir / f"{filename}.json", "w") as f:
        f.write(json.dumps(data_to_write))


def funding_tx_to_locked_tx(funding_tx: Tx, index: int, lock: Script, fee_rate: float, private_key: Wallet) -> Tx:
    funding_tx_out = funding_tx.tx_outs[index]

    # Construct tx locked with zkp
    locked_tx_out = TxOut(amount=funding_tx_out.amount, script_pubkey=lock)

    funding_tx_in = TxIn(prev_tx=funding_tx.id(), prev_index=index, script=Script())

    locked_tx = Tx(version=1, tx_ins=[funding_tx_in], tx_outs=[locked_tx_out], locktime=0)
    # Update amount to match fee_rate
    locked_tx.tx_outs = [
        TxOut(amount=funding_tx_out.amount - int(fee_rate * len(locked_tx.serialize()) / 1000), script_pubkey=lock)
    ]
    locked_tx_signed = private_key.sign_tx_sighash(
        index=index, input_pytx=funding_tx, pytx=locked_tx, sighash_type=SIGHASH.ALL_FORKID
    )
    # Assert correct signing
    locked_tx_signed.validate([funding_tx])

    return locked_tx_signed


def locked_tx_to_spending_tx(tx: Tx, index: int, unlock: Script, fee_rate: float, private_key: Wallet) -> Tx:
    spending_tx_in = TxIn(prev_tx=tx.id(), prev_index=index, script=unlock)

    spending_tx_out = TxOut(
        amount=tx.tx_outs[0].amount, script_pubkey=p2pkh_script(address_to_public_key_hash(private_key.get_address()))
    )

    spending_tx = Tx(version=1, tx_ins=[spending_tx_in], tx_outs=[spending_tx_out], locktime=0)
    # Update amount to match fee_rate
    spending_tx.tx_outs = [
        TxOut(
            amount=tx.tx_outs[0].amount - int(len(spending_tx.serialize()) * fee_rate / 1000),
            script_pubkey=p2pkh_script(address_to_public_key_hash(private_key.get_address())),
        )
    ]

    return spending_tx


def set_up_network_connection(network):
    """Set up network connection."""
    return InterfaceFactory().set_config({"interface_type": "woc", "network_type": network})


parser = argparse.ArgumentParser(
    description="Given a public statement, a Groth16 proof and verifying key, generate locking and unlocking script. \
        If funding UTXO (P2PKH) is supplied, create a couple of transactions:\
              one spending the UTXO and creating the ZKP verifier, \
                one spending the verifier and returning the amount to same PubKey"
)
parser.add_argument(
    "--dir",
    type=str,
    choices=["square_root", "sha256", "ai_inference"],
    help="Directory from which to get statement, proof and verifying key",
)
parser.add_argument(
    "--curve", type=str, choices=["bls12_381", "mnt4_753"], help="Curve over which Groth16 is instantiated"
)
parser.add_argument(
    "--config", type=str, help="JSON configuration file for transaction construction and broadcast", required=False
)
parser.add_argument("--regtest", type=bool, help="Test in regtest", default=False, required=False)

if __name__ == "__main__":
    # Fetch cli arguments
    args = parser.parse_args()
    data_dir = Path(args.dir)
    curve = args.curve
    config_path = Path(args.config) if args.config is not None else None
    test_in_regtest = args.regtest

    # Set up curve
    curve, groth16_script, field, miller_loop_type, denominator_elimination = curve_setup(args.curve)

    # Load proof, vk
    proof = curve.deserialise_proof(json.load(Path.open(data_dir / "proof/proof.json"))["proof"])
    vk = curve.deserialise_vk(json.load(Path.open(data_dir / "proof/verifying_key.json"))["verifying_key"])
    # Load public inputs
    public_inputs = load_public_inputs(json.load(Path.open(data_dir / "proof/public_inputs.json"))["public_inputs"])

    # Construct locking and unlocking scripts
    lock = vk_to_lock(public_inputs, vk, curve, groth16_script)
    unlock = proof_to_unlock(public_inputs, proof, vk, curve, groth16_script, miller_loop_type, denominator_elimination)

    context = Context(script=unlock + lock)
    assert context.evaluate(), "Evaluation using Context failed"

    if not config_path:
        save_data_to_file(
            [lock.to_string(), lock.serialize().hex()],
            ["locking_script", "locking_script_hex"],
            f"locking_script_{data_dir}",
        )
        save_data_to_file(
            [unlock.to_string(), unlock.serialize().hex()],
            ["unlocking_script", "unlocking_script_hex"],
            f"unlocking_script_{data_dir}",
        )
    else:
        # Fetch configuration parameters
        with Path.open(config_path, "rb") as f:
            config = tomllib.load(f)
        tx = config["tx"]
        index = config["index"]
        private_key = config["private_key"]
        network = config["network"]
        broadcast = config["broadcast"]
        fee_rate = config["fee_rate"]

        # Set up connection
        connection = set_up_network_connection(network)

        # Instantiate private_key and fetch funding_tx
        private_key = Wallet(private_key)
        funding_tx = Tx.parse_hexstr(connection.get_raw_transaction(tx))

        # Locked tx and spending tx
        tx_locked_with_zkp = funding_tx_to_locked_tx(funding_tx, index, lock, fee_rate, private_key)
        spending_tx = locked_tx_to_spending_tx(tx_locked_with_zkp, 0, unlock, fee_rate, private_key)

        if test_in_regtest:
            bsv_regtest = test_network()
            assert test_script_in_regtest(spending_tx, 0, lock, verification_flags, bsv_regtest)

        # Save data to file
        save_data_to_file(
            [tx_locked_with_zkp.serialize().hex()], ["tx_locked_with_zkp"], f"tx_locked_with_zkp_{data_dir}"
        )
        save_data_to_file([spending_tx.serialize().hex()], ["spending_tx"], f"spending_tx_{data_dir}")

        if broadcast:
            if curve == "mnt4_753":
                msg = "Broadcast is not supported for curve MNT4_753 yet"
                raise ValueError(msg)

            connection.broadcast_tx(tx_locked_with_zkp.serialize().hex())
            connection.broadcast_tx(spending_tx.serialize().hex())
