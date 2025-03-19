use ark_groth16::{Groth16, constraints::Groth16VerifierGadget};
use ark_mnt4_753::{Fr as ScalarFieldMNT4, MNT4_753, constraints::PairingVar as MNT4PairingVar};
use ark_mnt6_753::{
    Fr as ScalarFieldMNT6, MNT6_753, constraints::PairingVar as MNT6PairingVar,
    g1::Parameters as ShortWeierstrassParameters,
};
use ark_pcd::{
    ec_cycle_pcd::ECCyclePCDConfig,
    variable_length_crh::injective_map::{
        VariableLengthPedersenCRHCompressor, constraints::VariableLengthPedersenCRHCompressorGadget,
    },
};
use bitcoin_r1cs::{
    bitcoin_predicates::proof_of_burn::ProofOfBurn, constraints::tx::TxVarConfig,
    transaction_integrity_gadget::TransactionIntegrityConfig,
};
use chain_gang::transaction::sighash::{SIGHASH_ALL, SIGHASH_FORKID};
use rand_chacha::ChaChaRng;

pub struct PCDGroth16;
impl ECCyclePCDConfig<ScalarFieldMNT4, ScalarFieldMNT6> for PCDGroth16 {
    type CRH = VariableLengthPedersenCRHCompressor<ChaChaRng, ShortWeierstrassParameters>;
    type CRHGadget =
        VariableLengthPedersenCRHCompressorGadget<ChaChaRng, ShortWeierstrassParameters>;
    type MainSNARK = Groth16<MNT4_753>;
    type HelpSNARK = Groth16<MNT6_753>;
    type MainSNARKGadget = Groth16VerifierGadget<MNT4_753, MNT4PairingVar>;
    type HelpSNARKGadget = Groth16VerifierGadget<MNT6_753, MNT6PairingVar>;
}

#[derive(Clone)]
pub struct Config;

impl TxVarConfig for Config {
    const N_INPUTS: usize = 3; // Token to be burnt,  RefTx input, funds
    const N_OUTPUTS: usize = 2; // Burnt token, change
    const LEN_UNLOCK_SCRIPTS: &[usize] = &[0, 0, 0];
    const LEN_LOCK_SCRIPTS: &[usize] = &[0x02, 0x19]; // OP_0 OP_RETURN, P2PKH
}

impl TransactionIntegrityConfig for Config {
    const LEN_PREV_LOCK_SCRIPT: usize = 1; // OP_CHECKSIG
    const N_INPUT: usize = 1; // Reftx input is the second one
    const SIGHASH_FLAG: u8 = SIGHASH_ALL | SIGHASH_FORKID;
}

pub type PoB = ProofOfBurn<ScalarFieldMNT4, ScalarFieldMNT6, PCDGroth16, Config>;
