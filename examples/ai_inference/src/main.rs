use ark_crypto_primitives::sponge::CryptographicSponge;
use ark_crypto_primitives::sponge::poseidon::{PoseidonConfig, PoseidonSponge};
use ark_crypto_primitives::sponge::poseidon::constraints::PoseidonSpongeVar;
use ark_crypto_primitives::sponge::constraints::CryptographicSpongeVar;
use ark_crypto_primitives::sponge::FieldBasedCryptographicSponge;
use ark_ff::PrimeField;
use ark_groth16::Groth16;
use ark_r1cs_std::alloc::AllocVar;
use ark_r1cs_std::boolean::Boolean;
use ark_r1cs_std::eq::EqGadget;
use ark_r1cs_std::fields::fp::FpVar;
use ark_r1cs_std::R1CSVar;
use ark_r1cs_std::ToBitsGadget;
use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystemRef, SynthesisError};
use ark_serialize::{CanonicalSerialize, Compress};
use ark_snark::SNARK;
use ark_test_curves::bls12_381::{Bls12_381,Fr};
use rand::SeedableRng;
use rand_chacha::ChaChaRng;
use serde_json::json;
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use std::str::FromStr;

#[derive(Clone)]
pub struct TwoLayerNN<F: PrimeField> {
    pub weight_1: Vec<Vec<F>>,     // Weight matrix for the first layer 
    pub weight_2: Vec<Vec<F>>,     // Weight matrix for the second layer 
    pub input: Vec<F>,             // Input vector (private input)
    pub bias_1: Vec<F>,            // Bias vector for the first layer
    pub bias_2: Vec<F>,            // Bias vector for the second layer
    pub zero_relu: F,              // Zero value for the relu function,
    pub public_statement: F   // hash value computed with poseidon
}


