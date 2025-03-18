use clap::Parser;
use cli::Cli;

pub mod cli;
pub mod data_structures;
pub mod nft;
pub mod util;

use data_structures::{
    proving_data::ProvingData, setup_data::SetupData, verifying_data::VerifyingData,
};
use nft::{NFT, groth16_nft::UniversalTCPSnark};

fn main() {
    let cli = Cli::parse();

    if cli.setup {
        let setup_data = SetupData::load(cli.file).unwrap();
        <UniversalTCPSnark as NFT>::setup(setup_data).unwrap();
    } else if cli.process {
        let proving_data = ProvingData::load(cli.file).unwrap();
        <UniversalTCPSnark as NFT>::process_input(proving_data).unwrap();
    } else if cli.prove {
        let proving_data = ProvingData::load(cli.file).unwrap();
        <UniversalTCPSnark as NFT>::prove(proving_data).unwrap();
    } else if cli.verify {
        let verifying_data = VerifyingData::load(cli.file).unwrap();
        assert!(
            <UniversalTCPSnark as NFT>::verify(verifying_data).unwrap(),
            "\nProof not valid.\n"
        );
        println!("\nValid proof.\n")
    }
}
