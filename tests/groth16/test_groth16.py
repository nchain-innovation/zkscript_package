import json
import sys
from dataclasses import dataclass
from pathlib import Path
from random import randint, seed

import pytest
from elliptic_curves.instantiations.bls12_381.bls12_381 import BLS12_381, ProofBls12381, VerifyingKeyBls12381
from elliptic_curves.instantiations.mnt4_753.mnt4_753 import MNT4_753, ProofMnt4753, VerifyingKeyMnt4753
from tx_engine import Context

from src.zkscript.groth16.bls12_381.bls12_381 import bls12_381
from src.zkscript.groth16.mnt4_753.mnt4_753 import mnt4_753
from src.zkscript.script_types.locking_keys.groth16 import Groth16LockingKey, Groth16LockingKeyWithPrecomputedMsm
from src.zkscript.script_types.locking_keys.groth16_proj import (
    Groth16ProjLockingKey,
    Groth16ProjLockingKeyWithPrecomputedMsm,
)
from src.zkscript.script_types.unlocking_keys.groth16 import Groth16UnlockingKey, Groth16UnlockingKeyWithPrecomputedMsm
from src.zkscript.script_types.unlocking_keys.groth16_proj import (
    Groth16ProjUnlockingKey,
    Groth16ProjUnlockingKeyWithPrecomputedMsm,
)


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

    pub_statements = [
        # First two are fixed, next three are generated with secrets.randbelow(r),
        # last one test case in which sum_gamma_abc is the point at infinity
        [
            1,
            0,
            3060811274857224904833047709398271967974074288386860351197236696152656573180,
            27390874479047017110851549424990220824522965971102888510629230366504674671506,
            24349152937740702231723796066510072408409883142298395590343084869732829436096,
            0,
        ],
        # First is fixed, next three generated with secrets.randbelow(max_multipliers[i])
        [
            1,
            15873601289888851563210890519954554722754944672877308879146748244748648215436,
            18200759004277852045069547238917690602215856516219524855050602748049002760543,
            6624207402763485465215146574494506210670268277971846111605242550457686129604,
            7723334359066753317031400026175301517722172915552964496178764583574220787321,
            3143823999318409638568135151204909725849182090248472279935177552280870027687,
        ],
    ]

    max_multipliers = [
        # Default: r
        None,
        # Generated with secrets.randbelow(r)
        [
            48674282419960792948572465601857205496657803389507810561802118132204139818319,
            28828014628321497409813258425417715136480751747916501733157949037063021340095,
            9426102824259960575917047761056404778935153673065407357090026999444014361360,
            15159523228525613447532194300935938647513070623483703070707530544757884107632,
            9290867845475613632722678172943098621671641805019779573073747944398154759759,
        ],
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

    sum_gamma_abc = [g1.multiply(0), g1.multiply(0)]
    for j in range(2):
        for i in range(len(gamma_abc)):
            sum_gamma_abc[j] += gamma_abc[i].multiply(pub_statements[j][i])

    alpha_beta = [
        BLS12_381.pairing([A, sum_gamma_abc[0], C], [B, -gamma, -delta]),
        BLS12_381.pairing([A, sum_gamma_abc[1], C], [B, -gamma, -delta]),
    ]

    vk = VerifyingKeyBls12381(alpha, beta, gamma, delta, gamma_abc)

    proof = ProofBls12381(
        A,
        B,
        C,
    )

    cache_vk = vk.prepare()
    prepared_vk = vk.prepare_for_zkscript(cache_vk)
    prepared_proofs = [
        proof.prepare_for_zkscript(cache_vk, pub_statements[0][1:]),
        proof.prepare_for_zkscript(cache_vk, pub_statements[1][1:]),
    ]

    test_script = bls12_381

    filename = "bls12_381"


@dataclass
class Mnt4753:
    q = MNT4_753.g1_field.get_modulus()
    r = MNT4_753.scalar_field.get_modulus()
    g1 = MNT4_753.g1_curve.get_generator()
    g2 = MNT4_753.g2_curve.get_generator()
    val_miller_loop = MNT4_753.pairing_engine.miller_loop_engine.val_miller_loop
    pairing_curve = MNT4_753

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
    pub_statements = [
        [
            1,
            0,
            3800869276070790397500879783445441002239131304875812449940885748039214325636107043746181943692913794384318119948503065800442782298175442633374022885239310799719619346136657477875024060132795358959197893998611200389168111447311,
            28781452683004534275964361805323957053197312054729383211457538421523515999686407551486887390207945443601268123372819585278853990679379332656283982884473022143950452547357041406053247908500379416739218268832322803357589353142668,
            1467112264393594915737484231842743900018280034283544779833281854093164556016772674684703892580610835986072436711848603973015705524563724870838125780491307338082686169926744047799657227529532719071228407008026743740303534464202,
            0,
        ],
        [
            1,
            22011153221527638867606747211571794590718197227358838336496385777418334396996443664595798106450512215713614436370776867359413515599085351471103428661899329296711688299852880987957849458507568791454455496770126694395545718757097,
            30949058512810328257564167179736165752223431798970237651727459655087240500568311626778320308631563459488457913578974528781499177789744736639717919304436242750638244279898146182658057424381308647120846598852648503552724087277805,
            7390326651868016354968170551141356652142362217596319694877432518147590315636154285686794049336355822929046312679255058143657457564689617493201784501781039440119942968571101947228982108034339656480070405530472098124187227607365,
            15498304331516340666672360426319827093910373933279021596665184321533095563454834679200698735853414034597761546686166019542315024785843116278617822712873735245129429106018924783567212912904892589997703978207902297690291258395167,
            8561374157664351811794224646917071693762550957028622084398574670574661800711074404868001073075557068685583206545273662257986023963073452328267314664277920573689836537608018302388308895392620363451453214696046577588032369102844,
        ],
    ]

    max_multipliers = [
        # Default: r
        None,
        # Generated with secrets.randbelow(r)
        [
            22332903824394420615152979486276974397918042189462746647435789095522156384236975337361575515499716564529403147489921625521022311271361849827765232824397214629306871772923691488606653815112745434947025910691995042710298173497705,
            31158206618898976265016091224555356512346685098950342924922944329159368047571653088237950519064675011316131926763190270000097442880176987323993200129499314604455011511601338341255397384765192601075851743581781352305684754185119,
            8285619431093959234615568552994882531157519626950395190720003059292855073304576435661706935271359435362357183168221687952473161267624646752235192049455760659454873657366121204771289030693542263233323886271385651677964899042352,
            39476487257179005535114412831489574507994807326180313091930991326455393336895749412003142614961912487875436047217882394461674146569654978487889836366437789192982600665671716384887610537998635521149229463705583827430627567016684,
            11475276001327463306989756118902186888975361218125587517355841993542403776288748364181293881033782662370504831760637822611778044650835824228674930294697346584295211501459997348272874043592439556638606419544923105487115143317865,
        ],
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

    sum_gamma_abc = [g1.multiply(0), g1.multiply(0)]
    for j in range(2):
        for i in range(len(gamma_abc)):
            sum_gamma_abc[j] += gamma_abc[i].multiply(pub_statements[j][i])

    alpha_beta = [
        MNT4_753.pairing([A, sum_gamma_abc[0], C], [B, -gamma, -delta]),
        MNT4_753.pairing([A, sum_gamma_abc[1], C], [B, -gamma, -delta]),
    ]

    vk = VerifyingKeyMnt4753(alpha, beta, gamma, delta, gamma_abc)

    proof = ProofMnt4753(
        A,
        B,
        C,
    )

    cache_vk = vk.prepare()
    prepared_vk = vk.prepare_for_zkscript(cache_vk)
    prepared_proofs = [
        proof.prepare_for_zkscript(cache_vk, pub_statements[0][1:]),
        proof.prepare_for_zkscript(cache_vk, pub_statements[1][1:]),
    ]

    test_script = mnt4_753

    filename = "mnt4_753"


def generate_random_tests(curve, verifying_key_type, proof_type, groth16, filename, is_minimal_example):
    A = curve.pairing_curve.g1_curve.generate_random_point()
    B = curve.pairing_curve.g2_curve.generate_random_point()
    C = curve.pairing_curve.g1_curve.generate_random_point()

    alpha = curve.pairing_curve.g1_curve.generate_random_point()
    beta = curve.pairing_curve.g2_curve.generate_random_point()
    gamma = curve.pairing_curve.g2_curve.generate_random_point()
    delta = curve.pairing_curve.g2_curve.generate_random_point()

    if is_minimal_example:
        dlog_gamma_abc = [15, 23, 11] if filename == "bls12_381" else [7, 19]
        pub_statement = [1, 5, 4] if filename == "bls12_381" else [1, 2]
        max_multipliers = None
    else:
        dlog_gamma_abc = [randint(1, curve.r - 1) for _ in range(6)]  # noqa: S311
        max_multipliers = [randint(1, curve.r - 1) for _ in range(3)]  # noqa: S311
        # First two are fixed, next three are random, last one test case in which sum_gamma_abc is the point at infinity
        pub_statement = [1, 0] + [randint(1, max_multipliers[i]) for i in range(3)] + [0]  # noqa: S311
        max_multipliers = [curve.r, *max_multipliers, curve.r]

    gamma_abc = []
    for i in range(len(dlog_gamma_abc)):
        gamma_abc.append(curve.g1.multiply(dlog_gamma_abc[i]))

    sum_gamma_abc = curve.g1.multiply(0)
    for i in range(len(gamma_abc)):
        sum_gamma_abc += gamma_abc[i].multiply(pub_statement[i])

    vk = verifying_key_type(alpha, beta, gamma, delta, gamma_abc)

    proof = proof_type(
        A,
        B,
        C,
    )

    cache_vk = vk.prepare()
    prepared_vk = vk.prepare_for_zkscript(cache_vk)
    prepared_proof = proof.prepare_for_zkscript(cache_vk, pub_statement[1:])

    alpha_beta = curve.pairing_curve.pairing([A, sum_gamma_abc, C], [B, -gamma, -delta])

    return (alpha_beta, prepared_vk, prepared_proof, groth16, filename, max_multipliers, is_minimal_example)


def generate_test_cases(test_num, is_minimal_example=False, rnd_seed=42):
    # Parse and return config and the test_data for each config
    seed(rnd_seed)
    return [
        *[
            generate_random_tests(
                Bls12381, VerifyingKeyBls12381, ProofBls12381, bls12_381, "bls12_381", is_minimal_example
            )
            for _ in range(test_num)
        ],
        *[
            generate_random_tests(Mnt4753, VerifyingKeyMnt4753, ProofMnt4753, mnt4_753, "mnt4_753", is_minimal_example)
            for _ in range(test_num)
        ],
    ]


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


@pytest.mark.parametrize("extractable_inputs", [1, 0])
@pytest.mark.parametrize(
    ("test_script", "prepared_vk", "alpha_beta", "prepared_proof", "max_multipliers", "filename"),
    [
        (
            Bls12381.test_script,
            Bls12381.prepared_vk,
            Bls12381.alpha_beta[0],
            Bls12381.prepared_proofs[0],
            Bls12381.max_multipliers[0],
            Bls12381.filename,
        ),
        (
            Bls12381.test_script,
            Bls12381.prepared_vk,
            Bls12381.alpha_beta[1],
            Bls12381.prepared_proofs[1],
            Bls12381.max_multipliers[1],
            Bls12381.filename,
        ),
        (
            Mnt4753.test_script,
            Mnt4753.prepared_vk,
            Mnt4753.alpha_beta[0],
            Mnt4753.prepared_proofs[0],
            Mnt4753.max_multipliers[0],
            Mnt4753.filename,
        ),
        (
            Mnt4753.test_script,
            Mnt4753.prepared_vk,
            Mnt4753.alpha_beta[1],
            Mnt4753.prepared_proofs[1],
            Mnt4753.max_multipliers[1],
            Mnt4753.filename,
        ),
    ],
)
@pytest.mark.parametrize("precomputed_gradients_in_unlocking", [True, False])
def test_groth16(
    test_script,
    prepared_vk,
    alpha_beta,
    prepared_proof,
    max_multipliers,
    extractable_inputs,
    precomputed_gradients_in_unlocking,
    filename,
    save_to_json_folder,
):
    unlocking_key = Groth16UnlockingKey.from_data(
        groth16_model=test_script,
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
        gradient_gamma_abc_zero=prepared_proof.gradient_gamma_abc_zero,
        has_precomputed_gradients=precomputed_gradients_in_unlocking,
    )
    unlock = unlocking_key.to_unlocking_script(test_script, True, extractable_inputs)

    locking_key = Groth16LockingKey(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=prepared_vk.minus_gamma,
        minus_delta=prepared_vk.minus_delta,
        gamma_abc=prepared_vk.gamma_abc,
        gradients_pairings=[
            prepared_vk.gradients_minus_gamma,
            prepared_vk.gradients_minus_delta,
        ],
        has_precomputed_gradients=not precomputed_gradients_in_unlocking,
    )
    lock = test_script.groth16_verifier(
        locking_key,
        modulo_threshold=1,
        extractable_inputs=extractable_inputs,
        max_multipliers=max_multipliers,
        check_constant=True,
        clean_constant=True,
    )
    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, filename, "groth16")


@pytest.mark.parametrize("precomputed_gradients_in_unlocking", [True, False])
@pytest.mark.parametrize(
    ("test_script", "prepared_vk", "alpha_beta", "precomputed_msm", "prepared_proof", "filename"),
    [
        (
            Bls12381.test_script,
            Bls12381.prepared_vk,
            Bls12381.alpha_beta[0],
            Bls12381.sum_gamma_abc[0],
            Bls12381.prepared_proofs[0],
            Bls12381.filename,
        ),
        (
            Bls12381.test_script,
            Bls12381.prepared_vk,
            Bls12381.alpha_beta[1],
            Bls12381.sum_gamma_abc[1],
            Bls12381.prepared_proofs[1],
            Bls12381.filename,
        ),
        (
            Mnt4753.test_script,
            Mnt4753.prepared_vk,
            Mnt4753.alpha_beta[0],
            Mnt4753.sum_gamma_abc[0],
            Mnt4753.prepared_proofs[0],
            Mnt4753.filename,
        ),
        (
            Mnt4753.test_script,
            Mnt4753.prepared_vk,
            Mnt4753.alpha_beta[1],
            Mnt4753.sum_gamma_abc[1],
            Mnt4753.prepared_proofs[1],
            Mnt4753.filename,
        ),
    ],
)
def test_groth16_with_precomputed_msm(
    test_script,
    prepared_vk,
    alpha_beta,
    precomputed_msm,
    prepared_proof,
    precomputed_gradients_in_unlocking,
    filename,
    save_to_json_folder,
):
    unlocking_key = Groth16UnlockingKeyWithPrecomputedMsm(
        A=prepared_proof.a,
        B=prepared_proof.b,
        C=prepared_proof.c,
        gradients_pairings=[
            prepared_proof.gradients_b,
            prepared_proof.gradients_minus_gamma,
            prepared_proof.gradients_minus_delta,
        ],
        inverse_miller_output=prepared_proof.inverse_miller_loop,
        precomputed_msm=precomputed_msm.to_list(),
        has_precomputed_gradients=precomputed_gradients_in_unlocking,
    )

    unlock = unlocking_key.to_unlocking_script(test_script, True)

    locking_key = Groth16LockingKeyWithPrecomputedMsm(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=prepared_vk.minus_gamma,
        minus_delta=prepared_vk.minus_delta,
        gradients_pairings=[
            prepared_vk.gradients_minus_gamma,
            prepared_vk.gradients_minus_delta,
        ],
        has_precomputed_gradients=not precomputed_gradients_in_unlocking,
    )

    lock = test_script.groth16_verifier_with_precomputed_msm(
        locking_key,
        modulo_threshold=1,
        check_constant=True,
        clean_constant=True,
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, filename, "groth16")


@pytest.mark.slow
@pytest.mark.parametrize("precomputed_gradients_in_unlocking", [True, False])
@pytest.mark.parametrize("extractable_inputs", [1, 0])
@pytest.mark.parametrize(
    ("alpha_beta", "prepared_vk", "prepared_proof", "test_script", "filename", "max_multipliers", "is_minimal_example"),
    [
        *generate_test_cases(test_num=1, is_minimal_example=False, rnd_seed=42),
        *generate_test_cases(test_num=1, is_minimal_example=True, rnd_seed=42),
    ],
)
def test_groth16_slow(
    alpha_beta,
    prepared_vk,
    prepared_proof,
    test_script,
    filename,
    max_multipliers,
    extractable_inputs,
    is_minimal_example,
    precomputed_gradients_in_unlocking,
    save_to_json_folder,
):
    unlocking_key = Groth16UnlockingKey.from_data(
        groth16_model=test_script,
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
        gradient_gamma_abc_zero=prepared_proof.gradient_gamma_abc_zero,
        has_precomputed_gradients=precomputed_gradients_in_unlocking,
    )
    unlock = unlocking_key.to_unlocking_script(test_script, True, extractable_inputs)

    locking_key = Groth16LockingKey(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=prepared_vk.minus_gamma,
        minus_delta=prepared_vk.minus_delta,
        gamma_abc=prepared_vk.gamma_abc,
        gradients_pairings=[
            prepared_vk.gradients_minus_gamma,
            prepared_vk.gradients_minus_delta,
        ],
        has_precomputed_gradients=not precomputed_gradients_in_unlocking,
    )
    lock = test_script.groth16_verifier(
        locking_key,
        modulo_threshold=200 * 8,
        extractable_inputs=extractable_inputs,
        max_multipliers=max_multipliers,
        check_constant=True,
        clean_constant=True,
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if is_minimal_example:
        num_public_inputs = "two public inputs" if filename == "bls12_381" else "one public input"
        unlocking_script_type = "un" if precomputed_gradients_in_unlocking else ""
        message = (
            f"\nThe script size for Groth16 for the curve {filename} with {num_public_inputs} "
            f"and precomputed gradients in the {unlocking_script_type}locking script is:\n"
            f"Locking script: {len(lock.raw_serialize())} bytes.\n"
            f"Unlocking script: {len(unlock.raw_serialize())} bytes.\t"
        )

        sys.stdout.write(message)

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, filename, "groth16")


@pytest.mark.parametrize("extractable_inputs", [1])
@pytest.mark.parametrize(
    ("test_script", "prepared_vk", "alpha_beta", "prepared_proof", "max_multipliers", "filename"),
    [
        (
            Bls12381.test_script,
            Bls12381.prepared_vk,
            Bls12381.alpha_beta[0],
            Bls12381.prepared_proofs[0],
            Bls12381.max_multipliers[0],
            Bls12381.filename,
        ),
        (
            Bls12381.test_script,
            Bls12381.prepared_vk,
            Bls12381.alpha_beta[1],
            Bls12381.prepared_proofs[1],
            Bls12381.max_multipliers[1],
            Bls12381.filename,
        ),
        (
            Mnt4753.test_script,
            Mnt4753.prepared_vk,
            Mnt4753.alpha_beta[0],
            Mnt4753.prepared_proofs[0],
            Mnt4753.max_multipliers[0],
            Mnt4753.filename,
        ),
        (
            Mnt4753.test_script,
            Mnt4753.prepared_vk,
            Mnt4753.alpha_beta[1],
            Mnt4753.prepared_proofs[1],
            Mnt4753.max_multipliers[1],
            Mnt4753.filename,
        ),
    ],
)
def test_groth16_proj(
    test_script,
    prepared_vk,
    alpha_beta,
    prepared_proof,
    max_multipliers,
    extractable_inputs,
    filename,
    save_to_json_folder,
):
    unlocking_key = Groth16ProjUnlockingKey.from_data(
        groth16_model=test_script,
        pub=prepared_proof.public_statements,
        A=prepared_proof.a,
        B=prepared_proof.b,
        C=prepared_proof.c,
        max_multipliers=max_multipliers,
        inverse_miller_output=prepared_proof.inverse_miller_loop,
    )
    unlock = unlocking_key.to_unlocking_script(test_script, True, extractable_inputs)

    locking_key = Groth16ProjLockingKey(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=prepared_vk.minus_gamma,
        minus_delta=prepared_vk.minus_delta,
        gamma_abc=prepared_vk.gamma_abc,
    )
    lock = test_script.groth16_verifier_proj(
        locking_key,
        modulo_threshold=1,
        max_multipliers=max_multipliers,
        extractable_inputs=extractable_inputs,
        check_constant=True,
        clean_constant=True,
    )
    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, filename, "groth16")


