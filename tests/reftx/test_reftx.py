import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from elliptic_curves.instantiations.bls12_381.bls12_381 import BLS12_381, ProofBls12381, VerifyingKeyBls12381
from tx_engine import SIGHASH, Context, Script, Tx, TxIn, sig_hash

from src.zkscript.groth16.bls12_381.bls12_381 import bls12_381
from src.zkscript.reftx.reftx import RefTx
from src.zkscript.types.locking_keys.reftx import RefTxLockingKey
from src.zkscript.types.unlocking_keys.reftx import RefTxUnlockingKey


@dataclass
class Bls12381:
    q = BLS12_381.g1_field.get_modulus()
    r = BLS12_381.scalar_field.get_modulus()
    g1 = BLS12_381.g1_curve.get_generator()
    g2 = BLS12_381.g2_curve.get_generator()
    val_miller_loop = BLS12_381.pairing_engine.miller_loop_engine.val_miller_loop
    pairing_curve = BLS12_381

    # Dummy ZKP
    # Generated with secrets.randbelow(r - 1) + 1
    A_ = 33976064719184601046772332296059783359114154888771311478941393763485422892419
    B_ = 34384663481284015822004772645526885025674590588008966092270502606290692706039
    C_ = 24893988411182277785498905442769971411187449562420914731983022451448972146513

    A = g1.multiply(A_)
    B = g2.multiply(B_)
    C = g1.multiply(C_)

    proof = ProofBls12381(
        A,
        B,
        C,
    )

    # Dummy tx
    tx = Tx(
        version=1,
        tx_ins=[
            TxIn(
                prev_tx="3ba86485b1a52dbdee528654bd3589003043d08dfebecb8f9ebd99107989709b",
                prev_index=0,
                script=Script(),
            )
        ],
        tx_outs=[],
        locktime=0,
    )

    sighash = sig_hash(tx, 0, Script(), 100, SIGHASH.ALL_FORKID)

    # Dummy sighash chunks
    sighash_chunks = [int.from_bytes(sighash[:16]), int.from_bytes(sighash[16:])]

    # Dummy parameters public inputs
    n_pub_l_out = 2
    n_pub_u_stx = 3
    n_sighash_chunks = len(sighash_chunks)
    n_pub_ext = n_pub_l_out + n_pub_u_stx + n_sighash_chunks + 1

    # Public inputs
    pub_l_out = [
        [
            13415718076089370305826944785579239883651324784255574470329600688556558879623,
            43953503125262332579469682660278827421180625581195864128335243058824679100119,
        ],
        [
            35527880343125301181407542593069625141487329149327381234838070585002862830274,
            13264923715511738715634318137327806433483777514511257124665744590369323230736,
        ],
    ]

    pub_u_stx = [
        [
            27619361028686641000987135718602651711570749029825566255823031863352741505945,
            47452903718925205400929402263085824841143092607238758025139778290974034999981,
            17709397950792009628325203329420608167200624170233474246319206120297872760351,
        ],
        [
            16538324265438941952483641678367270790995842653489263285292278123405871130892,
            31944586111654427657321910294173196374777631232782995865421257531931976204818,
            14815944007104580465517863736169731435847681801022088657748001002893367857727,
        ],
    ]

    # Max multipliers
    max_multipliers = [None, None]

    # Dummy vk
    dlog_gamma_abc = [
        26859453423417183608099970269163549680319987295528605568651853064527304156677,
        38815809421335833942240584020860740039208487169163088170149194033298133063787,
        25555548930232095688990974275611581610449039676777562674923664893799263954086,
        9060328591727367729632255204965393346610698792723945877643359886579803634631,
        27398387531305677090221281399451613334882142837248679517978553495996911706261,
        1785914124199905738824258035853431543932270130089188051599752561277577525990,
        2142337593184753186874436145460379507775033499594176462982061343822615127237,
        24259212385275778900709787094270330925347317045396090115978062002600952840122,
    ]
    gamma_abc = []
    for i in range(n_pub_ext):
        gamma_abc.append(g1.multiply(dlog_gamma_abc[i]))

    alpha_ = 12790544464366708614940994215014625841059650806301063465359886873486625690547
    beta_ = 35703396574432322187740701285564343485982931931825512168376677487234446722993
    gamma_ = 39343400274038067941958661494186555637424382984868274330750039783384953010645
    delta_ = 2254455857535174888113934810625770138551286599034257880685085874098503964843

    alpha = g1.multiply(alpha_)
    beta = g2.multiply(beta_)
    gamma = g2.multiply(gamma_)
    delta = g2.multiply(delta_)

    pub_extended = []
    sum_gamma_abc = [g1.multiply(0)] * 2
    alpha_beta = []
    precomputed_l_out = [gamma_abc[0]] * 2
    gamma_abc_mod = []
    pub_mod = []
    vk = []
    cache_vk = []
    prepared_vk = []
    prepared_proofs = []

    for j in range(2):
        pub_extended.append(
            [1, *pub_l_out[j], *sighash_chunks, *pub_u_stx[j]],
        )

        for i in range(len(gamma_abc)):
            sum_gamma_abc[j] += gamma_abc[i].multiply(pub_extended[j][i])

        alpha_beta.append(
            BLS12_381.pairing([A, sum_gamma_abc[j], C], [B, -gamma, -delta]),
        )

        for i, scalar in enumerate(pub_l_out[j]):
            precomputed_l_out[j] += gamma_abc[i + 1].multiply(scalar)

        gamma_abc_mod.append([precomputed_l_out[j], *gamma_abc[n_pub_l_out + 1 :]])

        pub_mod.append(pub_extended[j][n_pub_l_out + 1 :])

        vk.append(VerifyingKeyBls12381(alpha, beta, gamma, delta, gamma_abc_mod[j]))

        cache_vk.append(vk[j].prepare())
        prepared_vk.append(vk[j].prepare_for_zkscript(cache_vk[j]))
        prepared_proofs.append(
            proof.prepare_for_zkscript(cache_vk[j], pub_mod[j]),
        )

    test_script = RefTx(bls12_381)
    filename = "bls12_381"


