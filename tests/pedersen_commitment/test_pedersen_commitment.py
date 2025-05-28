import json
from pathlib import Path

import pytest
from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.models.ec import ShortWeierstrassEllipticCurve
from tx_engine import Context, encode_num, hash256d

from script_examples.pedersen_commitment.pedersen_commitment import PedersenCommitmentSecp256k1
from script_examples.pedersen_commitment.pedersen_unlocking_key import (
    PedersenCommitmentSecp256k1UnlockingKey,
    Secp256k1PointMultiplicationUnlockingKey,
)

modulus = 115792089237316195423570985008687907853269984665640564039457584007908834671663
order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Fq_k1 = PrimeField(modulus)
Fr_k1 = PrimeField(order)
secp256k1 = ShortWeierstrassEllipticCurve(a=Fq_k1(0), b=Fq_k1(7))
degree = 1
point_at_infinity = secp256k1.infinity()
generator = secp256k1(
    x=Fq_k1(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798),
    y=Fq_k1(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8),
    infinity=False,
)
random_point = secp256k1(
    x=Fq_k1(0xD6765EA876740CE709C9CFF7789CBF621609E8CA79134B0C0BA0768E8D3EC7B2),
    y=Fq_k1(0xDF16ACCBBA6D8D44882E95FB0D2BA4E210ABE58A32AD4F0BCC4843204E9C0F8D),
    infinity=False,
)

dummy_sig_hash_preimage = int.to_bytes(
    53458750141241331933368176931386592061784348704092867077248862953896423193426, 32
)
dummy_sig_hash = hash256d(dummy_sig_hash_preimage)

# Random message generator with secrets
m = Fr_k1(108814412420754623055061741665661169183836554621981979708040288335846227315001)
# Randomness generated with secrets
r = Fr_k1(91983874018876379023889961993961681946728348573401297229445648499213712679245)
# Points
Q = generator.multiply(m.to_list()[0])
R = random_point.multiply(r.to_list()[0])
# Commitment
commitment = Q + R
bytes_commitment = b"".join([encode_num(el) for el in commitment.to_list()])

commitment_scheme = PedersenCommitmentSecp256k1(B=generator.to_list(), H=random_point.to_list())


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


def points_to_multiplication_unlocking_data(sighash: bytes, m: int, G, Q, P):
    h = int.from_bytes(sighash)

    d = []
    d.append(Fr_k1(h) * Fr_k1(Q.x.x).invert())
    d.append(Fr_k1(h) * Fr_k1((Q + G.multiply(m)).x.x).invert())

    s = []
    s.append(Fr_k1(Q.x.x) * Fr_k1(m).invert())
    s.append(Fr_k1((Q + G.multiply(m)).x.x) * Fr_k1(m).invert())

    D = []
    D.append(G.multiply(d[0].x))
    D.append(G.multiply(d[1].x - 1))
    D.append(G.multiply(m))

    gradients = []
    gradients.append(P.gradient(-D[0]))
    gradients.append(P.gradient(-D[1]))
    gradients.append(Q.gradient(D[2]))

    return Secp256k1PointMultiplicationUnlockingKey(
        sig_hash_preimage=b"",
        h=b"",
        s=[el.to_list()[0] for el in s],
        gradients=[el.to_list()[0] for el in gradients],
        d=[el.to_list()[0] for el in d],
        D=[el.to_list() for el in D],
        Q=Q.to_list(),
        b=m,
        P=P.to_list(),
    )


@pytest.mark.parametrize(
    ("commitment", "commitment_scheme", "sig_hash", "sig_hash_preimage", "m", "r", "Q", "P", "R", "S"),
    [
        (
            bytes_commitment,
            commitment_scheme,
            dummy_sig_hash,
            dummy_sig_hash_preimage,
            m.to_list()[0],
            r.to_list()[0],
            Q,
            generator,
            R,
            random_point,
        )
    ],
)
def test_pedersen_commitment(
    commitment,
    commitment_scheme,
    sig_hash,
    sig_hash_preimage,
    m,
    r,
    Q,
    P,
    R,
    S,
    save_to_json_folder,
):
    lock = commitment_scheme.commit(commitment)

    base_point_opening_data = points_to_multiplication_unlocking_data(sig_hash, m, generator, Q, P)
    randomness_opening_data = points_to_multiplication_unlocking_data(sig_hash, r, generator, R, S)

    opening_key = PedersenCommitmentSecp256k1UnlockingKey(
        sig_hash_preimage=sig_hash_preimage,
        h=sig_hash,
        gradient=Q.gradient(R).to_list()[0],
        base_point_opening_data=base_point_opening_data,
        randomness_opening_data=randomness_opening_data,
    )
    unlock = opening_key.to_unlocking_script(append_constants=True)

    context = Context(unlock + lock, z=sig_hash)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, "Pedersen", "pedersen_commitment")
