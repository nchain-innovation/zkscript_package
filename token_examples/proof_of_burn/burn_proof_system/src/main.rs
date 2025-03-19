use std::io::Cursor;

use anyhow::anyhow;
use ark_crypto_primitives::SNARK;
use ark_ff::PrimeField;
use ark_groth16::{Groth16, Proof, ProvingKey, VerifyingKey};
use ark_mnt4_753::{Fr as ScalarFieldMNT4, MNT4_753};
use ark_mnt6_753::MNT6_753;
use ark_pcd::variable_length_crh::pedersen::VariableLengthPedersenParameters;
use ark_serialize::CanonicalDeserialize;
use bitcoin_r1cs::bitcoin_predicates::data_structures::proof::BitcoinProof;
use bitcoin_r1cs::bitcoin_predicates::data_structures::unit::BitcoinUnit;
use bitcoin_r1cs::reftx::RefTxCircuit;
use bitcoin_r1cs::{
    bitcoin_predicates::data_structures::field_array::FieldArray,
    transaction_integrity_gadget::TransactionIntegrityScheme,
};
use chain_gang::script::op_codes::OP_CHECKSIG;
use chain_gang::script::Script;
use chain_gang::transaction::sighash::SigHashCache;
use chain_gang::{
    messages::Tx,
    util::{Hash256, Serializable},
};
use clap::Parser;
use cli::{Cli, Commands};
use pob::{Config, PoB};
use proving_data::ProvingData;
use rand_chacha::ChaChaRng;
use rand_chacha::rand_core::SeedableRng;
use utils::{data_to_serialisation, read_from_file, save_to_file};

