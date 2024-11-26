import json
from dataclasses import dataclass
from pathlib import Path
from random import randint, seed

import pytest
from elliptic_curves.instantiations.bls12_381.bls12_381 import bls12_381 as bls12_381_curve
from elliptic_curves.instantiations.mnt4_753.mnt4_753 import mnt4_753 as mnt4_753_curve
from tx_engine import Context

from src.zkscript.groth16.bls12_381.bls12_381 import bls12_381
from src.zkscript.groth16.mnt4_753.mnt4_753 import mnt4_753
from src.zkscript.types.locking_keys.groth16 import Groth16LockingKey
from src.zkscript.types.unlocking_keys.groth16 import Groth16UnlockingKey


@dataclass
class Bls12381:
    q = bls12_381_curve.q
    r = bls12_381_curve.r
    g1 = bls12_381_curve.g1
    g2 = bls12_381_curve.g2
    val_miller_loop = bls12_381_curve.val_miller_loop

    # Dummy ZKP
    # Generated with secrets.randbelow(r - 1) + 1
    A_ = 33976064719184601046772332296059783359114154888771311478941393763485422892419
    B_ = 34384663481284015822004772645526885025674590588008966092270502606290692706039
    C_ = 24893988411182277785498905442769971411187449562420914731983022451448972146513

    A = g1.multiply(A_)
    B = g2.multiply(B_)
    C = g1.multiply(C_)

    # First two are fixed, next three are generated with secrets.randbelow(r), last one test case in which sum_gamma_abc
    # is the point at infinity
    pub_statement = [
        1,
        0,
        3060811274857224904833047709398271967974074288386860351197236696152656573180,
        27390874479047017110851549424990220824522965971102888510629230366504674671506,
        24349152937740702231723796066510072408409883142298395590343084869732829436096,
        0,
    ]

    # Dummy CRS
    # Generated with secrets.randbelow(r - 1) + 1
    alpha_ = 12790544464366708614940994215014625841059650806301063465359886873486625690547
    beta_ = 35703396574432322187740701285564343485982931931825512168376677487234446722993
    gamma_ = 39343400274038067941958661494186555637424382984868274330750039783384953010645
    delta_ = 2254455857535174888113934810625770138551286599034257880685085874098503964843

    alpha = g1.multiply(alpha_)
    beta = g2.multiply(beta_)
    gamma = g2.multiply(gamma_)
    delta = g2.multiply(delta_)

    # Generated with secrets.randbelow(r - 1) + 1
    dlog_gamma_abc = [
        7765330906204304295426790574908159941776455820436175505039457880771513289924,
        36701720065583381165641451645092405804313763750254333987822772249896328625776,
        40058876863170189709897912667477024643085019141260655486881773835332888450386,
        35077936964151632078894217228748397595635056485526656284392370421457831299978,
        19796534658721255121573814519403587720342973345819112630333078798426481220095,
        29146420488221813783708258825528845342042299067751285391286198919801338911378,
    ]

    gamma_abc = []
    for i in range(len(dlog_gamma_abc)):
        gamma_abc.append(g1.multiply(dlog_gamma_abc[i]))

    sum_gamma_abc = g1.multiply(0)
    for i in range(len(gamma_abc)):
        sum_gamma_abc += gamma_abc[i].multiply(pub_statement[i])

    alpha_beta = bls12_381_curve.triple_pairing(A, sum_gamma_abc, C, B, -gamma, -delta)

    vk = {"alpha": alpha, "beta": beta, "gamma": gamma, "delta": delta, "gamma_abc": gamma_abc}

    groth16_proof = bls12_381_curve.prepare_groth16_proof(
        pub=pub_statement[1:],
        proof={"a": A, "b": B, "c": C},
        vk=vk,
        miller_loop_type="twisted_curve",
        denominator_elimination="quadratic",
    )

    test_script = bls12_381

    filename = "bls12_381"


