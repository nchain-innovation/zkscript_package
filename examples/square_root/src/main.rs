use std::{fs::File, io::{BufReader, Write}};

use ark_ff::PrimeField;
use ark_groth16::Groth16;
use ark_r1cs_std::{alloc::AllocVar, fields::{fp::FpVar, FieldVar}};
use ark_relations::r1cs::ConstraintSynthesizer;
use ark_serialize::{CanonicalSerialize, Compress};
use ark_snark::SNARK;
use rand_chacha::ChaChaRng;
use rand::SeedableRng;
use serde_json::{json, Value};
#[allow(unused_imports)]
use ark_test_curves::bls12_381::{Bls12_381, Fr as ScalarFieldBls};
#[allow(unused_imports)]
use ark_mnt4_753::{MNT4_753, Fr as ScalarFieldMnt};

#[derive(Clone)]
pub struct KnowledgeOfSquareRoot<F: PrimeField> {
    root: F,    // private input
    square: F   // public input
}

impl<F: PrimeField> ConstraintSynthesizer<F> for KnowledgeOfSquareRoot<F> {
    fn generate_constraints(self, cs: ark_relations::r1cs::ConstraintSystemRef<F>) -> ark_relations::r1cs::Result<()> {
        // Allocate public input
        let public_input: FpVar<F> = FpVar::<F>::new_input(cs.clone(), || Ok(self.square))?;
        // Allocate private input
        let private_input: FpVar<F> = FpVar::<F>::new_witness(cs.clone(), || Ok(self.root))?;

        // Enfore equality
        private_input.mul_equals(&private_input, &public_input)
    }
}

type ScalarField = ScalarFieldMnt;
type Curve = MNT4_753;

fn main() -> Result<(), Box<dyn std::error::Error>>{
    // Randomness
    let mut rng = ChaChaRng::from_entropy();

    // Fetch the parameters: 0 - root, 1 - square
    let parameters = read_parameters("parameters.json")?;

    // Build the circuit
    let circuit = KnowledgeOfSquareRoot::<ScalarField> {
        root: parameters[0],
        square: parameters[1],
    };

    // Setup
    let (pk, vk) = Groth16::<Curve>::circuit_specific_setup(circuit.clone(), &mut rng)
        .map_err(|e| format!("Setup failed: {}",e))?;

    // Proving
    let proof = Groth16::<Curve>::prove(&pk, circuit.clone(), &mut rng)
        .map_err(|e| format!("Proof generation failed: {}", e))?;

    // Verifying
    let is_valid = Groth16::<Curve>::verify(&vk, &[circuit.square], &proof)
        .map_err(|e| format!("Verificaiton failed: {}", e))?;
    assert!(is_valid,"Proof is invalid");

    // Save proof, verification key, and public input to files
    save_to_file(&proof,"proof/proof.json","proof")?;
    save_to_file(&vk, "proof/verifying_key.json","verifying_key")?;
    save_to_file(&vec![parameters[1]], "proof/public_inputs.json","public_inputs")?;

    Ok(())
}

// Function to read parameters from JSON file
fn read_parameters<F: PrimeField>(path: &str) -> Result<Vec<F>, Box<dyn std::error::Error>>{
    let file = File::open(path)?;
    let reader = BufReader::new(file);
    let json_data: Value = serde_json::from_reader(reader)?;
    let mut out: Vec<F> = vec![];
    if let Some(root) = json_data.get("root") {
        out.push(F::from(root.as_u64().unwrap()));
    }
    if let Some(square) = json_data.get("square") {
        out.push(F::from(square.as_u64().unwrap()));
    }

    Ok(out)
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