def save_scripts(lock, unlock, save_to_json_folder, filename, test_name):
    if save_to_json_folder:
        output_dir = Path("data") / save_to_json_folder / "groth16"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_file = output_dir / f"{filename}.json"

        data = {}

        if json_file.exists():
            with json_file.open("r") as f:
                data = json.load(f)

        data[test_name] = {"lock": lock, "unlock": unlock}

        with json_file.open("w") as f:
            json.dump(data, f, indent=4)


@pytest.mark.parametrize(
    ("config", "prepared_vk", "alpha_beta", "prepared_proof", "max_multipliers"),
    [
        (
            Bls12381,
            Bls12381.prepared_vk[0],
            Bls12381.alpha_beta[0],
            Bls12381.prepared_proofs[0],
            Bls12381.max_multipliers[0],
        ),
        (
            Bls12381,
            Bls12381.prepared_vk[1],
            Bls12381.alpha_beta[1],
            Bls12381.prepared_proofs[1],
            Bls12381.max_multipliers[1],
        ),
    ],
)
def test_reftx(
    config,
    prepared_vk,
    alpha_beta,
    prepared_proof,
    max_multipliers,
    save_to_json_folder,
):
    unlock_key = RefTxUnlockingKey.from_data(
        groth16_model=bls12_381,
        pub=prepared_proof.public_statements,
        A=prepared_proof.a,
        B=prepared_proof.b,
        C=prepared_proof.c,
        gradients_pairings=[
            prepared_proof.gradients_b,
            prepared_proof.gradients_minus_gamma,
            prepared_proof.gradients_minus_delta,
        ],
        gradients_multiplications=prepared_proof.gradients_multiplications,
        max_multipliers=max_multipliers,
        gradients_additions=prepared_proof.gradients_additions,
        inverse_miller_output=prepared_proof.inverse_miller_loop,
        gradient_precomputed_l_out=prepared_proof.gradient_gamma_abc_zero,
    )

    unlock = unlock_key.to_unlocking_script(bls12_381)

    locking_key = RefTxLockingKey(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=prepared_vk.minus_gamma,
        minus_delta=prepared_vk.minus_delta,
        precomputed_l_out=prepared_vk.gamma_abc[0],
        gamma_abc_without_l_out=prepared_vk.gamma_abc[1:],
        gradients_pairings=[
            prepared_vk.gradients_minus_gamma,
            prepared_vk.gradients_minus_delta,
        ],
        sighash_flags=SIGHASH.ALL_FORKID,
    )

    lock = config.test_script.locking_script(
        sighash_flags=SIGHASH.ALL_FORKID,
        locking_key=locking_key,
        modulo_threshold=200 * 8,
        max_multipliers=None,
        check_constant=True,
    )

    context = Context(script=unlock + lock, z=config.sighash)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, config.filename, "reftx")
