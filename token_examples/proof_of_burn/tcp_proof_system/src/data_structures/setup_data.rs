use std::fs;

use anyhow::{Result, anyhow};
use serde::Deserialize;

/// Data required to setup a Ttransaction Chain Proof circuit
#[derive(Clone, Deserialize)]
pub struct SetupData {
    pub chain_index: u32,
}

impl SetupData {
    pub fn load(file_path: String) -> Result<Self> {
        let file_data = fs::read_to_string(file_path)
            .map_err(|e| anyhow!("Failed to read setup data. Error: {}", e))?;
        toml::from_str::<SetupData>(&file_data)
            .map_err(|e| anyhow!("Failed to parse setup data. Error: {}", e))
    }
}