@pytest.mark.parametrize(
    ("test_script", "prepared_vk", "alpha_beta", "precomputed_msm", "prepared_proof", "filename"),
    [
        (
            Bls12381.test_script,
            Bls12381.prepared_vk,
            Bls12381.alpha_beta[0],
            Bls12381.sum_gamma_abc[0],
            Bls12381.prepared_proofs[0],
            Bls12381.filename,
        ),
        (
            Bls12381.test_script,
            Bls12381.prepared_vk,
            Bls12381.alpha_beta[1],
            Bls12381.sum_gamma_abc[1],
            Bls12381.prepared_proofs[1],
            Bls12381.filename,
        ),
        (
            Mnt4753.test_script,
            Mnt4753.prepared_vk,
            Mnt4753.alpha_beta[0],
            Mnt4753.sum_gamma_abc[0],
            Mnt4753.prepared_proofs[0],
            Mnt4753.filename,
        ),
        (
            Mnt4753.test_script,
            Mnt4753.prepared_vk,
            Mnt4753.alpha_beta[1],
            Mnt4753.sum_gamma_abc[1],
            Mnt4753.prepared_proofs[1],
            Mnt4753.filename,
        ),
    ],
)
def test_groth16_proj_with_precomputed_msm(
    test_script,
    prepared_vk,
    alpha_beta,
    precomputed_msm,
    prepared_proof,
    filename,
    save_to_json_folder,
):
    unlocking_key = Groth16ProjUnlockingKeyWithPrecomputedMsm(
        A=prepared_proof.a,
        B=prepared_proof.b,
        C=prepared_proof.c,
        inverse_miller_output=prepared_proof.inverse_miller_loop,
        precomputed_msm=precomputed_msm.to_list(),
    )

    unlock = unlocking_key.to_unlocking_script(test_script, True)

    locking_key = Groth16ProjLockingKeyWithPrecomputedMsm(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=prepared_vk.minus_gamma,
        minus_delta=prepared_vk.minus_delta,
    )

    lock = test_script.groth16_verifier_proj_with_precomputed_msm(
        locking_key,
        modulo_threshold=1,
        check_constant=True,
        clean_constant=True,
    )

    context = Context(script=unlock + lock)
    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, filename, "groth16")