impl<F: PrimeField> ConstraintSynthesizer<F> for TwoLayerNN<F> {
    fn generate_constraints(self, cs: ConstraintSystemRef<F>) -> Result<(), SynthesisError> {
        // Ensure that dimensions are consistent for matrix multiplication
        assert_eq!(self.weight_1[0].len(), self.input.len());  // Ensure matrix multiplication is valid for the first layer
        assert_eq!(self.weight_2[0].len(), self.weight_1.len());  // Ensure matrix multiplication is valid for the second layer

        // Allocate input vector as witness variables (private input)
        let input_vars: Vec<FpVar<F>> = self.input.iter()
            .map(|&val| FpVar::<F>::new_witness(cs.clone(), || Ok(val)).unwrap())
            .collect();
        

        // Allocate bias vectors as witness variables
        let bias_1_vars: Vec<FpVar<F>> = self.bias_1.iter()
            .map(|&val| FpVar::<F>::new_witness(cs.clone(), || Ok(val)).unwrap())
            .collect();

        let bias_2_vars: Vec<FpVar<F>> = self.bias_2.iter()
            .map(|&val| FpVar::<F>::new_witness(cs.clone(), || Ok(val)).unwrap())
            .collect();

        // Allocate weight matrices as witness variables
        let weight_1_vars: Vec<Vec<FpVar<F>>> = self.weight_1.iter()
            .map(|row| row.iter()
                .map(|&val| FpVar::<F>::new_witness(cs.clone(), || Ok(val)).unwrap())
                .collect())
            .collect();

        let weight_2_vars: Vec<Vec<FpVar<F>>> = self.weight_2.iter()
            .map(|row| row.iter()
                .map(|&val| FpVar::<F>::new_witness(cs.clone(), || Ok(val)).unwrap())
                .collect())
            .collect();

        // Allocate relu zero value as witness variables 
        let zero_relu_var = FpVar::new_witness(cs.clone(), || Ok(self.zero_relu)).unwrap();

        // Step 1: Compute the intermediate result for the first layer (weight_1 * input + bias_1)
        let mut intermediate_result: Vec<FpVar<F>> = vec![];
        for (j, row) in weight_1_vars.iter().enumerate() {
            let mut linear_combination = FpVar::Constant(F::zero());
            for (i, val) in row.iter().enumerate() {
                let term = val.clone() * input_vars[i].clone();
                linear_combination += term;
            }
            linear_combination += bias_1_vars[j].clone();            
            let linear_combination_bits = linear_combination.to_bits_le()?;
            let shifted_bits = if linear_combination_bits.len() > 22usize {
                linear_combination_bits[22usize..].to_vec()
            } else {
                vec![Boolean::constant(false)] 
            };
            let intermediate_var = FpVar::new_witness(cs.clone(), || Boolean::le_bits_to_fp_var(&shifted_bits)?.value()).unwrap();
            intermediate_result.push(intermediate_var);
        }

        // Step 2: Apply ReLU activation to the intermediate result (ReLU: l(x) = max(128, x))
        let relu_result: Vec<FpVar<F>> = intermediate_result.into_iter()
            .map(|val| {
                val.is_cmp(&zero_relu_var, core::cmp::Ordering::Greater, true)
                    .unwrap()
                    .select(&val, &zero_relu_var)
                    .unwrap()
            })
            .collect();

        // Step 3: Compute the final result for the second layer (weight_2 * ReLU(intermediate_result) + bias_2)
        let mut final_result: Vec<FpVar<F>> = vec![];
        for (j, row) in weight_2_vars.iter().enumerate() {
            let mut linear_combination = FpVar::Constant(F::zero());
            for (i, val) in row.iter().enumerate() {
                let term = val.clone() * relu_result[i].clone();
                linear_combination += term;
            }
            linear_combination += bias_2_vars[j].clone();
            let final_var = FpVar::new_witness(cs.clone(), || linear_combination.value()).unwrap();
            final_result.push(final_var);
        }

        // Step 4: Apply the argmax function to find the index of the maximum value in the final result
        let mut max_value = final_result[0].clone();
        let mut index = FpVar::Constant(F::zero());
        let mut max_index = index.clone();
        for val in final_result.iter().skip(1) {
            let is_greater = val.is_cmp(&max_value, core::cmp::Ordering::Greater, true)?;
            index = index.clone() + FpVar::Constant(F::one());
            max_value = is_greater.select(val, &max_value)?;
            max_index = is_greater.select(&index, &max_index)?;
        }
        let computed_output_var = FpVar::new_witness(cs.clone(), || max_index.value()).unwrap();

        // Step 5: Generate the hash for the model  
        let poseidon_config = get_poseidon_config();
        let mut sponge_model = PoseidonSpongeVar::<F>::new(cs.clone(), &poseidon_config);
    

        for row in &weight_1_vars {
            for var in row {
                sponge_model.absorb(&var).unwrap();
            }
        }

        for row in &weight_2_vars {
            for var in row {
                sponge_model.absorb(&var).unwrap();
            }
        }

        for var in bias_1_vars {
            sponge_model.absorb(&var).unwrap();
        }   
        for var in bias_2_vars {
            sponge_model.absorb(&var).unwrap();
        } 

        sponge_model.absorb(&zero_relu_var).unwrap();
        let hash_model_var: FpVar<F> = sponge_model.squeeze_field_elements(1).unwrap()[0].clone();

        // Step 6: Check that hash(input||output||hash_model) is the same as the public statement 
        let mut sponge_inference = PoseidonSpongeVar::<F>::new(cs.clone(), &poseidon_config);
        for var in input_vars {
            sponge_inference.absorb(&var)?;
        }   
        sponge_inference.absorb(&computed_output_var).unwrap();
        sponge_inference.absorb(&hash_model_var).unwrap();
        let hash_inference_var: FpVar<F> = sponge_inference.squeeze_field_elements(1).unwrap()[0].clone();

        let public_statement_var = FpVar::new_input(cs.clone(), || Ok(self.public_statement)).unwrap();


        hash_inference_var.enforce_equal(&public_statement_var)?;


        Ok(())
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize weight matrices, input vector, biases, and output
    let weight_1 = load_matrix("parameters/weight_1.txt");  // Load first layer weights from file
    let weight_2 = load_matrix("parameters/weight_2.txt");  // Load second layer weights from file
    let input = load_vector("parameters/input.txt", 0);        // Load input vector from file
    let bias_1 = load_vector("parameters/bias_1.txt", 0);      // Load first layer biases from file
    let bias_2 = load_vector("parameters/bias_2.txt", 0);      // Load second layer biases from file
    let zero_relu = load_value("parameters/zero_relu.txt", 0, 0);       // Load expected output from file
    let expected_output = load_value("parameters/expected_output.txt", 0, 0);       // Load expected output from file
    let public_statement = compute_model_var(&weight_1, &weight_2, &bias_1, &bias_2, &zero_relu, &input, &expected_output);
    
    // Create the circuit instance
    let circuit = TwoLayerNN {
        weight_1,
        weight_2,
        input,
        bias_1,
        bias_2,
        zero_relu,
        public_statement,
    };

    // Create a random number generator
    let mut rng = ChaChaRng::from_entropy();

    let cs = ark_relations::r1cs::ConstraintSystem::<Fr>::new_ref();

    // Generate constraints
    circuit.clone().generate_constraints(cs.clone())?;

    // Print the number of constraints in the circuit
    println!("Number of constraints in the circuit: {}", cs.num_constraints());
    
    // Setup phase - generate the proving key (pk) and verifying key (vk)
    let (pk, vk) = Groth16::<Bls12_381>::circuit_specific_setup(circuit.clone(), &mut rng)
        .map_err(|e| format!("Setup failed: {}", e))?;
        
    // Proof generation phase
    let proof = Groth16::<Bls12_381>::prove(&pk, circuit.clone(), &mut rng)
        .map_err(|e| format!("Proof generation failed: {}", e))?;

    // Verification phase
    let is_valid = Groth16::<Bls12_381>::verify(&vk, &[public_statement], &proof)
        .map_err(|e| format!("Verification failed: {}", e))?;
    assert!(is_valid, "Proof is invalid");

    // Size information
    let proving_key_size = pk.serialized_size(Compress::No);
    let verifying_key_size = vk.serialized_size(Compress::No);
    let proof_size = proof.serialized_size(Compress::No);

    println!("Proving key size: {} bytes", proving_key_size);
    println!("Verifying key size: {} bytes", verifying_key_size);
    println!("Proof size: {} bytes", proof_size);

    // Save proof, verification key, and public input to files
    save_to_file(&proof, "proof/proof.json", "proof")?;
    save_to_file(&vk, "proof/verifying_key.json", "verifying_key")?;
    save_to_file(&vec![public_statement], "proof/public_inputs.json", "public_inputs")?;

    println!("Proof, verification key, and public input have been saved to 'proof.json', 'verifying_key.json', and 'public_input.json'.");

    Ok(())
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

// Function to parse a .txt file containing a matrix
fn parse_file<T: FromStr>(path: &str) -> Vec<Vec<T>> 
where 
    T::Err: std::fmt::Debug,  // Ensure errors from T's FromStr implementation can be displayed
{
    let f = BufReader::new(File::open(path).unwrap());

    f.lines()
        .map(|line| line.unwrap().split(char::is_whitespace)
             .map(|number| number.parse::<T>().unwrap())
             .collect())
        .collect()
}

// Extract a Fr matrix from a .txt file
fn load_matrix(path: &str) -> Vec<Vec<Fr>> {

    let matrix = parse_file::<i64>(path);
    
    matrix.iter().map(|row| 
        {row.iter().map(|&col| Fr::from(col)).collect::<Vec<Fr>>()
        }
    ).collect()
}

// Extract a Fr vector from a .txt file
fn load_vector(path: &str, col: usize) -> Vec<Fr> {
    let matrix = parse_file::<i64>(path);
    
    matrix.iter().map(|row| {Fr::from(row[col])}).collect()
}

// Extract a Fr value from a .txt file
fn load_value(path: &str, row: usize, col: usize) -> Fr {
    let matrix = parse_file::<i64>(path);
    
    Fr::from(matrix[row][col])
}

// Initialize poseidon sponge
fn get_poseidon_config<F: PrimeField> () -> PoseidonConfig<F> {
    PoseidonConfig {
        full_rounds: 8,
        partial_rounds: 57,
        alpha: 5,
        mds: vec![
            vec![F::from(1u64), F::from(2u64), F::from(3u64)],
            vec![F::from(4u64), F::from(5u64), F::from(6u64)],
            vec![F::from(7u64), F::from(8u64), F::from(9u64)],
        ],
        ark: (0..65)
            .map(|i| vec![F::from(i as u64), F::from(i as u64 + 1), F::from(i as u64 + 2)])
            .collect(),
        rate: 2,
        capacity: 1,
    }
}

// Compute public input 
fn compute_model_var(w1: &Vec<Vec<Fr>>, w2: &Vec<Vec<Fr>>, b1: &Vec<Fr>, b2: &Vec<Fr>, zero: &Fr, input: &Vec<Fr>, output: &Fr) -> Fr {
    let sponge_params = get_poseidon_config();
    
    let mut sponge1 = PoseidonSponge::<Fr>::new(&sponge_params);

    for row in w1 {
        for var in row {
            sponge1.absorb(&var);
        }
    }

    for row in w2 {
        for var in row {
            sponge1.absorb(&var);
        }
    }

    for var in b1 {
        sponge1.absorb(&var);
    }   

    for var in b2 {
        sponge1.absorb(&var);
    } 

    sponge1.absorb(&zero);
    let hash_model: Fr = sponge1.squeeze_field_elements(1)[0];

    let mut sponge2 = PoseidonSponge::<Fr>::new(&sponge_params);
    for var in input {
        sponge2.absorb(&var);
    }   

    sponge2.absorb(&output);
    sponge2.absorb(&hash_model);

    sponge2.squeeze_native_field_elements(1)[0]
}