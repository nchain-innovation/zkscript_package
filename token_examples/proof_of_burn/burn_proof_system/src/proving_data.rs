use anyhow::{Result, anyhow};
use std::fs;

use serde::Deserialize;

/// Data required to generate a Transaction Chain Proof
#[derive(Clone, Deserialize)]
pub struct ProvingData {
    pub genesis_txid: String,
    pub spending_tx: String,
    pub tcp_proof_name: String,
    pub prev_amount: u64,
}

impl ProvingData {
    pub fn load(file_path: &str) -> Result<Self> {
        let file_data = fs::read_to_string(file_path)
            .map_err(|e| anyhow!("Failed to read proving data. Error: {}", e))?;
        toml::from_str::<ProvingData>(&file_data)
            .map_err(|e| anyhow!("Failed to parse proving data. Error {}", e))
    }
}
