import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from elliptic_curves.instantiations.bls12_381.bls12_381 import BLS12_381, ProofBls12381, VerifyingKeyBls12381
from elliptic_curves.instantiations.mnt4_753.mnt4_753 import MNT4_753, ProofMnt4753, VerifyingKeyMnt4753
from tx_engine import SIGHASH, Context, Script, Tx, TxIn, sig_hash

from src.zkscript.groth16.bls12_381.bls12_381 import bls12_381
from src.zkscript.groth16.mnt4_753.mnt4_753 import mnt4_753
from src.zkscript.reftx.reftx import RefTx
from src.zkscript.script_types.locking_keys.reftx import RefTxLockingKey
from src.zkscript.script_types.unlocking_keys.reftx import RefTxUnlockingKey


@dataclass
class Bls12381:
    q = BLS12_381.g1_field.get_modulus()
    r = BLS12_381.scalar_field.get_modulus()
    g1 = BLS12_381.g1_curve.get_generator()
    g2 = BLS12_381.g2_curve.get_generator()

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
    sighash_chunks = [int.from_bytes(sighash[:16], "little"), int.from_bytes(sighash[16:], "little")]

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
    test_script_groth16 = bls12_381
    filename = "bls12_381"


@dataclass
class Mnt4753:
    q = MNT4_753.g1_field.get_modulus()
    r = MNT4_753.scalar_field.get_modulus()
    g1 = MNT4_753.g1_curve.get_generator()
    g2 = MNT4_753.g2_curve.get_generator()

    # Dummy ZKP
    # Generated with secrets.randbelow(r - 1) + 1
    A_ = 272305577651305140310613172595275386027013762501515343240163048609172798634049496371843021865521238841887045228163650643110817033530270550299236673836051955932768871545452966675935515618087467349206495382988333243675305900735889  # noqa: E501
    B_ = 6664763770039059624002862451609814855662026887034867315010661435472719714436725569762120215305183498289614898316267298097495043513270051808193724682245605523964340130133012929695832010624101073207251800330941946058672621528219  # noqa: E501
    C_ = 34475479520051462809021836218570023707977336307271451900811262599017749625416055235212106260402491805840511744803235981600861597860458448581015210793993720576620535502434685142083395160466021775582688337776757571884439148524627  # noqa: E501

    A = g1.multiply(A_)
    B = g2.multiply(B_)
    C = g1.multiply(C_)

    proof = ProofMnt4753(
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
    sighash_chunks = [int.from_bytes(sighash, "little")]

    # Dummy parameters public inputs
    n_pub_l_out = 2
    n_pub_u_stx = 3
    n_sighash_chunks = len(sighash_chunks)
    n_pub_ext = n_pub_l_out + n_pub_u_stx + n_sighash_chunks + 1

    # Public inputs
    pub_l_out = [
        [
            10479130678929174340480965839371746802266349422606251674499224077246714272469497230720022909880803184230508325875083413364758856372991671186934444023000124007921659075530340348529573717103170440312360592464647112695034869790330,
            2523326787196103877774067557682858771787093798581501227978670724720562549215733646166036121970877584593853864886924446758522425774307093264374879666327737103810668453526997577096498928183310421324486944817548197686251079679886,
        ],
        [
            21529089920616395803311708573807357838686736256080866696553479821368450674667153935156652015132177556664051581347387492268304968680655241491941937789581237620512801178759977166679725097809953280635607678146567925996152654250294,
            35932276401859015847587664493391544656877129722490781328027863426650004504525051200546095915779076932858559770838939901754712886081618364084191921426031247774352166560935824999641565937640105140666546013338463616730452662715604,
        ],
    ]

    pub_u_stx = [
        [
            19411797746147162890178311672934806307038520749902377075690824651344627644939765749414031668752780834237689913920070620911849855341472776620576693664525402690784966294236484101544747715108787179889217449762788214260585700697997,
            7205513351291023444207182227454141975533423119934761180797699851605660614140038051729219185952624308204072622927283265681886447332106342560442830121601463692967508394528998097076237545733787786998957905294036257005780641595845,
            27165536997620193109809017066736868176082798763718943469563936907977189054316360792000334632244000668782557379300130974463459140568317150586786204290430705455394996330686519974420422792301698057840218965838958999965329375103050,
        ],
        [
            35311037456815258110689632100256686311634276251379744176279050918478062364406403967461878478591022488206963847791629336121088644517372464171240538234763506768151345332461587039289064056536315612869032725448985349167767853692285,
            27389790048838316928330212635418771667384236281164735103334637706042396970833317253972599188501001694900408577101764157404086302153309942372931053994040782967374557760202382870323943355885204155750095441808519073097697759745438,
            3673545907406689589124134101055539330482797564740244221502909212217207526642382233664149714453481905620127907929726406645899475341803956521779798595490465308298941035830029425594595970112053216803148028186656789113464011220149,
        ],
    ]

    # Max multipliers
    max_multipliers = [None, None]

    # Dummy vk
    dlog_gamma_abc = [
        36654759581720979066753228177756132582048441273150435065311701304547526797888068388449009875584996936708461141070000855742230129483596530543037722228751782019253291533230419522161818602321458421152109780608132647842780137101940,
        34336177661212225974935828479040018581890571365233539788165086145114413564049074887908448295839348258359268007407843212308293464661488017941732857131353777422288851233486694325763625152825192177040893425685459876907081513299673,
        31618232523048853263256575408831597932944458583751401724455330577020603730206403962560623065131972634339325597626191026858587943141725540509441370262582825250103089570215149632013074590196825805846109465265339838069875089026790,
        15751252375259337013347039534961397410357289228830225608443093351513972703850889945593972210236369345449799744455868058048822916862113699043313408932171046792094156201805008883251700343152776099267474845285048468943150944073301,
        1279996905712738111786357667702395616408783111952645842497481984150066386568051574689204767410985084950371631836767033931667232685644668694322096865610536308101205302473499847245199398614393185735881007663344558049229306985870,
        27176636021795652984469727222213055358164075448677452571551608860697293549127215321931510943073261975620314630404073546196752030867981938141178788040336412150502309231654067138606852582299491847999257831163957431664464514084498,
        39256990243150212173073078006257375987162058601548029073750982837141987396011946632047440357084174411956228552525560121310180165875600306863300314398738503621075582369950748292689032997283419331513425341010774700676792966293575,
    ]
    gamma_abc = []
    for i in range(n_pub_ext):
        gamma_abc.append(g1.multiply(dlog_gamma_abc[i]))

    alpha_ = 22154869533288628032721592269568212536377714523972897061261032764278717330596912427164979799913022981149516620617636484790209933126169020031408935410981046183197631786088916013962462940821330335402036718396030757277938164632199  # noqa: E501
    beta_ = 38604478190405061258070758546490352351434935333899487304839255552442197706055977599324321085133116465415039413786074769516241533238209785418099313683296100514950400560317216245965768719128128192617036858397924816777241698190668  # noqa: E501
    gamma_ = 2163091689249734606904268556840612952311491848266082384147356885891111474140198575626968315366263283138867705965285352179395825560264004443829507010147397352150979474497178856733164947842330777316406085098855809935436561980160  # noqa: E501
    delta_ = 16333323520394361455666596339208826734990659893162012922470524699855041863240775568156373395014762328540569235786629261541983517366627802833042654749789787889756837105283041270521942365069953608097338735907185828578038700042531  # noqa: E501

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
            MNT4_753.pairing([A, sum_gamma_abc[j], C], [B, -gamma, -delta]),
        )

        for i, scalar in enumerate(pub_l_out[j]):
            precomputed_l_out[j] += gamma_abc[i + 1].multiply(scalar)

        gamma_abc_mod.append([precomputed_l_out[j], *gamma_abc[n_pub_l_out + 1 :]])

        pub_mod.append(pub_extended[j][n_pub_l_out + 1 :])

        vk.append(VerifyingKeyMnt4753(alpha, beta, gamma, delta, gamma_abc_mod[j]))

        cache_vk.append(vk[j].prepare())
        prepared_vk.append(vk[j].prepare_for_zkscript(cache_vk[j]))
        prepared_proofs.append(
            proof.prepare_for_zkscript(cache_vk[j], pub_mod[j]),
        )

    test_script = RefTx(mnt4_753)
    test_script_groth16 = mnt4_753
    filename = "mnt4_753"


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
        (
            Mnt4753,
            Mnt4753.prepared_vk[0],
            Mnt4753.alpha_beta[0],
            Mnt4753.prepared_proofs[0],
            Mnt4753.max_multipliers[0],
        ),
        (
            Mnt4753,
            Mnt4753.prepared_vk[1],
            Mnt4753.alpha_beta[1],
            Mnt4753.prepared_proofs[1],
            Mnt4753.max_multipliers[1],
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
        groth16_model=config.test_script_groth16,
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

    unlock = unlock_key.to_unlocking_script(config.test_script_groth16)

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