@dataclass
class Mnt4753:
    q = mnt4_753_curve.q
    r = mnt4_753_curve.r
    g1 = mnt4_753_curve.g1
    g2 = mnt4_753_curve.g2
    val_miller_loop = mnt4_753_curve.val_miller_loop

    # Dummy ZKP
    # Generated with secrets.randbelow(r - 1) + 1
    A_ = 20685711118128018278577076187124439253535081792789487854656966629103541188574298302986578360892676710063145828379557876845483259663753419676916503957449071854672270209733450720780810697231576421148520499318568528943855390997855  # noqa: E501
    B_ = 10913940172823037511528542521281694537711305786439658931546735410058823696897795322889592454273121147796148246597903966760904562051442102478663630338135590868056774144732387661381147276614868457892761856778474528063118615025742  # noqa: E501
    C_ = 25386220775058469612258618922794882094196968365629909057619064823363542039782881940261788354701479078497151296275017878742541286692577001102414656379282134029380976876552793116084538258674537965038965715796271131060116506301344  # noqa: E501

    A = g1.multiply(A_)
    B = g2.multiply(B_)
    C = g1.multiply(C_)

    # First two are fixed, next three are generated with secrets.randbelow(r), last one test case in which sum_gamma_abc
    # is the point at infinity
    pub_statement = [
        1,
        0,
        3800869276070790397500879783445441002239131304875812449940885748039214325636107043746181943692913794384318119948503065800442782298175442633374022885239310799719619346136657477875024060132795358959197893998611200389168111447311,
        28781452683004534275964361805323957053197312054729383211457538421523515999686407551486887390207945443601268123372819585278853990679379332656283982884473022143950452547357041406053247908500379416739218268832322803357589353142668,
        1467112264393594915737484231842743900018280034283544779833281854093164556016772674684703892580610835986072436711848603973015705524563724870838125780491307338082686169926744047799657227529532719071228407008026743740303534464202,
        0,
    ]

    # Dummy CRS
    # Generated with secrets.randbelow(r - 1) + 1
    alpha_ = 31774848307725317287807854307059955440695670767099429336741197611837162219770984409039832154438341924539101763589541517358114489981096227839583222532166563948713694115757041175897741744357274577465034682372553435010637556048389  # noqa: E501
    beta_ = 27957933549639411972169557567905301666128915531662918426215532898279130339811666109926405597538726209923184740320711625758817287032601580827144804408700846979753438333131678358290874097956082878959877551474753422260292428105901  # noqa: E501
    gamma_ = 9246782951337481962710337158903104878055522046608314528412736430197478735861776610651076911425064288414461871149367605868452112761600201292818833001670340865354594308486967704356083087028821146299613519899584985360529931685790  # noqa: E501
    delta_ = 14587553952064230472663635149860058654431696341799079846124123793396752090009295603630133161855409865109674204519940100418930028269745012291845079348281354867160964177628831590274757261894618435044807630704851331792280125029891  # noqa: E501

    alpha = g1.multiply(alpha_)
    beta = g2.multiply(beta_)
    gamma = g2.multiply(gamma_)
    delta = g2.multiply(delta_)

    # Generated with secrets.randbelow(r - 1) + 1
    dlog_gamma_abc = [
        2090592671794039469147592651060274965117396024144467329885866277911505284507163662590143253110243395613526144663947900795678248865818677643746945729528483577462816793825129876508332662392524101179200822841937992770454897113864,
        24899632621882647423465524815788124042623362294874187323765229453730840070685795908323127246073174260856889915662941990703143656939127369632498908497810143587269213960451276195631909649325664490751106628646145447812097035848617,
        36842006389036844587724145516891950954911262613081525123183724525224398290876304709440508650300970108140214458545040679821237114086126957656014033638682744161953337522315343188768390418904646273139947763712501496099473678174561,
        8962661991527251755632915815728596106946849838309883101001248583506213229255526351668312017961450335072477009430683375994415463254534170246219439288641899217645440444136680916173181588130202190010945452534465567659983597899356,
        22407385450471694800838416493445271412932131761359663223727750839846453295830347116980849344499925016441348215395638078979474628256394788744682418714288919256104783532224907163416673018789548122904185184714118448896624956668387,
        13760222364321929750546282525427728944438995153106356182120317122424275381548747354538668928891153531596888380019189960049885921382794074796381468007108876615969833115813340970721406990040317327896882194363710605179038555537281,
    ]

    gamma_abc = []
    for i in range(len(dlog_gamma_abc)):
        gamma_abc.append(g1.multiply(dlog_gamma_abc[i]))

    sum_gamma_abc = g1.multiply(0)
    for i in range(len(gamma_abc)):
        sum_gamma_abc += gamma_abc[i].multiply(pub_statement[i])

    alpha_beta = mnt4_753_curve.triple_pairing(A, sum_gamma_abc, C, B, -gamma, -delta)

    vk = {"alpha": alpha, "beta": beta, "gamma": gamma, "delta": delta, "gamma_abc": gamma_abc}

    groth16_proof = mnt4_753_curve.prepare_groth16_proof(
        pub=pub_statement[1:],
        proof={"a": A, "b": B, "c": C},
        vk=vk,
        miller_loop_type="twisted_curve",
        denominator_elimination="quadratic",
    )

    test_script = mnt4_753

    filename = "mnt4_753"


