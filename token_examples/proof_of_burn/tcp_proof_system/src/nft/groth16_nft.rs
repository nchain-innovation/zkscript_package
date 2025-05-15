use anyhow::{Result, anyhow};
use std::io::Cursor;

use ark_mnt4_753::{
    Fq as ScalarFieldMNT6, Fr as ScalarFieldMNT4,
};
use ark_mnt6_753::g1::Parameters as ShortWeierstrassParameters;
use ark_pcd::ec_cycle_pcd::{ECCyclePCD, ECCyclePCDConfig};
use ark_pcd::variable_length_crh::injective_map::VariableLengthPedersenCRHCompressor;
use ark_pcd::variable_length_crh::injective_map::constraints::VariableLengthPedersenCRHCompressorGadget;
use ark_pcd::variable_length_crh::pedersen::VariableLengthPedersenParameters;

use ark_groth16::{
    Groth16, PreparedVerifyingKey, ProvingKey, VerifyingKey, constraints::Groth16VerifierGadget,
};
use ark_mnt4_753::{MNT4_753, constraints::PairingVar as MNT4PairingVar};
use ark_mnt6_753::{MNT6_753, constraints::PairingVar as MNT6PairingVar};

use ark_serialize::CanonicalDeserialize;
use bitcoin_r1cs::constraints::tx::TxVarConfig;
use chain_gang::messages::Tx;
use chain_gang::util::Serializable;
use rand_chacha::ChaChaRng;

use transaction_chain_proof::predicates::universal_tcp::UniversalTransactionChainProofPredicate;
use transaction_chain_proof::snarks::universal_tcp_snark::{
    UniversalTransactionChainProofData, UniversalTransactionChainProofPublicInput,
    UniversalTransactionChainProofSNARK, UniversalTransactionChainProofWitness,
};

use crate::data_structures::proving_data::ProvingData;
use crate::data_structures::setup_data::SetupData;
use crate::data_structures::verifying_data::VerifyingData;

use crate::nft::NFT;
use crate::util::{data_to_serialisation, read_from_file, save_to_file};

/// PCD with Groth16 as MainSNARK and HelpSNARK
/// Over the MNT4_753 - MNT6_753 cycle, with MNT6_753 as the HelpSNARK curve
pub struct PCDGroth16Mnt4;
impl ECCyclePCDConfig<ScalarFieldMNT4, ScalarFieldMNT6> for PCDGroth16Mnt4 {
    type CRH = VariableLengthPedersenCRHCompressor<ChaChaRng, ShortWeierstrassParameters>;
    type CRHGadget =
        VariableLengthPedersenCRHCompressorGadget<ChaChaRng, ShortWeierstrassParameters>;
    type MainSNARK = Groth16<MNT4_753>;
    type HelpSNARK = Groth16<MNT6_753>;
    type MainSNARKGadget = Groth16VerifierGadget<MNT4_753, MNT4PairingVar>;
    type HelpSNARKGadget = Groth16VerifierGadget<MNT6_753, MNT6PairingVar>;
}
type PCD = ECCyclePCD<ScalarFieldMNT4, ScalarFieldMNT6, PCDGroth16Mnt4>;

/// Structure of the transactions in the chain
/// Inputs are P2PK
/// Unlocking scripts are <Sig> w/ r.len = 33, s.len = 32
/// Outputs are P2PK
#[derive(Clone)]
pub(crate) struct Config;
impl TxVarConfig for Config {
    const N_INPUTS: usize = 1;
    const N_OUTPUTS: usize = 1;
    const LEN_UNLOCK_SCRIPTS: &[usize] = &[0x6b];
    const LEN_LOCK_SCRIPTS: &[usize] = &[0x19];
    const LEN_PREV_LOCK_SCRIPT: Option<usize> = None;
    const PRE_SIGHASH_N_INPUT: Option<usize> = None;
}

pub(crate) type UniversalTCPSnark =
    UniversalTransactionChainProofSNARK<ScalarFieldMNT4, Config, PCD, ChaChaRng>;

