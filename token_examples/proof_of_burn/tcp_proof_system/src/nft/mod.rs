use anyhow::Result;
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};

use crate::data_structures::proving_data::ProvingData;
use crate::data_structures::setup_data::SetupData;
use crate::data_structures::verifying_data::VerifyingData;

pub mod groth16_nft;

/// Interface for NFT application of PCD
pub trait NFT {
    type ProvingKeyMainCircuit: Clone + CanonicalSerialize + CanonicalDeserialize;
    type ProvingKeyHelpCircuit: Clone + CanonicalSerialize + CanonicalDeserialize;
    type ProvingKey: Clone;
    type VerifyingKeyMainCircuit: Clone + CanonicalSerialize + CanonicalDeserialize;
    type VerifyingKeyHelpCircuit: Clone + CanonicalSerialize + CanonicalDeserialize;
    type VerifyingKey;
    type Proof: Clone + CanonicalSerialize + CanonicalDeserialize;
    const KEYS_PATH: &str;
    const PROOFS_PATH: &str;

    // Perform the setup of the NFT and save the keys to file
    fn setup(setup_data: SetupData) -> Result<()>;

    // Process the public input contained in `ProvingData` and save it to file
    fn process_input(proving_data: ProvingData) -> Result<()>;

    // Prove that an NFT is held in the output of a given tx and save the proof to file
    fn prove(proving_data: ProvingData) -> Result<()>;

    // Verify that an NFT is held in the output of a given tx
    fn verify(verifying_data: VerifyingData) -> Result<bool>;

    // Load the proving key of the NFT scheme
    fn load_pk() -> Result<Self::ProvingKey>;

    // Load the verifying key of the NFT scheme
    fn load_vk() -> Result<Self::VerifyingKey>;
}