def generate_random_tests(curve, groth16, filename, is_minimal_example):
    A = curve.g1.multiply(randint(1, curve.r - 1))  # noqa: S311
    B = curve.g2.multiply(randint(1, curve.r - 1))  # noqa: S311
    C = curve.g1.multiply(randint(1, curve.r - 1))  # noqa: S311

    alpha = curve.g1.multiply(randint(1, curve.r - 1))  # noqa: S311
    beta = curve.g2.multiply(randint(1, curve.r - 1))  # noqa: S311
    gamma = curve.g2.multiply(randint(1, curve.r - 1))  # noqa: S311
    delta = curve.g2.multiply(randint(1, curve.r - 1))  # noqa: S311

    if is_minimal_example:
        dlog_gamma_abc = [15, 23, 11] if filename == "bls12_381" else [7, 19]
        pub_statement = [1, 5, 4] if filename == "bls12_381" else [1, 2]
    else:
        dlog_gamma_abc = [randint(1, curve.r - 1) for _ in range(6)]  # noqa: S311
        # First two are fixed, next three are random, last one test case in which sum_gamma_abc is the point at infinity
        pub_statement = [1, 0] + [randint(1, curve.r - 1) for _ in range(3)] + [0]  # noqa: S311

    gamma_abc = []
    for i in range(len(dlog_gamma_abc)):
        gamma_abc.append(curve.g1.multiply(dlog_gamma_abc[i]))

    sum_gamma_abc = curve.g1.multiply(0)
    for i in range(len(gamma_abc)):
        sum_gamma_abc += gamma_abc[i].multiply(pub_statement[i])

    vk = {"alpha": alpha, "beta": beta, "gamma": gamma, "delta": delta, "gamma_abc": gamma_abc}

    groth16_proof = curve.prepare_groth16_proof(
        pub=pub_statement[1:],
        proof={"a": A, "b": B, "c": C},
        vk=vk,
        miller_loop_type="twisted_curve",
        denominator_elimination="quadratic",
    )

    alpha_beta = curve.triple_pairing(A, sum_gamma_abc, C, B, -gamma, -delta)

    return (alpha_beta, vk, groth16_proof, groth16, filename, is_minimal_example)


def generate_test_cases(test_num, is_minimal_example=False, rnd_seed=42):
    # Parse and return config and the test_data for each config
    seed(rnd_seed)
    return [
        generate_random_tests(bls12_381_curve, bls12_381, "bls12_381", is_minimal_example) for _ in range(test_num)
    ] + [generate_random_tests(mnt4_753_curve, mnt4_753, "mnt4_753", is_minimal_example) for _ in range(test_num)]


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
    ("test_script", "vk", "alpha_beta", "groth16_proof", "filename"),
    [
        (Bls12381.test_script, Bls12381.vk, Bls12381.alpha_beta, Bls12381.groth16_proof, Bls12381.filename),
        (Mnt4753.test_script, Mnt4753.vk, Mnt4753.alpha_beta, Mnt4753.groth16_proof, Mnt4753.filename),
    ],
)
def test_groth16(test_script, vk, alpha_beta, groth16_proof, filename, save_to_json_folder):
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
    unlock = unlocking_key.to_unlocking_script(test_script, None, True)

    locking_key = Groth16LockingKey(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=(-vk["gamma"]).to_list(),
        minus_delta=(-vk["delta"]).to_list(),
        gamma_abc=[s.to_list() for s in vk["gamma_abc"]],
    )
    lock = test_script.groth16_verifier(
        locking_key,
        modulo_threshold=1,
        check_constant=True,
        clean_constant=True,
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert len(context.get_stack()) == 1
    assert len(context.get_altstack()) == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, filename, "groth16")


@pytest.mark.slow
@pytest.mark.parametrize(
    ("alpha_beta", "vk", "groth16_proof", "test_script", "filename", "is_minimal_example"),
    [
        *generate_test_cases(test_num=1, is_minimal_example=False, rnd_seed=42),
        *generate_test_cases(test_num=1, is_minimal_example=True, rnd_seed=42),
    ],
)
def test_groth16_slow(alpha_beta, vk, groth16_proof, test_script, filename, is_minimal_example, save_to_json_folder):
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
    unlock = unlocking_key.to_unlocking_script(test_script, None, True)

    locking_key = Groth16LockingKey(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=(-vk["gamma"]).to_list(),
        minus_delta=(-vk["delta"]).to_list(),
        gamma_abc=[s.to_list() for s in vk["gamma_abc"]],
    )
    lock = test_script.groth16_verifier(
        locking_key,
        modulo_threshold=200 * 8,
        check_constant=True,
        clean_constant=True,
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert len(context.get_stack()) == 1
    assert len(context.get_altstack()) == 0

    if is_minimal_example:
        print(
            "\nThe locking script size for Groth16 for the curve",
            filename,
            "with",
            ("two" if filename == "bls12_381" else "one"),
            "public",
            ("inputs" if filename == "bls12_381" else "input"),
            "is",
            len(lock.raw_serialize()),
            "bytes.",
        )

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, filename, "groth16")
