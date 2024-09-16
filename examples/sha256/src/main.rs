use std::{fs::File, io::{BufReader, Write}};

use ark_ff::PrimeField;
use ark_groth16::Groth16;
use ark_r1cs_std::{alloc::AllocVar, fields::fp::FpVar, uint8::UInt8, ToBytesGadget, eq::EqGadget};
use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystemRef};
use ark_serialize::{CanonicalSerialize, Compress};
use ark_snark::SNARK;
use ark_test_curves::bls12_381::{Bls12_381, Fr};
use rand_chacha::ChaChaRng;
use rand::SeedableRng;
use serde_json::{json, Value};
use ark_crypto_primitives::crh::{sha256::{constraints::{DigestVar, Sha256Gadget}, Sha256},CRHScheme};


#[derive(Clone)]
pub struct Sha256Preimage<F: PrimeField> {
    pub preimage: Vec<u8>,
    pub hash: Vec<F>
}

impl<F: PrimeField> ConstraintSynthesizer<F> for Sha256Preimage<F> {
    fn generate_constraints(self, cs: ConstraintSystemRef<F>) -> ark_relations::r1cs::Result<()> {
        assert_eq!(self.hash.len(),2);

        // Allocate the witness
        let preimage_var =  UInt8::<F>::new_witness_vec(cs.clone(), &self.preimage)?;
        // Allocate public inputs
        let mut public_inputs: Vec<FpVar::<F>> = Vec::new();
        for element in self.hash.iter() {
            public_inputs.push(FpVar::<F>::new_input(cs.clone(), || Ok(element))?);
        };

        // Compute SHA256 hash of witness
        let computed_hash = Sha256Gadget::<F>::digest(&preimage_var)?;
        // Reconstruct expected hash from public inputs
        let expected_hash = DigestVar::<F>(vec_hash_to_hash(&public_inputs)?);
        
       computed_hash.enforce_equal(&expected_hash)
    }
}


fn main() -> Result<(), Box<dyn std::error::Error>>{
    // Randomness
    let mut rng = ChaChaRng::from_entropy();

    // Fetch the parameters: 0 - root, 1 - square
    let preimage = read_parameter("parameters.json");

    // Build the circuit
    let circuit = Sha256Preimage::<Fr> {
        preimage: preimage.as_bytes().to_vec(),
        hash: input_to_vec_hash(&preimage),
    };

    // Setup
    let (pk, vk) = Groth16::<Bls12_381>::circuit_specific_setup(circuit.clone(), &mut rng)
        .map_err(|e| format!("Setup failed: {}",e))?;

    // Proving
    let proof = Groth16::<Bls12_381>::prove(&pk, circuit.clone(), &mut rng)
        .map_err(|e| format!("Proof generation failed: {}", e))?;

    // Verifying
    let is_valid = Groth16::<Bls12_381>::verify(&vk, &input_to_vec_hash(&preimage), &proof)
        .map_err(|e| format!("Verification failed: {}", e))?;
    assert!(is_valid,"Proof is invalid");

    // Save proof, verification key, and public input to files
    save_to_file(&proof,"proof/proof.json","proof")?;
    save_to_file(&vk, "proof/verifying_key.json","verifying_key")?;
    save_to_file(&input_to_vec_hash(&preimage), "proof/public_inputs.json","public_inputs")?;

    Ok(())
}

// Function to read parameters from JSON file
fn read_parameter(path: &str) -> String {
    let file = File::open(path).unwrap();
    let reader = BufReader::new(file);
    let json_data: Value = serde_json::from_reader(reader).unwrap();
    let preimage = json_data.get("preimage").cloned().unwrap();
    String::from(preimage.as_str().unwrap())
}

// Takes input value, computes its hash and encodes it in two elements of Fr
fn input_to_vec_hash(input: &str) -> Vec<Fr> {
    let input_bytes = input.as_bytes();
    let hashed_input = Sha256::evaluate(&(), input_bytes).unwrap();

    let mut output: Vec<Fr> = Vec::new();
    output.push(Fr::from_le_bytes_mod_order(&hashed_input[..31]));
    output.push(Fr::from_le_bytes_mod_order(&hashed_input[31..]));
    output

}

// Take a Vec<Fr> representation of the hash and reconstructs the hash
fn vec_hash_to_hash<F: PrimeField>(vec_hash: &Vec<FpVar<F>>) -> ark_relations::r1cs::Result<Vec<UInt8<F>>> {
    let mut expected_hash_bytes: Vec<UInt8<F>> = Vec::new();
    for element in vec_hash.iter() {
        // Only use the first 31 bytes
        let relevant_part = element.to_bytes()?[..31].to_vec();
        expected_hash_bytes.extend(relevant_part);
    };
    Ok(expected_hash_bytes[..32].to_vec())
}

// Generic function to save serializable data
fn save_to_file<T>(
    item: &T,
    file_path: &str,
    key_name: &str
) -> Result<(), Box<dyn std::error::Error>>
where
    T: CanonicalSerialize,
{
    let mut serialized_data = vec![0; item.serialized_size(Compress::No)];
    item.serialize_uncompressed(&mut serialized_data[..])?;
    
    let json_data = json!({key_name: serialized_data});
    let json_string = serde_json::to_string_pretty(&json_data)?;
    
    File::create(file_path)?.write_all(json_string.as_bytes())?;
    Ok(())
}