use std::fs;

use anyhow::{Result, anyhow};
use chain_gang::{messages::OutPoint, util::Hash256};
use serde::Deserialize;
use transaction_chain_proof::snarks::universal_tcp_snark::UniversalTransactionChainProofPublicInput;

/// Data required to verify a Transaction Chain Proof
#[derive(Deserialize)]
pub struct VerifyingData {
    pub chain_parameters: ChainParameters,
    pub public_inputs: PublicInputs,
    pub proof_path: String,
}

/// Parameters of the Transaction Chain
#[derive(Clone, Deserialize)]
pub struct ChainParameters {
    pub chain_index: u32,
}

/// Public inputs
#[derive(Deserialize)]
pub struct PublicInputs {
    pub outpoint_txid: String,
    pub genesis_txid: String,
}

impl VerifyingData {
    pub fn load(file_path: String) -> Result<Self> {
        let file_data = fs::read_to_string(file_path)
            .map_err(|e| anyhow!("Failed to read verifying data. Error: {}", e))?;
        toml::from_str::<VerifyingData>(&file_data)
            .map_err(|e| anyhow!("Failed to parse verifying data. Error: {}", e))
    }
}

impl From<VerifyingData> for UniversalTransactionChainProofPublicInput {
    fn from(value: VerifyingData) -> Self {
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