impl NFT for UniversalTCPSnark {
    type ProvingKeyMainCircuit = ProvingKey<MNT4_753>;
    type ProvingKeyHelpCircuit = ProvingKey<MNT6_753>;
    type ProvingKey = <UniversalTCPSnark as UniversalTransactionChainProofData>::ProvingKey;
    type VerifyingKeyMainCircuit = VerifyingKey<MNT4_753>;
    type VerifyingKeyHelpCircuit = VerifyingKey<MNT6_753>;
    type VerifyingKey = <UniversalTCPSnark as UniversalTransactionChainProofData>::VerifyingKey;
    type Proof = <UniversalTCPSnark as UniversalTransactionChainProofData>::Proof;
    const KEYS_PATH: &str = "data/keys/";
    const PROOFS_PATH: &str = "data/proofs/";

    /// Perform the setup based on the provided `chain_index`
    fn setup(setup_data: SetupData) -> Result<()> {
        let (pk, _vk) = Self::setup(&setup_data.chain_index).unwrap();
        save_to_file(
            &pk.crh_pp.seed,
            &(Self::KEYS_PATH.to_owned() + "crh_pp_seed.bin"),
        )
        .map_err(|e| anyhow!("Failed to save crh_pp. Error: {}", e))?;
        save_to_file(
            &data_to_serialisation(&pk.main_pk),
            &(Self::KEYS_PATH.to_owned() + "main_pk.bin"),
        )
        .map_err(|e| anyhow!("Failed to save main_pk. Error: {}", e))?;
        save_to_file(
            &data_to_serialisation(&pk.help_pk),
            &(Self::KEYS_PATH.to_owned() + "help_pk.bin"),
        )
        .map_err(|e| anyhow!("Failed to save help_pk. Error: {}", e))?;
        save_to_file(
            &data_to_serialisation(&pk.help_vk),
            &(Self::KEYS_PATH.to_owned() + "help_vk.bin"),
        )
        .map_err(|e| anyhow!("Failed to save help_vk. Error: {}", e))?;
        save_to_file(
            &data_to_serialisation(&pk.main_pvk.vk),
            &(Self::KEYS_PATH.to_owned() + "main_vk.bin"),
        )
        .map_err(|e| anyhow!("Failed to save main_vk. Error: {}", e))?;

        Ok(())
    }

    /// Process the input contained in `ProvingData` (i.e., compute the Pedersen hash)
    fn process_input(proving_data: ProvingData) -> Result<()> {
        // Generate processed input
        let vk = Self::load_vk().map_err(|e| anyhow!("Failed to load vk. Error: {}", e))?;
        let public_input: UniversalTransactionChainProofPublicInput = proving_data.clone().into();
        let processed_input = PCD::msg_to_input_hash::<
            UniversalTransactionChainProofPredicate<Config>,
        >(&vk, &public_input.into())
        .map_err(|e| anyhow!("Failed to process the public input. Error: {}", e))?;

        // Save processed input to file
        let processed_input_path =
            Self::PROOFS_PATH.to_owned() + &proving_data.proof_name + "_processed_input.bin";
        save_to_file(
            &data_to_serialisation(&processed_input),
            &processed_input_path,
        )
        .map_err(|e| anyhow!("Failed to save the processed public input. Error: {}", e))?;

        Ok(())
    }

    /// Generate a proof for the provided `ProvingData`
    fn prove(proving_data: ProvingData) -> Result<()> {
        let pk = Self::load_pk().map_err(|e| anyhow!("Failed to load pk. Error: {}", e))?;

        // Proving data
        let chain_index = proving_data.chain_parameters.chain_index;
        let tx = match proving_data.witness.tx.is_empty() {
            true => None,
            false => Some(
                Tx::read(&mut Cursor::new(
                    hex::decode(proving_data.witness.tx.clone())
                        .map_err(|e| anyhow!("Failed to hex decode witness tx. Error: {}", e))?,
                ))
                .map_err(|e| anyhow!("Failed to read witness tx. Error: {}", e))?,
            ),
        };
        let prior_proof = match proving_data.witness.prior_proof_path.is_empty() {
            true => None,
            false => {
                let prior_proof_path =
                    Self::PROOFS_PATH.to_owned() + &proving_data.witness.prior_proof_path + ".bin";
                Self::Proof::deserialize_unchecked(Cursor::new(
                    read_from_file(&prior_proof_path)
                        .map_err(|e| anyhow!("Failed to read prior proof. Error: {}", e))?,
                ))
                .ok()
            }
        };

        // Proof generation
        let public_input: UniversalTransactionChainProofPublicInput = proving_data.clone().into();
        let witness = UniversalTransactionChainProofWitness::<Self::Proof> { tx, prior_proof };
        let proof = Self::prove(&chain_index, &pk, &public_input, &witness).unwrap();

        // Save proof to file
        let proof_path = Self::PROOFS_PATH.to_owned() + &proving_data.proof_name + ".bin";
        save_to_file(&data_to_serialisation(&proof), &proof_path)
            .map_err(|e| anyhow!("Failed to save proof. Error: {}", e))?;

        Ok(())
    }

