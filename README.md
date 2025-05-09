## zk Script Library

The zk Script Library is a collection of Python scripts that generate Bitcoin SV Scripts compatible with [Bitcoin SV version 1.1.0](https://github.com/bitcoin-sv/bitcoin-sv).

The library supports the generation of Groth16 verification scripts and ancillary operations.

The following scripts are currently implemented:

- [Finite field arithmetic](./docs/finite_fields.md)
- [Elliptic curve arithmetic](./docs/elliptic_curves.md)
- [Efficient operations on secp256k1](./docs/secp256k1.md)
- [Bilinear pairings](./docs/bilinear_pairings.md)
- [Groth16](./docs/groth16.md)

The library currently contains implementations of pairings and Groth16 for:

- [BLS12-381](src/zkscript/groth16/bls12_381/bls12_381.py)
- [MNT4-753](src/zkscript/groth16/mnt4_753/mnt4_753.py)

Please, refer to the [notes](./notes/bilinear_pairings.tex) for a walkthrough of the implementation of bilinear pairings and Groth16 in Bitcoin Script.

Additionally, the library contains the following scripts:

- [Transaction introspection](./docs/transaction_introspection.md)
- [Merkle trees](./docs/merkle_trees.md)

## Requirements
Make sure you are using Python 3.12 or later versions.

You can check your Python version with

```bash
python --version
```

## Installation

After cloning the repository, you can install all the dependencies with

```bash
pip install -r requirements.txt
```

## Getting started

The folder `test` contains scripts generating Bitcoin Scripts for all the implemented operations.
Groth16 locking scripts are generated by [test_groth16.py](./tests/groth16/test_groth16.py).

You can generate the script verifying Groth16 for BLS12-281 and MNT4-753 with pytest:

```bash
pytest .\tests\groth16\test_groth16.py --save-to-json
```

When the --save-to-json option is set (as shown above), scripts are saved in the data/ folder.

## Script size

A transaction spending an output locked by a Groth16 verifier can be found [here](https://whatsonchain.com/tx/e4cd00c1fa7dd6931dd1e45034e9d9f732e6d7d38f7826341715f488a146514c).

The script sizes for Groth16 are:

| Curve | # public statements | Unlocking script size | Locking script size | Modulo threshold | Total |
| ----- | ------------------- | --------------------- | ------------------- | ---------------- | ----- |
| `BLS12-381` | 2 | ~ 59 KB | ~ 421 KB | 200B | ~ 480 KB |
| `MNT4-753` | 1 | ~ 402 KB | ~ 485 KB | 200B | ~ 887 KB |

Note: the unlocking script is dependent on the public statements.

## Disclaimer

The code and resources within this repository are intended for research and educational purposes only.

Please note:

- No guarantees are provided regarding the security or the performance of the code.
- Users are responsible for validating the code and understanding its implications before using it in any capacity.
- There may be edge cases causing bugs or unexpected behaviours. Please contact us if you find any bug.

## License

The code is released under the attached [LICENSE](./LICENSE.txt). If you would like to use it for commercial purposes, please contact <research.enquiries@nchain.com>.