@pytest.mark.slow
@pytest.mark.parametrize("extractable_inputs", [1, 0])
@pytest.mark.parametrize(
    ("alpha_beta", "prepared_vk", "prepared_proof", "test_script", "filename", "max_multipliers", "is_minimal_example"),
    [
        *generate_test_cases(test_num=1, is_minimal_example=False, rnd_seed=42),
        *generate_test_cases(test_num=1, is_minimal_example=True, rnd_seed=42),
    ],
)
def test_groth16_proj_slow(
    alpha_beta,
    prepared_vk,
    prepared_proof,
    test_script,
    filename,
    max_multipliers,
    extractable_inputs,
    is_minimal_example,
    save_to_json_folder,
):
    unlocking_key = Groth16ProjUnlockingKey.from_data(
        groth16_model=test_script,
        pub=prepared_proof.public_statements,
        A=prepared_proof.a,
        B=prepared_proof.b,
        C=prepared_proof.c,
        max_multipliers=max_multipliers,
        inverse_miller_output=prepared_proof.inverse_miller_loop,
    )
    unlock = unlocking_key.to_unlocking_script(test_script, True, extractable_inputs)

    locking_key = Groth16ProjLockingKey(
        alpha_beta=alpha_beta.to_list(),
        minus_gamma=prepared_vk.minus_gamma,
        minus_delta=prepared_vk.minus_delta,
        gamma_abc=prepared_vk.gamma_abc,
    )
    lock = test_script.groth16_verifier_proj(
        locking_key,
        modulo_threshold=200 * 8,
        max_multipliers=max_multipliers,
        extractable_inputs=extractable_inputs,
        check_constant=True,
        clean_constant=True,
    )
    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert context.get_stack().size() == 1
    assert context.get_altstack().size() == 0

    if is_minimal_example:
        num_public_inputs = "two public inputs" if filename == "bls12_381" else "one public input"
        message = (
            f"\nThe script size for Groth16Proj for the curve {filename} with {num_public_inputs} is:\n"
            f"Locking script: {len(lock.raw_serialize())} bytes.\n"
            f"Unlocking script: {len(unlock.raw_serialize())} bytes.\t"
        )

        sys.stdout.write(message)

    if save_to_json_folder:
        save_scripts(str(lock), str(unlock), save_to_json_folder, filename, "groth16")
