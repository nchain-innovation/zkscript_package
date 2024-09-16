## Neural Network

This repository contains a Groth16 verifier for a 2-layer neural network performing inference on the MNIST dataset (handwritten digits).

**Input**: 784-dimensional array. Each entry represents the grayscale value of a byte in an input image.  
**Output**: A value between 0 and 9.

The network parameters are all integers. The structure of the network is as follows.

Let `v_0` be the input.

1. **First fully connected layer**: size 16x784, with a 16-dimensional bias vector. Operations:  
   `v_1' = W_1 * v_0 + b_1`. After computing `v_1'`, it is divided (integer division) by `2**22`.

2. **ReLU function**: We compute `v_2 = map(lambda x: max(93, x), v_1)`.

3. **Second fully connected layer**: size 10x16, with a 10-dimensional bias vector. Operations:  
   `v_3 = W_2 * v_2 + b_2`.

4. **Argmax layer**: Takes the `argmax(v_3)` and outputs the result.

### Notes:
- The existing parameters were computed using quantization-aware training.
- The division in point 1 is performed using bitwise shift, it is necessary to maintain model accuracy.
- Avoiding softmax in the last step reduces circuit complexity.

## Poseidon Hash

Instead of checking if `output = expected_output`, we use the Poseidon hash function to squeeze all information into a single hash.

1. We compute `poseidon(model)`, which depends on all the model parameters.
2. Use this value to compute `poseidon(input | output | poseidon(model))`.
3. We check that `poseidon(input | output | poseidon(model)) = poseidon(input | expected_output | poseidon(model))`.

This approach ensure the circuit is operating using a committed model.

## Parameters

The model parameters are loaded from the `parameters` folder. The file `output.txt` contains the ground truth and is loaded to compute the poseidon hash. A dummy folder `test_parameters` is provided to test small changes to the code.

## Circuit

The circuit representing the neural network takes as **private inputs**:
- The input vector.
- The network parameters.

The **public output** is the hash value:  
`poseidon(input | expected_output | poseidon(model))`.