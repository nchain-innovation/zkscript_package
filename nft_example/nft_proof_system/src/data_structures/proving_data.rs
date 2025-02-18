use anyhow::{Result, anyhow};
use std::fs;

use chain_gang::{messages::OutPoint, util::Hash256};
use serde::Deserialize;
use transaction_chain_proof::snarks::universal_tcp_snark::UniversalTransactionChainProofPublicInput;

/// Data required to generate a Transaction Chain Proof
#[derive(Clone, Deserialize)]
pub struct ProvingData {
    pub chain_parameters: ChainParameters,
    pub public_inputs: PublicInputs,
    pub witness: Witness,
    pub proof_name: String,
}

/// Parameters of the Transaction Chain
#[derive(Clone, Deserialize)]
pub struct ChainParameters {
    pub chain_index: u32,
}

/// Public inputs of the proof
#[derive(Clone, Deserialize)]
pub struct PublicInputs {
    pub outpoint_txid: String,
    pub genesis_txid: String,
}

/// Witness of the proof
#[derive(Clone, Deserialize)]
pub struct Witness {
    pub tx: String,
    pub prior_proof_path: String,
}

impl ProvingData {
    pub fn load(file_path: String) -> Result<Self> {
        let file_data = fs::read_to_string(file_path)
            .map_err(|e| anyhow!("Failed to read proving data. Error: {}", e))?;
        toml::from_str::<ProvingData>(&file_data)
            .map_err(|e| anyhow!("Failed to parse proving data. Error {}", e))
    }
}

impl From<ProvingData> for UniversalTransactionChainProofPublicInput {
    fn from(value: ProvingData) -> Self {
        Self {
            outpoint: OutPoint {
                hash: Hash256::decode(&value.public_inputs.outpoint_txid).unwrap(),
                index: value.chain_parameters.chain_index,
            },
            genesis_txid: Hash256::decode(&value.public_inputs.genesis_txid)
                .unwrap()
                .0,
        }
    }
}