mod cli;
mod pob;
mod proving_data;
mod utils;

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Setup => {
            // Load the key of the TCP
            let crh_pp_seed_bytes = read_from_file("../tcp_proof_system/data/keys/crh_pp_seed.bin")
                .map_err(|e| anyhow!("Failed to read crh_pp. Error: {}", e))
                .unwrap();
            let help_vk_bytes = read_from_file("../tcp_proof_system/data/keys/help_vk.bin")
                .map_err(|e: std::io::Error| anyhow!("Failed to read help_vk. Error: {}", e))
                .unwrap();

            let crh_pp = VariableLengthPedersenParameters {
                seed: crh_pp_seed_bytes,
            };
            let help_vk = VerifyingKey::<MNT6_753>::deserialize_unchecked(help_vk_bytes.as_slice())
                .map_err(|e| anyhow!("Failed to deserialize help_vk. Error: {}", e))
                .unwrap();

            // PoB
            let pob = PoB::new(&crh_pp, &help_vk, 0);
            // Dummy RefTx
            let dummy_reftx = RefTxCircuit::<PoB, ScalarFieldMNT4, Config> {
                locking_data: FieldArray::<1, ScalarFieldMNT4, Config>::default(),
                integrity_tag: None,
                unlocking_data: BitcoinUnit::default(),
                witness: BitcoinProof::new(&Proof::<MNT6_753>::default()),
                spending_data: None,
                prev_lock_script: None,
                prev_amount: None,
                sighash_cache: None,
                predicate: pob,
            };

            // Setup
            let mut rng = ChaChaRng::from_entropy();
            let (pk, vk) = Groth16::<MNT4_753>::circuit_specific_setup(dummy_reftx, &mut rng).unwrap();

            // Save keys
            save_to_file(&data_to_serialisation(&pk), "data/keys/pk.bin").unwrap();
            save_to_file(&data_to_serialisation(&vk), "data/keys/vk.bin").unwrap();
        },
    Commands::Prove => {
        let proving_data = ProvingData::load("data/proving_data.toml").unwrap();
        let genesis_txid = FieldArray::<1, ScalarFieldMNT4, Config>::new([
            ScalarFieldMNT4::from_le_bytes_mod_order(
                &Hash256::decode(&proving_data.genesis_txid).unwrap().0,
            ),
        ]);
        let spending_tx = Tx::read(&mut Cursor::new(
            hex::decode(proving_data.spending_tx)
                .map_err(|e| anyhow!("Failed to hex decode witness tx. Error: {}", e))
                .unwrap(),
        ))
        .map_err(|e| anyhow!("Failed to read witness tx. Error: {}", e))
        .unwrap();
        let tcp_proof = Proof::<MNT6_753>::deserialize_unchecked(Cursor::new(
            read_from_file(&format!("../tcp_proof_system/data/proofs/{}", proving_data.tcp_proof_name))
                .map_err(|e| anyhow!("Failed to read prior proof. Error: {}", e))
                .unwrap(),
        ))
        .unwrap();

        // Load the key of the TCP
        let crh_pp_seed_bytes = read_from_file("../tcp_proof_system/data/keys/crh_pp_seed.bin")
            .map_err(|e| anyhow!("Failed to read crh_pp. Error: {}", e))
            .unwrap();
        let help_vk_bytes = read_from_file("../tcp_proof_system/data/keys/help_vk.bin")
            .map_err(|e: std::io::Error| anyhow!("Failed to read help_vk. Error: {}", e))
            .unwrap();

        let crh_pp = VariableLengthPedersenParameters {
            seed: crh_pp_seed_bytes,
        };
        let help_vk = VerifyingKey::<MNT6_753>::deserialize_unchecked(help_vk_bytes.as_slice())
            .map_err(|e| anyhow!("Failed to deserialize help_vk. Error: {}", e))
            .unwrap();

        // PoB
        let pob = PoB::new(&crh_pp, &help_vk, 0);

        // Tag
        let tag = TransactionIntegrityScheme::<Config>::commit(
            &spending_tx,
            &Script(vec![OP_CHECKSIG]),
            proving_data.prev_amount,
            &mut SigHashCache::new(),
        );

        // RefTx
        let reftx = RefTxCircuit::<PoB, ScalarFieldMNT4, Config> {
            locking_data: genesis_txid,
            integrity_tag: Some(tag),
            unlocking_data: BitcoinUnit::default(),
            witness: BitcoinProof::new(&tcp_proof),
            spending_data: Some(spending_tx),
            prev_lock_script: Some(Script(vec![OP_CHECKSIG])),
            prev_amount: Some(proving_data.prev_amount),
            sighash_cache: None,
            predicate: pob,
        };

        // Load key of RefTx
        let pk_serialised = read_from_file("data/keys/pk.bin")
            .map_err(|e: std::io::Error| anyhow!("Failed to read pk. Error: {}", e))
            .unwrap();
        let pk = ProvingKey::<MNT4_753>::deserialize_unchecked(pk_serialised.as_slice())
            .map_err(|e| anyhow!("Failed to deserialize pk. Error: {}", e))
            .unwrap();

        // Save the public input
        save_to_file(
            data_to_serialisation(&reftx.public_input()).as_slice(),
            "data/proofs/input_proof_of_burn.bin",
        )
        .unwrap();

        // Proof
        let mut rng = ChaChaRng::from_entropy();
        let proof = Groth16::<MNT4_753>::prove(&pk, reftx, &mut rng).unwrap();

        // Save the proof
        save_to_file(
            &data_to_serialisation(&proof),
            "data/proofs/proof_of_burn.bin",
        )
        .unwrap();
    },
    Commands::Verify => {
        // Load vk of RefTx
        let vk_serialised = read_from_file("data/keys/vk.bin")
            .map_err(|e: std::io::Error| anyhow!("Failed to read vk. Error: {}", e))
            .unwrap();
        let vk = VerifyingKey::<MNT4_753>::deserialize_unchecked(vk_serialised.as_slice())
            .map_err(|e| anyhow!("Failed to deserialize vk. Error: {}", e))
            .unwrap();

        // Load the public input
        let public_input_serialised = read_from_file("data/proofs/input_proof_of_burn.bin")
            .map_err(|e: std::io::Error| anyhow!("Failed to read public input. Error: {}", e))
            .unwrap();
        let public_input =
            Vec::<ScalarFieldMNT4>::deserialize_unchecked(public_input_serialised.as_slice())
                .map_err(|e| anyhow!("Failed to deserialize public input. Error: {}", e))
                .unwrap();

        // Load the proof
        let proof_serialised = read_from_file("data/proofs/proof_of_burn.bin")
            .map_err(|e: std::io::Error| anyhow!("Failed to read proof. Error: {}", e))
            .unwrap();
        let proof = Proof::<MNT4_753>::deserialize_unchecked(proof_serialised.as_slice())
            .map_err(|e| anyhow!("Failed to deserialize proof. Error: {}", e))
            .unwrap();

        let is_valid = Groth16::<MNT4_753>::verify(&vk, &public_input, &proof).unwrap();

        assert!(is_valid, "\nProof not valid.\n");
        println!("\nValid proof.\n")
    }
}
}