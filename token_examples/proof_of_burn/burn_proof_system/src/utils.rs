use std::fs::{self, File};
use std::io::{Read, Result as IoResult, Write};
use std::path::Path;

use ark_serialize::CanonicalSerialize;

/// Save a list of bytes to `file_path`
pub(crate) fn save_to_file(data: &[u8], file_path: &str) -> IoResult<()> {
    let file_path: &Path = Path::new(file_path);
    // Create parent directories if they don't exist
    fs::create_dir_all(file_path.parent().unwrap())?;
    // Write data to file
    let mut bin_data = File::create(file_path)?;
    bin_data.write_all(&(data.len() as u64).to_le_bytes())?; // Write length
    bin_data.write_all(data)?; // Write data
    Ok(())
}

/// Read `file_path` into a vector of bytes
pub(crate) fn read_from_file(file_path: &str) -> IoResult<Vec<u8>> {
    let mut file = File::open(file_path)?;
    let mut len_bytes = [0u8; 8];
    file.read_exact(&mut len_bytes)?;

    let len = u64::from_le_bytes(len_bytes) as usize;

    let mut vec = vec![0; len];
    file.read_exact(&mut vec)?;
    Ok(vec)
}

/// Serialise an item implementing [CanonicalSerialize]
/// We use unchecked serialisation for speed reasons
pub(crate) fn data_to_serialisation(item: &impl CanonicalSerialize) -> Vec<u8> {
    let mut serialized_data: Vec<u8> = vec![0; item.uncompressed_size()];
    item.serialize_unchecked(&mut serialized_data[..]).unwrap();
    serialized_data
}