    /// Verify the proof contained in `VerifyingData`
    fn verify(verifying_data: VerifyingData) -> Result<bool> {
        let vk = Self::load_vk().map_err(|e| anyhow!("Failed to load vk. Error: {}", e))?;
        let proof_path = Self::PROOFS_PATH.to_owned() + &verifying_data.proof_path + ".bin";
        let proof =
            Self::Proof::deserialize_unchecked(Cursor::new(read_from_file(&proof_path).unwrap()))
                .map_err(|e| anyhow!("Failed to deserialize proof. Error: {}", e))?;
        let public_input: UniversalTransactionChainProofPublicInput = verifying_data.into();
        Self::verify(&vk, &public_input, &proof)
            .map_err(|e| anyhow!("Failed to verify the proof. Error: {:?}", e))
    }

    /// Load the proving key
    fn load_pk() -> Result<Self::ProvingKey> {
        let crh_pp_seed_bytes = read_from_file(&(Self::KEYS_PATH.to_owned() + "/crh_pp_seed.bin"))
            .map_err(|e| anyhow!("Failed to read crh_pp. Error: {}", e))?;
        let main_pk_bytes = read_from_file(&(Self::KEYS_PATH.to_owned() + "/main_pk.bin"))
            .map_err(|e| anyhow!("Failed to read main_pk. Error: {}", e))?;
        let help_pk_bytes = read_from_file(&(Self::KEYS_PATH.to_owned() + "/help_pk.bin"))
            .map_err(|e| anyhow!("Failed to read help_pk. Error: {}", e))?;

        let crh_pp = VariableLengthPedersenParameters {
            seed: crh_pp_seed_bytes,
        };
        let main_pk = Self::ProvingKeyMainCircuit::deserialize_unchecked(main_pk_bytes.as_slice())
            .map_err(|e| anyhow!("Failed to deserialize main_pk. Error: {}", e))?;
        let help_pk = Self::ProvingKeyHelpCircuit::deserialize_unchecked(help_pk_bytes.as_slice())
            .map_err(|e| anyhow!("Failed to deserialize help_pk. Error: {}", e))?;
        let help_vk = help_pk.vk.clone();
        let main_pvk: PreparedVerifyingKey<MNT4_753> = main_pk.vk.clone().into();
        Ok(Self::ProvingKey {
            crh_pp,
            main_pk,
            main_pvk,
            help_pk,
            help_vk,
        })
    }

    /// Load the verifying key
    fn load_vk() -> Result<Self::VerifyingKey> {
        let crh_pp_seed_bytes = read_from_file(&(Self::KEYS_PATH.to_owned() + "/crh_pp_seed.bin"))
            .map_err(|e| anyhow!("Failed to read crh_pp. Error: {}", e))?;
        let help_vk_bytes = read_from_file(&(Self::KEYS_PATH.to_owned() + "/help_vk.bin"))
            .map_err(|e: std::io::Error| anyhow!("Failed to read help_vk. Error: {}", e))?;

        let crh_pp = VariableLengthPedersenParameters {
            seed: crh_pp_seed_bytes,
        };
        let help_vk =
            Self::VerifyingKeyHelpCircuit::deserialize_unchecked(help_vk_bytes.as_slice())
                .map_err(|e| anyhow!("Failed to deserialize help_vk. Error: {}", e))?;

        Ok(Self::VerifyingKey { crh_pp, help_vk })
    }
}
